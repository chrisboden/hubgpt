# tools/handoff_to_agent.py

def execute(agent_name: str, handoff: str, work_done: str = "", llm_client=None, **kwargs):
    """
    Hands off work to another agent.
    
    Args:
        agent_name (str): Name of the agent to hand off to
        handoff (str): Message explaining what work needs to be done
        work_done (str, optional): Work completed so far
        llm_client (optional): Ignored but accepted for consistency
        **kwargs: Additional arguments are ignored for flexibility
    """

    return {
        "status": "success",
        "message": f"Handing off to {agent_name}"
    }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "handoff_to_agent",
        "description": "Use this to hand off work to another agent when their expertise is needed",
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
                }
            },
            "required": ["agent_name", "handoff"]
        }
    }
}