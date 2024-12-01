# team_chat.py

import os
import json
import logging
import uuid
from typing import List, Callable, Optional, Dict
from dataclasses import dataclass
import inspect
import traceback
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
from utils.db_utils import AgentRunsDB
from utils.tool_utils import TOOL_REGISTRY, TOOL_METADATA_REGISTRY
from utils.tool_utils import load_tools

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Response:
    agent: 'Agent'
    messages: list

class Agent:
    def __init__(self, name: str, instructions: str, tools: List[str] = None):
        self.name = name
        self.instructions = instructions
        self.tool_names = tools or []  # Store tool names
        self.model = "openai/gpt-4o-mini"
        
        # Get tool metadata for this agent's tools
        self.tools = []
        for tool_name in self.tool_names:
            if tool_name in TOOL_METADATA_REGISTRY:
                self.tools.append(TOOL_METADATA_REGISTRY[tool_name])
            else:
                logging.warning(f"Tool {tool_name} not found in registry")

def final_outcome(report: str) -> str:
    """Present the final report to the user"""
    st.chat_message("assistant").markdown(f"**Final Report:**\n\n{report}")
    return "Final report delivered to user."

def escalate_to_human(summary: str):
    """Escalate complex issues to human oversight"""
    st.chat_message("assistant").markdown(f"**Human Escalation Required:**\n\nSummary: {summary}")
    return "Escalated to human supervisor"

# Tool mapping
AVAILABLE_TOOLS = {
    "escalate_to_human": escalate_to_human,
    "final_outcome": final_outcome
}

def init_teams():
    # Load shared tools
    load_tools('tools/')
    
    # Load team configs and create agents
    config = load_team_config('teams/old/demo_team.json')
    agents = create_agents(config)
    return agents


def load_team_config(file_path: str) -> Dict:
    """Load team configuration from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading team configuration: {str(e)}")
        raise

def create_agents(config: Dict) -> Dict[str, Agent]:
    """Create agent instances from configuration"""
    created_agents = {}
    
    for agent_id, agent_config in config['agents'].items():
        # Instead of looking up tools in AVAILABLE_TOOLS, just pass the tool names
        # The Agent class will look them up in TOOL_METADATA_REGISTRY
        created_agents[agent_id] = Agent(
            name=agent_config['name'],
            instructions=agent_config['instructions'],
            tools=agent_config['tools']  # Just pass the tool names
        )
    
    return created_agents

def function_to_schema(func: Callable) -> dict:
    """Convert a function to an OpenAI tool schema."""
    if func.__name__ == "handoff_to_coordinator":
        schema = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "work_done": {
                            "type": "string",
                            "description": "The complete output from the work you have done, to pass to the coordinator agent"
                        },
                        "handoff": {
                            "type": "string",
                            "description": "The message explaining what work you have done, for the coordinator agent"
                        }
                    },
                    "required": ["work_done", "handoff"]
                }
            }
        }
    elif func.__name__ == "handoff_to_agent":
        schema = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "The name of the agent to hand off to (in lower case)"
                        },
                        "handoff": {
                            "type": "string",
                            "description": "A comprehensive briefing message that explains what work you want the target agent to perform."
                        },
                        "work_done": {
                            "type": "string",
                            "description": "The work you have completed that needs to be passed to the next agent"
                        }
                    },
                    "required": ["agent_name", "handoff"]
                }
            }
        }
    else:
        # Default schema for other functions
        schema = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    return schema

# team_chat.py

def execute_tool_call(tool_call, tools, agent_name, messages, run_id):
    """Execute a tool call and handle agent transfers with context."""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    # Get the actual tool function from TOOL_REGISTRY
    tool_func = TOOL_REGISTRY.get(name)
    if not tool_func:
        raise Exception(f"Tool {name} not found in registry")

    # Always add llm_client to args for all tools
    args["llm_client"] = client

    if name == "handoff_to_coordinator":
        if not args.get('work_done') or not args.get('handoff'):
            raise Exception("Agents must provide 'work_done' and 'handoff' when calling handoff_to_coordinator")
        
        tool_call_id = str(uuid.uuid4())
        db.add_step(
            run_id=run_id,
            output=args['work_done'],
            handoff_msg=args['handoff'],
            actor_agent=agent_name,
            target_agent="coordinator",
            summary="Handoff to coordinator",
            tool_call_id=tool_call_id
        )
        
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_call_id": tool_call_id,
            "handoff": args['handoff'],
            "agent_name": agent_name
        })
        
        # Execute tool and return the coordinator agent
        tool_func(**args)  # Execute with llm_client
        return agents["coordinator"]

    elif name == "handoff_to_agent":
        if not args.get('agent_name') or not args.get('handoff'):
            raise Exception("Must specify 'agent_name' and 'handoff' when handing off to another agent")

        tool_call_id = str(uuid.uuid4())
        if args.get('work_done'):
            db.add_step(
                run_id=run_id,
                output=args['work_done'],
                handoff_msg=args['handoff'],
                actor_agent=agent_name,
                target_agent=args['agent_name'],
                summary=f"Handoff to {args['agent_name']}",
                tool_call_id=tool_call_id
            )

        message_entry = {
            "role": "assistant",
            "content": "",
            "handoff": args['handoff'],
            "agent_name": agent_name,
            "tool_call_id": tool_call_id
        }

        messages.append(message_entry)

        # Execute tool and return the target agent
        tool_func(**args)  # Execute with llm_client
        return agents[args['agent_name']]

    elif name == "final_outcome":
        work_done = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and "tool_call_id" in msg:
                steps = db.get_steps_for_run(run_id)
                for step in reversed(steps):
                    if step["tool_call_id"] == msg["tool_call_id"]:
                        work_done = step["output"]
                        break
                if work_done:
                    break
        if not work_done:
            raise Exception("No final report found for final_outcome")
        cleaned_args = {'report': work_done}
        logger.info(f"Executing tool: {name} with args: {str(cleaned_args)[:100]}...")
        return final_outcome(**cleaned_args)

    else:
        sig = inspect.signature(tool_func)
        cleaned_args = {k: v for k, v in args.items() if k in sig.parameters}
        logger.info(f"Executing tool: {name} with args: {str(cleaned_args)[:100]}...")
        return tool_func(**cleaned_args)


def build_context_messages(agent: Agent, messages: List[dict], run_id: str) -> List[dict]:
    if agent.name.lower() == "coordinator":
        context_messages = [{"role": "system", "content": agent.instructions}]
        
        N = 30
        truncated_messages = messages[-N:]
        logger.info(f"Using the last {N} messages for context.")

        steps = db.get_steps_for_run(run_id)
        steps_by_tool_call = {step["tool_call_id"]: step for step in steps}

        for msg in truncated_messages:
            context_msg = {
                "role": msg["role"],
                "content": msg.get("content", "")
            }

            if msg["role"] in ["system", "user", "assistant"]:
                if "tool_call_id" in msg:
                    step = steps_by_tool_call.get(msg["tool_call_id"])
                    if step and step['output'].strip():
                        agent_name = step["actor_agent"]
                        if agent_name.lower() != "coordinator":
                            context_msg["content"] += f"\n\nPrevious work done by {agent_name}:\n{step['output']}"
                if "handoff" in msg:
                    context_msg["content"] += f"\n\nHandoff Instructions:\n{msg['handoff']}"

            context_messages.append(context_msg)

        return context_messages
    else:
        user_request = None
        for msg in messages:
            if msg["role"] == "user":
                user_request = msg["content"]
                break

        steps = db.get_steps_for_run(run_id)
        previous_work = ''
        previous_agent_name = ''
        
        for step in reversed(steps):
            if step["actor_agent"].lower() != "coordinator" and step["output"].strip():
                previous_work = step["output"]
                previous_agent_name = step["actor_agent"]
                break

        handoff_instructions = ''
        for msg in reversed(messages):
            if "handoff" in msg:
                handoff_instructions = msg["handoff"]
                break

        user_message_content = f"""Hi, it's the Coordinator Agent here. A user has asked our team for assistance and we have been on the job.

The user's request was: 

{user_request}

"""

        if previous_work.strip():
            user_message_content += f"""-------
Our team has been working on this request. Prior work done by {previous_agent_name} is as follows:

{previous_work}

"""

        user_message_content += f"""-------
Here's what the team needs you to do:

{handoff_instructions}

Please figure out the best possible answer to the last user query from the conversation above.
"""

        context_messages = [
            {"role": "system", "content": agent.instructions},
            {"role": "user", "content": user_message_content}
        ]

        return context_messages


def run_full_turn(agent: Agent, messages: list, run_id: str) -> Response:
    current_agent = agent
    num_init_messages = len(messages)
    messages = messages.copy()
    max_retries = 2
    retry_count = 0

    while True:
        # Get tool metadata from TOOL_METADATA_REGISTRY instead of converting functions
        tool_schemas = []
        for tool_name in current_agent.tool_names:  # Use tool_names from agent
            if tool_name in TOOL_METADATA_REGISTRY:
                tool_schemas.append(TOOL_METADATA_REGISTRY[tool_name])

        context_messages = build_context_messages(current_agent, messages, run_id)

        request_payload = {
            'model': current_agent.model,
            'messages': context_messages,
            'tools': tool_schemas if tool_schemas else None
        }
        logger.info("\n=== API Request Payload ===")
        logger.info(json.dumps(request_payload, indent=2))
        logger.info("==========================\n")
        
        try:
            response = client.chat.completions.create(**request_payload)
            logger.info("\n=== API Response ===")
            logger.info(str(response))
            logger.info("====================\n")

            if not response or not response.choices:
                raise Exception(f"Empty response received from API")

            message = response.choices[0].message
            if not message:
                if 'error' in response:
                    logger.error(f"API Error: {response['error']}")
                    raise Exception(f"API Error: {response['error']}")
                raise Exception("No message in API response")

            logger.info(f"Received response from {current_agent.model}")
            logger.info(f"Response content: {message.content or 'No content'}")

            message_dict = {
                "role": "assistant",
                "content": message.content or ""
            }

            if message.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]

            messages.append(message_dict)

            if message.content:
                st.chat_message("assistant").markdown(message.content)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result = execute_tool_call(tool_call, None, current_agent.name, messages, run_id)

                    if isinstance(result, Agent):
                        logger.info(f"Agent transfer: {current_agent.name} → {result.name}")
                        current_agent = result
                        result = f"Transferred to {result.name}. Adopting new role."
                        # Continue the loop with the new agent
                        break  # Break the tool_calls loop to continue with while loop

                    messages.append({
                        "role": "assistant",
                        "content": result or ""
                    })
                    
                    if tool_call.function.name == "final_outcome":
                        return Response(agent=current_agent, messages=messages[num_init_messages:])
                else:  # This else belongs to the for loop - executes if no break occurred
                    return Response(agent=current_agent, messages=messages[num_init_messages:])
            elif not message.content:  # Only break if there's no content AND no tool calls
                raise Exception("Empty response from API - no content or tool calls")
            else:  # Has content but no tool calls
                return Response(agent=current_agent, messages=messages[num_init_messages:])

        except Exception as e:
            logger.error(f"Error in run_full_turn: {str(e)}")
            logger.error("Exception Traceback:")
            logger.error(traceback.format_exc())
            retry_count += 1
            if retry_count > max_retries:
                return Response(
                    agent=agents["coordinator"],
                    messages=[{
                        "role": "assistant",
                        "content": "I encountered an error and need to restart with the coordinator."
                    }]
                )
            continue


# Initialize db and load agents
db = AgentRunsDB()
load_tools('tools/')  # Load tools first
config = load_team_config('teams/old/demo_team.json')
agents = create_agents(config)

if __name__ == "__main__":
    client = OpenAI(
        base_url=os.getenv('API_BASE_URL'),
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    st.title("AI Chatbot")
    st.write("Start chatting! (type 'quit' to exit)")

    agent = agents["coordinator"]
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.run_id = db.create_run()
    
    user_input = st.chat_input("Type your message here...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            response = run_full_turn(agent, st.session_state.messages, st.session_state.run_id)
            agent = response.agent
            st.session_state.messages.extend(response.messages)
        except Exception as e:
            st.chat_message("assistant").markdown(f"Error: {str(e)}")
            st.chat_message("assistant").markdown("Transferring back to coordinator...")
            agent = agents["coordinator"]

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.chat_message("user").markdown(message["content"])
        else:
            st.chat_message("assistant").markdown(message["content"])