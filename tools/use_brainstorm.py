# tools/brainstorm.py

import json
from typing import List, Dict, Any
from termcolor import colored
from utils.ui_utils import update_spinner_status

class TreeNode:
    def __init__(self, content):
        self.content = content
        self.children = []

    def add_child(self, child):
        self.children.append(child)

def print_tree(node: TreeNode, level: int = 0) -> List[Dict[str, Any]]:
    """Convert tree structure to a list of dictionaries for JSON output"""
    result = {
        "content": node.content,
        "level": level,
        "children": []
    }
    
    for child in node.children:
        result["children"].append(print_tree(child, level + 1))
    
    return result

def parse_bullet_points(text: str) -> List[str]:
    """Extract bullet points from text response"""
    lines = text.strip().split('\n')
    points = [line.strip().lstrip('•-*').strip() for line in lines if line.strip().startswith(('•', '-', '*'))]
    return points if points else [text]  # Return full text if no bullet points found

PROMPTS = {
    "big_mind_mapping": """You are a clever idea expansion assistant that helps people expand one idea into 5 other related ideas. The resulting ideas should be diverse, detailed, developed, precise and significant. The ideas should not be redundant and repetitive, be creative and unique. The ideas must be formatted in the form of bullet points.

Brief to expand: {brief}
List 5 bullet points:""",

    "reverse_brainstorming": """You are a perceptive problem-identification assistant that helps people analyze an idea by uncovering 5 potential issues or challenges it may encounter. The identified problems should be diverse, detailed, well-developed, precise, and significant. Avoid redundancy and repetition; ensure the problems are creative and unique. Present the problems in bullet points.

Brief to analyze: {brief}
List 5 potential problems:""",

    "role_storming": """Generate 5 unique ideas based on the topic provided, with each idea coming from a different perspective:
- Overly Positive Persona
- Overly Negative Persona
- Curious Child
- Skeptical Analyst
- Visionary Futurist

Brief to analyze: {brief}
List 5 role-based perspectives in bullet points:""",

    "scamper": """Generate ideas using the SCAMPER method (Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse). For each SCAMPER element, generate one creative idea based on the brief provided. Present ideas in bullet points.

Brief to analyze: {brief}
List 7 SCAMPER ideas:""",

    "six_hats": """Analyze the topic using Six Thinking Hats method:
- White Hat (Facts)
- Red Hat (Emotions)
- Black Hat (Risks)
- Yellow Hat (Benefits)
- Green Hat (Creativity)
- Blue Hat (Process)

Brief to analyze: {brief}
List 6 perspectives in bullet points:""",

    "starbursting": """Generate questions using the 5 W's and 1 H method:
- Who
- What
- Where
- When
- Why
- How

Brief to analyze: {brief}
List 6 key questions in bullet points:"""
}


def tree_to_markdown(node: dict, level: int = 0) -> str:
    """
    Recursively converts a tree structure into a Markdown-formatted string.
    """
    # Use `#` for headers for the root and `-` for child points
    indent = "  " * level  # Indentation for nested levels
    if level == 0:
        # Top-level idea as a Markdown header
        markdown = f"# {node['content']}\n\n"
    else:
        # Nested levels as bullet points
        markdown = f"{indent}- **{node['content']}**\n"
    
    # Recursively add children
    for child in node.get("children", []):
        markdown += tree_to_markdown(child, level + 1)
    
    return markdown

def execute(llm_client=None, brief: str = None, method: str = "six_hats") -> str:
    """
    Generate brainstorming ideas using various methods and return Markdown-formatted output.
    """
    if not llm_client or not brief:
        return "Error: LLM client and brief are required."

    try:
        # Validate method
        if method not in PROMPTS:
            method = "six_hats"  # Default to Six Thinking Hats

        # Create root node
        root = TreeNode(brief)

        # Generate initial ideas
        update_spinner_status("Generating initial ideas...")
        print(colored("Generating initial ideas...", "green"))
        initial_response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative brainstorming assistant."},
                {"role": "user", "content": f"Generate 5 initial ideas related to: {brief}. Present as bullet points."}
            ]
        )
        initial_ideas = parse_bullet_points(initial_response.choices[0].message.content)
        update_spinner_status(f"Received {len(initial_ideas)} initial ideas.")
        print(colored(f"Received {len(initial_ideas)} initial ideas.", "green"))

        # Process each idea
        for i, idea in enumerate(initial_ideas, 1):
            idea_node = TreeNode(idea)
            root.add_child(idea_node)
            update_spinner_status(f"Processing idea {i} of {len(initial_ideas)}: {idea}")
            print(colored(f"Processing idea {i} of {len(initial_ideas)}: {idea}", "green"))

            # Generate expansions for each idea using the specified method
            method_response = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative brainstorming assistant."},
                    {"role": "user", "content": PROMPTS[method].format(brief=idea)}
                ]
            )
            method_ideas = parse_bullet_points(method_response.choices[0].message.content)

            # Add expanded ideas as children
            for method_idea in method_ideas:
                method_node = TreeNode(method_idea)
                idea_node.add_child(method_node)

        # Convert the tree to Markdown
        update_spinner_status("Converting tree to Markdown...")
        print(colored("Converting tree to Markdown...", "green"))
        tree_result = print_tree(root)  # JSON-like tree structure
        markdown_result = tree_to_markdown(tree_result)  # Clean Markdown output
        update_spinner_status("Markdown conversion complete.")
        print(colored("Markdown conversion complete.", "green"))
        return markdown_result

    except Exception as e:
        update_spinner_status(f"Error occurred: {str(e)}")
        print(colored(f"Error occurred: {str(e)}", "red"))
        return f"Error: {str(e)}"

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_brainstorm",
        "description": "Generate creative ideas using various brainstorming techniques. Respond with clean markdown format.",
        "parameters": {
            "type": "object",
            "properties": {
                "brief": {
                    "type": "string",
                    "description": "The topic, question, or problem to brainstorm about"
                },
                "method": {
                    "type": "string",
                    "description": "The brainstorming method to use (defaults to six_hats)",
                    "enum": [
                        "big_mind_mapping",
                        "reverse_brainstorming",
                        "role_storming",
                        "scamper",
                        "six_hats",
                        "starbursting"
                    ]
                }
            },
            "required": ["brief"]
        }
    },
    "direct_stream": True
}