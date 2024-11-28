# team_tools.py

import logging

# Configure logging
logger = logging.getLogger(__name__)

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

def escalate_to_human(summary: str) -> str:
    """
    Escalate complex issues to human oversight

    Args:
        summary: A brief summary of the issue that needs human attention
    Returns:
        Confirmation message
    """
    print("\n=== Human Escalation Required ===")
    print(f"Summary: {summary}")
    print("================================\n")
    return "Escalated to human supervisor"

def get_researcher_agent(work_done: str = "", handoff: str = "", agents_dict=None) -> 'Agent':
    """
    Transfer work to the researcher agent

    Args:
        work_done: The content or material that you want the researcher agent to use in their work.
        handoff: The briefing you give to the researcher agent with respect to their task.
        agents_dict: Dictionary of agent instances.
    Returns:
        Researcher agent instance
    """
    logger.info(f"Transferring to researcher with work: {work_done[:100]}...")
    return agents_dict["Researcher"]

def get_analyst_agent(work_done: str = "", handoff: str = "", agents_dict=None) -> 'Agent':
    """
    Transfer work to the analyst agent

    Args:
        work_done: The content or material that you want the analyst agent to use in their work.
        handoff: The briefing message you wish to give to the analyst agent to instruct them on the task you need done.
        agents_dict: Dictionary of agent instances.
    Returns:
        Analyst agent instance
    """
    logger.info(f"Transferring to analyst with work: {work_done[:100]}...")
    return agents_dict["Analyst"]

def get_writer_agent(work_done: str = "", handoff: str = "", agents_dict=None) -> 'Agent':
    """
    Transfer work to the writer agent

    Args:
        work_done: The content or material that you want the writer agent to use in their work.
        handoff: The briefing message you wish to give to the writer agent to instruct them on the task you need done.
        agents_dict: Dictionary of agent instances.
    Returns:
        Writer agent instance
    """
    logger.info(f"Transferring to writer with work: {work_done[:100]}...")
    return agents_dict["Writer"]

def get_coordinator_agent(work_done: str = "", handoff: str = "", agents_dict=None) -> 'Agent':
    """
    Transfer work to the coordinator agent

    Args:
        work_done: The output from the task you have just completed.
        handoff: Your message to the coordinator explaining the work you have done.
        agents_dict: Dictionary of agent instances.
    Returns:
        Coordinator agent instance
    """
    logger.info(f"Transferring to coordinator with work: {work_done[:100]}...")
    return agents_dict["Coordinator"]