import os
import json
import logging
from typing import List, Callable, Optional
from dataclasses import dataclass
from openai import OpenAI
import inspect
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """
    Present the final report to the user
    
    Args:
        report: The complete, formatted report text
    Returns:
        Confirmation message
    """
    print("\n=== Final Report ===")
    print(report)
    print("==================\n")
    return "Final report delivered to user."


def escalate_to_human(summary: str):
    """Escalate complex issues to human oversight"""
    print("\n=== Human Escalation Required ===")
    print(f"Summary: {summary}")
    print("================================\n")
    return "Escalated to human supervisor"

def get_researcher_agent(work_done: str = "", handoff: str = ""):
    """Transfer work to the researcher agent
    Args:
        work_done: This is the content or material that you want the researcher agent to use in their work.
        handoff: This is the briefing you give to the researcher agent with respect to their task. Eg
    """
    logger.info(f"Transferring to researcher with work: {work_done[:100]}...")
    return researcher_agent

def get_analyst_agent(work_done: str = "", handoff: str = ""):
    """Transfer work to the analyst agent
    Args:
        work_done: This is the content or material that you want the analyst agent to use in their work.
        handoff: This is the briefing message you wish to give to the analyst agent to instruct them on the task you need done
    """
    logger.info(f"Transferring to analyst with work: {work_done[:100]}...")
    return analyst_agent

def get_writer_agent(work_done: str = "", handoff: str = ""):
    """Transfer work to the writer agent
    Args:
        work_done: This is the content or material that you want the writer agent to use in their work.
        handoff: This is the briefing message you wish to give to the writer agent to instruct them on the task you need done
    """
    logger.info(f"Transferring to writer with work: {work_done[:100]}...")
    return writer_agent

def get_coordinator_agent(work_done: str = "", handoff: str = ""):
    """Transfer work to the coordinator agent
    Args:
        work_done: This is the output from the task you have just completed in response to the brief from the co-ordinator.
        handoff: This is your message to the coordinator explaining the work you have done, or seeking clarification or assistance, etc
    """
    logger.info(f"Transferring to coordinator with work: {work_done[:100]}...")
    return coordinator_agent

def function_to_schema(func: Callable) -> dict:
    """Convert a function to an OpenAI tool schema"""
    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__,
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
    
    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        # Skip self parameter for methods
        if param_name == 'self':
            continue
            
        param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
        schema["function"]["parameters"]["properties"][param_name] = {
            "type": "string",
            "description": ""
        }
        
        # Add required parameters
        if param.default == inspect.Parameter.empty:
            if "required" not in schema["function"]["parameters"]:
                schema["function"]["parameters"]["required"] = []
            schema["function"]["parameters"]["required"].append(param_name)
            
    return schema

def execute_tool_call(tool_call, tools, agent_name, messages):
    """Execute a tool call and handle agent transfers with context"""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    if name.startswith('get_') and name.endswith('_agent'):
        if 'work_done' not in args or not args['work_done']:
            content_messages = [m for m in messages if m['role'] in ('assistant', 'user')]
            if content_messages:
                args['work_done'] = ' '.join([m.get('content', '') for m in content_messages[-3:]])
    
    logger.info(f"Executing tool: {name} with args: {args}")
    result = tools[name](**args)
    logger.info(f"Tool execution result type: {type(result)}")
    return result

def run_full_turn(agent: Agent, messages: list) -> Response:
    current_agent = agent
    num_init_messages = len(messages)
    messages = messages.copy()
    max_retries = 2
    retry_count = 0

    # Add message truncation to prevent history from growing too large
    if len(messages) > 10:  # Keep only recent messages
        messages = messages[-10:]
        logger.info("Truncated message history to last 10 messages")

    while True:
        tool_schemas = [function_to_schema(tool) for tool in current_agent.tools]
        tools = {tool.__name__: tool for tool in current_agent.tools}

        logger.info(f"Making API call with agent: {current_agent.name}")
        logger.info(f"System prompt: {current_agent.instructions[:100]}...")
        
        # Prepare request payload
        request_payload = {
            'model': current_agent.model,
            'messages': [{"role": "system", "content": current_agent.instructions}] + messages,
            'tools': tool_schemas or None
        }
        
        try:
            response = client.chat.completions.create(**request_payload)
            
            if not response or not response.choices:
                raise Exception(f"Empty response received from API")
                
            message = response.choices[0].message
            if not message:
                raise Exception("No message in API response")

            logger.info(f"Received response from {agent.model}")
            logger.info(f"Response content: {message.content or 'No content'}")
            
            if message.tool_calls:
                logger.info(f"Tool calls requested: {[t.function.name for t in message.tool_calls]}")

            # Add message to history, handling None content
            message_dict = {
                "role": "assistant",
                "content": message.content or ""  # Convert None to empty string
            }
            
            if message.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            
            messages.append(message_dict)

            # Print non-empty content
            if message.content:
                print(f"{current_agent.name}: {message.content}")

            # Handle tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result = execute_tool_call(tool_call, tools, current_agent.name, messages)
                    
                    if isinstance(result, Agent):
                        logger.info(f"Agent transfer: {current_agent.name} → {result.name}")
                        current_agent = result
                        result = f"Transferred to {result.name}. Adopting new role."
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result or ""  # Convert None to empty string
                    })
            else:
                break

        except Exception as e:
            logger.error(f"Error in run_full_turn: {str(e)}")
            retry_count += 1
            if retry_count > max_retries:
                return Response(
                    agent=coordinator_agent,
                    messages=[{
                        "role": "assistant",
                        "content": "I encountered an error and need to restart with the coordinator."
                    }]
                )
            continue

    return Response(agent=current_agent, messages=messages[num_init_messages:])

# Agent definitions
coordinator_agent = Agent(
    name="Coordinator",
    instructions="""You are the coordination agent responsible for orchestrating the workflow.
    ALWAYS start by transferring new requests to the Researcher agent to gather information.
    
    When transferring to another agent, always include:
    1. work_done: A summary of what has been discovered/analyzed so far
    2. handoff: Clear instructions about what you want them to do next
    
    Workflow steps:
    1. Transfer to Researcher first (use get_researcher_agent)
    2. When research is complete, transfer to Analyst (use get_analyst_agent)
    3. After analysis, transfer to Writer (use get_writer_agent)
    4. Review final content from Writer
    5. Use final_outcome to present the complete report to the user

    Only use escalate_to_human for genuine emergencies or technical issues.
    
    Working on your team you have:
    a) a highly skilled researcher (use get_researcher_agent);
    b) an intelligent analyst (use get_analyst_agent);
    c) a skilled writer (use get_writer_agent);
    
    Your role is to make the best use of these talents to produce high quality work for the user.
    Always pass along the accumulated knowledge when transferring between agents.
    After using final_outcome, do not repeat the report content.
    
    IMPORTANT: When transferring work between agents:
    1. ALWAYS include the FULL detailed content from previous agents
    2. Do not summarize or condense previous work
    3. Add your own insights/directions in the handoff section
    4. Use markdown formatting to clearly separate previous work from new instructions""",
    tools=[get_researcher_agent, get_analyst_agent, get_writer_agent, escalate_to_human, final_outcome]
)

researcher_agent = Agent(
    name="Researcher",
    instructions="""You are the research agent specialized in gathering and validating information.
    You receive your instructions from the coordinator agent who manages the project and allocates tasks to your
    fellow colleague agents, including a writer agent and analyst agent.
    The coordinator agent will give you a briefing in the 'handoff' field and the the material you have to work with,
     in the 'work_done' field.
    - Conduct thorough research on topics
    - Verify information accuracy
    - Identify knowledge gaps
    Transfer to coordinator when your research task is complete or when you need clarification or any other assistance.
    Provide the outputs of your work in the 'work_done' field and include a message for the coordinator
    telling them what you have produced in the 'handoff' field.""",
    tools=[get_coordinator_agent]
)

analyst_agent = Agent(
    name="Analyst",
    instructions="""You are the analysis agent specialized in deep analysis and insights.
    You receive your instructions from the coordinator agent who manages the project and allocates tasks to your
    fellow colleague agents, including a research agent and writer agent.
    The coordinator agent will give you a briefing in the 'handoff' field and the the material you have to work with,
     in the 'work_done' field.
    - Analyze information and identify patterns
    - Draw conclusions and make recommendations
    - Provide strategic insights
    Transfer to coordinator when your analysis task is complete or when you need clarification or any other assistance.
    Provide the outputs of your work in the 'work_done' field and include a message for the coordinator
    telling them what you have produced in the 'handoff' field.""",
    tools=[get_coordinator_agent]
)

writer_agent = Agent(
    name="Writer",
    instructions="""You are the writing agent specialized in clear communication.
    You receive your instructions from the coordinator agent who manages the project and allocates tasks to your
    fellow colleague agents, including a research agent and analyst agent.
    The coordinator agent will give you a briefing in the 'handoff' field and the the material you have to work with,
     in the 'work_done' field.
    - Synthesize information from research and analysis
    - Create clear, engaging content
    - Adapt tone and style as needed
    Transfer to coordinator when your writing task is complete or when you need clarification or any other assistance.
    Provide the outputs of your work in the 'work_done' field and include a message for the coordinator
    telling them what you have produced in the 'handoff' field.""",
    tools=[get_coordinator_agent]
)

if __name__ == "__main__":
    client = OpenAI(
        base_url=os.getenv('API_BASE_URL'),
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    print("Start chatting! (type 'quit' to exit)")
    print("\nSuggested test: 'I need to understand the impact of AI on software development jobs. What are the current trends and future implications?'")
    
    agent = coordinator_agent
    messages = []

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() == 'quit':
            break

        messages.append({"role": "user", "content": user_input})
        try:
            response = run_full_turn(agent, messages)
            agent = response.agent
            messages.extend(response.messages)
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Transferring back to coordinator...")
            agent = coordinator_agent