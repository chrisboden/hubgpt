import os
import json
import logging
from dotenv import load_dotenv
import streamlit as st
from swarm import Swarm, Agent
from openai import OpenAI
from utils.tool_utils import load_tools, TOOL_REGISTRY

# Load environment variables
load_dotenv()

# Initialize Swarm client
client = Swarm(
    client=OpenAI(
        base_url=os.getenv('API_BASE_URL'),
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load tools from the tools directory
TOOLS_DIR = "tools"
load_tools(TOOLS_DIR)  # This populates TOOL_REGISTRY

# Load agent definitions from JSON file located in the 'teams' directory
SWARM_TEAM_CONFIG = "teams/swarm_team.json"
with open(SWARM_TEAM_CONFIG, "r") as f:
    agent_definitions = json.load(f)

# Initialize an agent registry to store agents by name
agent_registry = {}

# Instantiate agents from JSON definitions and assign loaded tools
for properties in agent_definitions:
    functions = []
    
    # Dynamically assign tools based on the "functions" field of each agent
    for func_name in properties.get("functions", []):
        if func_name in TOOL_REGISTRY:
            # Add the function to the agent’s functions
            functions.append(TOOL_REGISTRY[func_name])
            logging.info(f"Assigned tool '{func_name}' to agent '{properties['name']}'")
        else:
            logging.warning(f"Tool '{func_name}' not found in TOOL_REGISTRY. Skipping.")

    # Create the agent with loaded tools and instructions
    agent = Agent(
        name=properties["name"],
        instructions=properties["instructions"],
        functions=functions
    )

    # Register agent in registry for easy access by name
    agent_registry[properties["name"]] = agent

# Streamlit UI Setup
st.title("Streamlit Chatbot with Swarm Agents")

# Ensure session state variables are initialized
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "current_agent" not in st.session_state:
    # Default to ServiceAgent if current_agent is not already set
    st.session_state["current_agent"] = agent_registry.get("ServiceAgent", None)

# Debug: Verify initial session state
print(f"[Debug] Initialized current_agent: {st.session_state['current_agent']}")
print(f"[Debug] Initialized messages: {st.session_state['messages']}")

# Function to create handoff functions dynamically
def create_handoff_function(target_agent_name, description=""):
    def handoff_function():
        print(f"[Handoff] Attempting to hand off to {target_agent_name}. {description}")
        return agent_registry[target_agent_name]
    handoff_function.__name__ = f"handoff_to_{target_agent_name}"
    if st.session_state.current_agent.name == "WebSearchAgent":
        print("[Debug] WebSearchAgent is now in control.")
    return handoff_function

# Add handoff functions based on JSON configuration
for properties in agent_definitions:
    agent = agent_registry[properties["name"]]
    for handoff in properties.get("handoffs", []):
        # Create and add the handoff function for each target agent with description
        handoff_function = create_handoff_function(handoff["target"], handoff.get("description", ""))
        agent.functions.append(handoff_function)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = agent_registry["ServiceAgent"]

# Display previous messages
for message in st.session_state.messages:
    role = message.get("role", "Unknown")
    content = message["content"]
    if role == "user":
        st.chat_message("user").markdown(content)
    else:
        st.chat_message("assistant").markdown(content)

# Handle user input
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Run the conversation with the current agent
    response = client.run(agent=st.session_state.current_agent, messages=st.session_state.messages)

    # Check if a handoff is required and prevent multiple handoffs in the same cycle
    handoff_occurred = False
    for func in st.session_state.current_agent.functions:
        if func.__name__.startswith("handoff_to_") and not handoff_occurred:
            next_agent = func()
            if next_agent != st.session_state.current_agent:  # Ensures we're switching agents
                print(f"[Handoff] {st.session_state.current_agent.name} handing off to {next_agent.name}")
                st.session_state.current_agent = next_agent
                handoff_occurred = True  # Prevents additional handoffs in this cycle
                break

    # Append the response to the chat messages
    for message in response.messages:
        if message not in st.session_state.messages:  # Avoid duplicate entries
            st.session_state.messages.append(message)

    # Display the updated messages
    for message in st.session_state.messages:
        role = message.get("role", "Unknown")
        content = message["content"]
        if role == "user":
            st.chat_message("user").markdown(content)
        else:
            st.chat_message("assistant").markdown(content)
