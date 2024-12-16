# tools/brainstorm.py

import json
from typing import List, Dict, Any
from termcolor import colored

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

def execute(llm_client=None, brief: str = None, method: str = "six_hats") -> Dict[str, Any]:
    """
    Generate brainstorming ideas using various methods.
    
    Parameters:
    - brief (str): The topic or question to brainstorm about
    - method (str): Brainstorming method to use (defaults to six_hats)
    - llm_client: LLM client for generating ideas
    
    Returns:
    - dict: Tree structure of brainstorming results
    """
    if not llm_client or not brief:
        print(colored("Error: LLM client and brief are required", "red"))
        return {"error": "LLM client and brief are required"}

    try:
        # Validate method
        if method not in PROMPTS:
            print(colored(f"Invalid method. Using default (six_hats). Valid methods are: {', '.join(PROMPTS.keys())}", "yellow"))
            method = "six_hats"

        print(colored(f"\nStarting brainstorming session:", "cyan"))
        print(colored(f"Brief: {brief}", "cyan"))
        print(colored(f"Method: {method}", "cyan"))

        # Create root node
        root = TreeNode(brief)

        # Get initial ideas
        print(colored("\nGenerating initial ideas...", "blue"))
        initial_response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative brainstorming assistant."},
                {"role": "user", "content": f"Generate 5 initial ideas related to: {brief}. Present as bullet points."}
            ]
        )
        initial_ideas = parse_bullet_points(initial_response.choices[0].message.content)
        print(colored(f"Generated {len(initial_ideas)} initial ideas", "green"))

        # Process each initial idea
        for i, idea in enumerate(initial_ideas, 1):
            print(colored(f"\nProcessing initial idea {i}/{len(initial_ideas)}:", "blue"))
            print(colored(f"Idea: {idea}", "white"))
            
            idea_node = TreeNode(idea)
            root.add_child(idea_node)

            # Generate method-specific expansions
            print(colored(f"Applying {method} method...", "blue"))
            method_response = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative brainstorming assistant."},
                    {"role": "user", "content": PROMPTS[method].format(brief=idea)}
                ]
            )
            method_ideas = parse_bullet_points(method_response.choices[0].message.content)
            print(colored(f"Generated {len(method_ideas)} {method} ideas", "green"))

            # Add method-specific ideas
            for method_idea in method_ideas:
                method_node = TreeNode(method_idea)
                idea_node.add_child(method_node)

        print(colored("\nBrainstorming session completed successfully!", "green"))
        
        # Convert tree to JSON-friendly format
        result = print_tree(root)
        return {"result": result}

    except Exception as e:
        error_msg = f"Brainstorming failed: {str(e)}"
        print(colored(error_msg, "red"))
        return {"error": error_msg}

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_brainstorm",
        "description": "Generate creative ideas using various brainstorming techniques",
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
            "required": ["brief"]  # Only brief is required since method has a default
        }
    }
}