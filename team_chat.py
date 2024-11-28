# run_team_streamlit.py

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

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScratchpadManager:
    def __init__(self):
        self.work = {}
        
    def save_work(self, content: str, agent_name: str, handoff_message: str = "", handoff_target: str = "") -> str:
        key = str(uuid.uuid4())
        self.work[key] = {
            "key": key,
            "agent_name": agent_name,
            "content": content,
            "handoff_message": handoff_message,
            "handoff_target": handoff_target
        }
        return key
        
    def get_work(self, key: str) -> Optional[dict]:
        if key not in self.work:
            return None
        work_entry = self.work[key]
        return work_entry
        
    def get_all_work(self) -> dict:
        if not self.work:
            logger.info("Scratchpad is empty")
        for key, work_entry in self.work.items():
            logger.info(f"\nKey: {key}\nWork Entry:\n{work_entry}")
        return self.work.copy()
        
    def clear(self):
        logger.info("\n=== SCRATCHPAD CLEARED ===")
        self.work = {}

@dataclass
class Response:
    agent: 'Agent'
    messages: list

class Agent:
    def __init__(self, name: str, instructions: str, tools: List[Callable] = None):
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model = "openai/gpt-4o-mini"

def final_outcome(report: str) -> str:
    """Present the final report to the user"""
    st.chat_message("assistant").markdown(f"**Final Report:**\n\n{report}")
    return "Final report delivered to user."

def escalate_to_human(summary: str):
    """Escalate complex issues to human oversight"""
    st.chat_message("assistant").markdown(f"**Human Escalation Required:**\n\nSummary: {summary}")
    return "Escalated to human supervisor"

def handoff_to_coordinator(work_done: str, handoff: str) -> Agent:
    """Handoff work to the coordinator agent."""
    return agents["coordinator"]

def handoff_to_agent(agent_name: str, handoff: str) -> Agent:
    """Handoff work to another agent by name."""
    return agents[agent_name]

# Tool mapping
AVAILABLE_TOOLS = {
    "handoff_to_agent": handoff_to_agent,
    "handoff_to_coordinator": handoff_to_coordinator,
    "escalate_to_human": escalate_to_human,
    "final_outcome": final_outcome
}

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
        tools = [AVAILABLE_TOOLS[tool_name] for tool_name in agent_config['tools']]
        created_agents[agent_id] = Agent(
            name=agent_config['name'],
            instructions=agent_config['instructions'],
            tools=tools
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

def execute_tool_call(tool_call, tools, agent_name, messages):
    """Execute a tool call and handle agent transfers with context."""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    scratchpad.get_all_work()

    if name == "final_outcome":
        work_done = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and "work_done_key" in msg:
                work_entry = scratchpad.get_work(msg["work_done_key"])
                if work_entry:
                    work_done = work_entry['content']
                    break
        if not work_done:
            raise Exception("No final report found for final_outcome")
        cleaned_args = {'report': work_done}
        logger.info(f"Executing tool: {name} with args: {str(cleaned_args)[:100]}...")
        result = tools[name](**cleaned_args)
        return result

    elif name == "handoff_to_coordinator":
        if not args.get('work_done') or not args.get('handoff'):
            raise Exception("Agents must provide 'work_done' and 'handoff' when calling handoff_to_coordinator")
        work_done_key = scratchpad.save_work(
            content=args['work_done'],
            agent_name=agent_name,
            handoff_message=args['handoff'],
            handoff_target="coordinator"
        )
        messages.append({
            "role": "assistant",
            "content": "",
            "work_done_key": work_done_key,
            "handoff": args['handoff'],
            "agent_name": agent_name
        })
        result = tools[name](work_done=args['work_done'], handoff=args['handoff'])
        logger.info(f"Executing tool: {name} with args: {str(args)[:100]}...")
        return result

    elif name == "handoff_to_agent":
        if not args.get('agent_name') or not args.get('handoff'):
            raise Exception("Must specify 'agent_name' and 'handoff' when handing off to another agent")

        message_entry = {
            "role": "assistant",
            "content": "",
            "handoff": args['handoff'],
            "agent_name": agent_name
        }

        if args.get('work_done'):
            message_entry['work_done'] = args['work_done']

        messages.append(message_entry)

        result = tools[name](
            agent_name=args['agent_name'],
            handoff=args['handoff']
        )
        logger.info(f"Executing tool: {name} with args: {str(args)[:100]}...")
        return result

    else:
        sig = inspect.signature(tools[name])
        cleaned_args = {k: v for k, v in args.items() if k in sig.parameters}
        logger.info(f"Executing tool: {name} with args: {str(cleaned_args)[:100]}...")
        result = tools[name](**cleaned_args)
        return result

def build_context_messages(agent: Agent, messages: List[dict]) -> List[dict]:
    if agent.name.lower() == "coordinator":
        context_messages = [{"role": "system", "content": agent.instructions}]
        
        N = 30
        truncated_messages = messages[-N:]
        logger.info(f"Using the last {N} messages for context.")

        for msg in truncated_messages:
            context_msg = {
                "role": msg["role"],
                "content": msg.get("content", "")
            }

            if msg["role"] in ["system", "user", "assistant"]:
                if "work_done_key" in msg:
                    work_entry = scratchpad.get_work(msg["work_done_key"])
                    if work_entry and work_entry['content'].strip():
                        agent_name = work_entry.get("agent_name", "an agent")
                        if agent_name.lower() != "coordinator":
                            context_msg["content"] += f"\n\nPrevious work done by {agent_name}:\n{work_entry['content']}"
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

        previous_work = ''
        previous_agent_name = ''
        for msg in reversed(messages):
            if 'work_done_key' in msg:
                work_entry = scratchpad.get_work(msg["work_done_key"])
                if work_entry and work_entry['content'].strip():
                    agent_name = work_entry.get("agent_name", "an agent")
                    if agent_name.lower() == "coordinator":
                        continue
                    previous_work = work_entry['content']
                    previous_agent_name = agent_name
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

def run_full_turn(agent: Agent, messages: list) -> Response:
    current_agent = agent
    num_init_messages = len(messages)
    messages = messages.copy()
    max_retries = 2
    retry_count = 0

    while True:
        tool_schemas = [function_to_schema(tool) for tool in current_agent.tools]
        tools = {tool.__name__: tool for tool in current_agent.tools}

        context_messages = build_context_messages(current_agent, messages)

        request_payload = {
            'model': current_agent.model,
            'messages': context_messages,
            'tools': tool_schemas or None
        }
        logger.info("\n=== API Request Payload ===")
        logger.info(json.dumps(request_payload, indent=2))
        logger.info("==========================\n")
        # In run_full_turn function of team_chat.py
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
                    result = execute_tool_call(tool_call, tools, current_agent.name, messages)

                    if isinstance(result, Agent):
                        logger.info(f"Agent transfer: {current_agent.name} → {result.name}")
                        current_agent = result
                        result = f"Transferred to {result.name}. Adopting new role."

                    messages.append({
                        "role": "assistant",
                        "content": result or ""
                    })
                    
                    if tool_call.function.name == "final_outcome":
                        return Response(agent=current_agent, messages=messages[num_init_messages:])
            elif not message.content:  # Only break if there's no content AND no tool calls
                raise Exception("Empty response from API - no content or tool calls")

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

    return Response(agent=current_agent, messages=messages[num_init_messages:])

# Initialize scratchpad and load agents
scratchpad = ScratchpadManager()
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
    messages = []

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    user_input = st.chat_input("Type your message here...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            response = run_full_turn(agent, st.session_state.messages)
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

    scratchpad.clear()