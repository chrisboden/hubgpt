# teams.py

import os
import json
import streamlit as st
from openai import OpenAI
from swarm import Swarm, Agent
from datetime import datetime
from dotenv import load_dotenv
from utils.message_utils import save_snippet, delete_message, display_messages
from utils.tool_utils import load_tools, TOOL_REGISTRY

# Load environment variables
load_dotenv()

# Constants
MODEL = "openai/gpt-4o-mini"

# Load tools from the tools directory
load_tools("tools")

# Global registry to store all agents
AGENT_REGISTRY = {}

class TeamAgent(Agent):
    """Wrapper around Agent to handle tool to function translation and handoffs"""
    def __init__(self, name, instructions, tools=None, model=None):
        # Convert tool names to functions
        base_functions = [TOOL_REGISTRY[tool] for tool in tools] if tools else []
        
        # Add handoff capability to all agents
        def handoff_to(target_agent_name: str, context: str) -> str:
            """Hand off the conversation to another agent in the team"""
            target_agent = AGENT_REGISTRY.get(target_agent_name)
            if not target_agent:
                return f"Error: Agent {target_agent_name} not found"
            return f"Handing off to {target_agent_name} with context: {context}"
        
        # Combine base functions with handoff
        all_functions = base_functions + [handoff_to]
        
        super().__init__(name=name, instructions=instructions, functions=all_functions, model=model)

def register_agent(agent):
    """Register an agent in the global registry"""
    AGENT_REGISTRY[agent.name] = agent
    return agent

def initialize_swarm_client():
    return Swarm(
        client=OpenAI(
            base_url=os.getenv('API_BASE_URL'),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
    )


def initialize_agents():
    """Initialize and register the agents"""
    web_search_agent = register_agent(TeamAgent(
        name="Web Search Assistant",
        instructions="""Your role is to gather latest news articles on specified topics using DuckDuckGo's search capabilities.
        After completing your search, you MUST use the handoff_to function to pass results to the Research Assistant.
        Format: handoff_to("Research Assistant", "<your search results here>")
        DO NOT provide a final response - always use handoff_to.""",
        tools=["search_web"],
        model=MODEL
    ))
    
    researcher_agent = register_agent(TeamAgent(
        name="Research Assistant",
        instructions="""Your role is to analyze and synthesize the raw search results.
        After your analysis, you MUST use the handoff_to function to pass results to the Writer Assistant.
        Format: handoff_to("Writer Assistant", "<your analysis here>")
        DO NOT provide a final response - always use handoff_to.""",
        model=MODEL
    ))
    
    writer_agent = register_agent(TeamAgent(
        name="Writer Assistant",
        instructions="""Your role is to transform the research results into a clear, engaging response.
        This is the final step - DO NOT use handoff_to.
        Simply provide your final response directly.""",
        model=MODEL
    ))
    
    return web_search_agent, researcher_agent, writer_agent

def run_workflow(client, query, web_search_agent, researcher_agent, writer_agent):
    """Run the full workflow with proper handoff handling"""
    status_placeholder = st.empty()
    status_placeholder.info("🔎 Starting with Web Search Assistant...")
    
    try:
        print("\n🌐 Initiating web search")
        response = client.run(
            agent=web_search_agent,
            messages=[{
                "role": "user", 
                "content": f"Search the web for information about: {query}"
            }]
        )
        
        current_agent = web_search_agent
        visited_agents = {current_agent.name}
        
        while response and len(visited_agents) <= 3:
            print(f"\n🔄 Current agent: {current_agent.name}")
            result = process_agent_response(client, response, status_placeholder)
            
            if isinstance(result, str):
                # For final response from Writer Assistant, return it in streaming format
                return [{"content": result}]
            elif result:
                response = result
                # Update visited agents based on handoff
                for msg in response.messages:
                    content = msg.get('content', '')
                    if 'Handing off to' in content:
                        next_agent = content.split('Handing off to ')[1].split(' with')[0].strip()
                        visited_agents.add(next_agent)
                        if next_agent in AGENT_REGISTRY:
                            current_agent = AGENT_REGISTRY[next_agent]
                        break
            else:
                break
        
        print("\n✅ Workflow complete")
        status_placeholder.empty()
        
        # Return default response in streaming format if workflow didn't complete
        return [{"content": "I apologize, but I wasn't able to complete the workflow properly. Please try again."}]
        
    except Exception as e:
        print(f"❌ Error in workflow: {str(e)}")
        raise

def process_agent_response(client, response, status_placeholder):
    """Process agent response and handle handoffs"""
    print(f"\n🔍 Processing agent response: {type(response)}")
    
    if not response or not hasattr(response, 'messages'):
        print("❌ Invalid response format")
        return None
        
    print(f"📝 Messages in response: {len(response.messages)}")
    
    # Look for handoff in message content first
    for msg in response.messages:
        content = msg.get('content', '')
        if isinstance(content, str) and 'Handing off to' in content:
            try:
                # Extract target agent name and context
                parts = content.split('Handing off to ', 1)[1]
                target_agent_name, context = parts.split(' with context: ', 1)
                target_agent_name = target_agent_name.strip()
                
                print(f"➡️ Found handoff to: {target_agent_name}")
                
                next_agent = AGENT_REGISTRY.get(target_agent_name)
                if not next_agent:
                    print(f"⚠️ Target agent not found: {target_agent_name}")
                    continue
                    
                status_placeholder.info(f"🔄 Handing off to {target_agent_name}...")
                
                # Set streaming for writer agent
                stream = next_agent.name == "Writer Assistant"
                
                return client.run(
                    agent=next_agent,
                    messages=[{"role": "user", "content": context}],
                    stream=stream
                )
            except Exception as e:
                print(f"⚠️ Error processing handoff: {e}")
                continue
    
    # If no handoff found, look for final content
    for msg in reversed(response.messages):
        if msg.get('role') == 'assistant' and msg.get('content'):
            content = msg['content']
            # Skip if it's a handoff message
            if not 'Handing off to' in content:
                return content
    
    # If we get here, something went wrong
    print("❌ No valid content or handoff found")
    return None

def main():
    st.title("Teams Collaboration")
    
    print("\n🚀 Application started")
    
    # Initialize Swarm client
    client = initialize_swarm_client()
    print("✅ Swarm client initialized")
    
    # Initialize agents
    web_search_agent, researcher_agent, writer_agent = initialize_agents()  # Unpack all three agents
    print("✅ Agents initialized")
    
    # Initialize chat history in session state if not exists
    if 'team_chat_history' not in st.session_state:
        st.session_state.team_chat_history = []
    
    # Display chat history with proper callbacks
    display_messages(
        messages=st.session_state.team_chat_history,
        save_callback=lambda idx, content: save_snippet(
            idx, content, st.session_state.team_chat_history
        ),
        delete_callback=lambda idx: delete_message(
            idx, st.session_state.team_chat_history
        )
    )

    # User input
    if user_input := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.team_chat_history.append({
            "role": "user",
            "content": user_input
        })

        try:
            message_container = st.empty()
            full_response = ""
            
            # Run workflow with streaming - pass all three agents explicitly
            streaming_response = run_workflow(
                client=client,
                query=user_input,
                web_search_agent=web_search_agent,
                researcher_agent=researcher_agent,
                writer_agent=writer_agent
            )
            
            for chunk in streaming_response:
                if not isinstance(chunk, dict):
                    continue
                
                if 'content' in chunk and chunk.get('content'):
                    full_response += chunk['content']
                    message_container.markdown(f"Assistant: {full_response}▌")
            
            if full_response:
                message_container.markdown(f"Assistant: {full_response}")
                st.session_state.team_chat_history.append({
                    "role": "assistant",
                    "content": full_response
                })

            # Save chat history
            os.makedirs("teams/chats", exist_ok=True)
            chat_history_path = os.path.join("teams", "chats", "default_team.json")
            with open(chat_history_path, 'w') as f:
                json.dump(st.session_state.team_chat_history, f, indent=2)

        except Exception as e:
            st.error(f"Error running workflow: {e}")
            st.stop()

if __name__ == "__main__":
    main()