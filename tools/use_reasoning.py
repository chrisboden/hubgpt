# tools/sequential_thinking.py

import json
from typing import Any, Dict, Optional, List
from termcolor import colored

class ThoughtData:
    def __init__(
        self,
        thought: str,
        thoughtNumber: int,
        totalThoughts: int,
        nextThoughtNeeded: bool,
        isRevision: bool = False,
        revisesThought: Optional[int] = None,
        branchFromThought: Optional[int] = None,
        branchId: Optional[str] = None,
        needsMoreThoughts: bool = False
    ):
        self.thought = thought
        self.thoughtNumber = thoughtNumber
        self.totalThoughts = totalThoughts
        self.nextThoughtNeeded = nextThoughtNeeded
        self.isRevision = isRevision
        self.revisesThought = revisesThought
        self.branchFromThought = branchFromThought
        self.branchId = branchId
        self.needsMoreThoughts = needsMoreThoughts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought": self.thought,
            "thoughtNumber": self.thoughtNumber,
            "totalThoughts": self.totalThoughts,
            "nextThoughtNeeded": self.nextThoughtNeeded,
            "isRevision": self.isRevision,
            "revisesThought": self.revisesThought,
            "branchFromThought": self.branchFromThought,
            "branchId": self.branchId,
            "needsMoreThoughts": self.needsMoreThoughts
        }

class SequentialThinkingTool:
    def __init__(self):
        # In a longer-running system, you may want to persist this somewhere
        self.thoughtHistory: List[ThoughtData] = []
        self.branches: Dict[str, List[ThoughtData]] = {}

    def validate_params(
        self,
        thought: str,
        nextThoughtNeeded: bool,
        thoughtNumber: int,
        totalThoughts: int,
        isRevision: bool,
        revisesThought: Optional[int],
        branchFromThought: Optional[int],
        branchId: Optional[str],
        needsMoreThoughts: bool
    ):
        if not isinstance(thought, str):
            raise ValueError("thought must be a string")
        if not isinstance(nextThoughtNeeded, bool):
            raise ValueError("nextThoughtNeeded must be a boolean")
        if not isinstance(thoughtNumber, int) or thoughtNumber < 1:
            raise ValueError("thoughtNumber must be an integer >= 1")
        if not isinstance(totalThoughts, int) or totalThoughts < 1:
            raise ValueError("totalThoughts must be an integer >= 1")

    def format_thought(self, td: ThoughtData) -> str:
        prefix, context = "", ""
        if td.isRevision:
            prefix = colored('🔄 Revision', 'yellow')
            context = f" (revising thought {td.revisesThought})" if td.revisesThought else ""
        elif td.branchFromThought:
            prefix = colored('🌿 Branch', 'green')
            context = f" (from thought {td.branchFromThought}, ID: {td.branchId})"
        else:
            prefix = colored('💭 Thought', 'blue')

        header = f"{prefix} {td.thoughtNumber}/{td.totalThoughts}{context}"
        line_len = max(len(header), len(td.thought)) + 4
        border = '─' * line_len
        return (
            f"\n┌{border}┐\n"
            f"│ {header}{' ' * (line_len - len(header) - 1)}│\n"
            f"├{border}┤\n"
            f"│ {td.thought}{' ' * (line_len - len(td.thought) - 1)}│\n"
            f"└{border}┘\n"
        )

    def add_thought(self, td: ThoughtData):
        if td.thoughtNumber > td.totalThoughts:
            td.totalThoughts = td.thoughtNumber
        self.thoughtHistory.append(td)
        if td.branchFromThought and td.branchId:
            if td.branchId not in self.branches:
                self.branches[td.branchId] = []
            self.branches[td.branchId].append(td)

        # Print formatted block
        formatted = self.format_thought(td)
        print(colored(formatted, "white"))

    def suggest_next_thought(self, llm_client: Any) -> Optional[str]:
        """
        If desired, prompt the LLM to suggest the next thought.
        This is optional and depends on if llm_client is provided and nextThoughtNeeded is True.
        We'll feed in some context from the last few thoughts.
        """
        if not llm_client:
            return None

        # You can decide how to prompt the LLM here. For simplicity, let's just feed it the last thought.
        last_thought = self.thoughtHistory[-1] if self.thoughtHistory else None
        if not last_thought:
            return None

        prompt = f"""
You are engaged in a chain-of-thought reasoning process. The last thought was:

{last_thought.thought}

Based on the reasoning so far, suggest the next best thought. Be concise and focus on logical continuity.
"""
        response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a reasoning assistant."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def build_response(self) -> Dict[str, Any]:
        return {
            "thoughtHistoryLength": len(self.thoughtHistory),
            "branches": list(self.branches.keys()),
            "currentThought": self.thoughtHistory[-1].to_dict() if self.thoughtHistory else None
        }

thinking_tool = SequentialThinkingTool()

def execute(
    llm_client: Any = None,
    thought: str = None,
    nextThoughtNeeded: bool = None,
    thoughtNumber: int = None,
    totalThoughts: int = None,
    isRevision: bool = False,
    revisesThought: int = None,
    branchFromThought: int = None,
    branchId: str = None,
    needsMoreThoughts: bool = False
) -> Dict[str, Any]:
    """
    Refactored Sequential Thinking Tool

    This tool supports a self-directed, iterative reasoning process. It keeps track of a chain of thoughts,
    supports branching and revision, and can optionally use the LLM to propose the next thought if needed.

    Parameters:
    - llm_client: LLM client (optional). If provided and nextThoughtNeeded is True, it can suggest the next thought.
    - thought: The current reasoning step.
    - nextThoughtNeeded: Boolean indicating if another thought step is needed.
    - thoughtNumber: The current thought number in the sequence.
    - totalThoughts: The current estimate of total thoughts needed.
    - isRevision: True if this is a revision of a previous thought.
    - revisesThought: Which thought number is being revised (if applicable).
    - branchFromThought: If branching, which thought number is the source.
    - branchId: Identifier for the branch.
    - needsMoreThoughts: True if we realize we need more thoughts beyond the original estimate.

    Returns:
    A dictionary with the current state and possibly the suggestion for the next thought.
    """

    try:
        thinking_tool.validate_params(
            thought, nextThoughtNeeded, thoughtNumber, totalThoughts,
            isRevision, revisesThought, branchFromThought, branchId, needsMoreThoughts
        )

        # Create the ThoughtData object
        td = ThoughtData(
            thought=thought,
            thoughtNumber=thoughtNumber,
            totalThoughts=totalThoughts,
            nextThoughtNeeded=nextThoughtNeeded,
            isRevision=isRevision,
            revisesThought=revisesThought,
            branchFromThought=branchFromThought,
            branchId=branchId,
            needsMoreThoughts=needsMoreThoughts
        )

        # Add the thought to the history
        thinking_tool.add_thought(td)

        # If more thoughts are needed and llm_client is available, try to suggest next thought
        suggestion = None
        if nextThoughtNeeded and llm_client:
            suggestion = thinking_tool.suggest_next_thought(llm_client)

        response = thinking_tool.build_response()
        if suggestion:
            response["suggestedNextThought"] = suggestion

        return {"result": response}

    except Exception as e:
        return {"error": str(e)}

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_sequential_thinking",
        "description": (
            "A tool for dynamic, reflective, and self-directed sequential reasoning. "
            "It stores a chain of thoughts, supports revisions and branching, and can "
            "optionally suggest next steps using an LLM if needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Your current thinking step"
                },
                "nextThoughtNeeded": {
                    "type": "boolean",
                    "description": "Whether another thought step is needed"
                },
                "thoughtNumber": {
                    "type": "integer",
                    "description": "Current thought number (>=1)"
                },
                "totalThoughts": {
                    "type": "integer",
                    "description": "Estimated total thoughts needed (>=1)"
                },
                "isRevision": {
                    "type": "boolean",
                    "description": "Whether this is a revision of a previous thought"
                },
                "revisesThought": {
                    "type": "integer",
                    "description": "Which thought number is being revised"
                },
                "branchFromThought": {
                    "type": "integer",
                    "description": "If branching, which thought number is the source"
                },
                "branchId": {
                    "type": "string",
                    "description": "Identifier for the current branch"
                },
                "needsMoreThoughts": {
                    "type": "boolean",
                    "description": "If we realize we need more thoughts than originally estimated"
                }
            },
            "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
        }
    },
    "direct_stream": True
}