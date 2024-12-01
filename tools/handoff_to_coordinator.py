# tools/handoff_to_coordinator.py

def execute(handoff: str, work_done: str, llm_client=None, **kwargs):
    """
    Hands work back to the coordinator agent.
    
    Args:
        handoff (str): Message explaining what was done and what needs to happen next
        work_done (str): The complete output from the work done
        llm_client (optional): Ignored but accepted for consistency
        **kwargs: Additional arguments are ignored for flexibility
    """
    # Implementation remains the same
    return {
        "status": "success",
        "message": "Handing back to coordinator"
    }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "handoff_to_coordinator",
        "description": "Use this to hand work back to the coordinator agent when you have completed your part",
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