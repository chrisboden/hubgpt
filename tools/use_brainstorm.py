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

    "role_storming": """You are a clever idea generator assistant that helps people brainstorm and generate ideas using the Role Storming method. This involves adopting various personas to generate diverse perspectives and enrich the brainstorming process. Each persona brings a unique approach, exploring different angles and highlighting creative possibilities.

Here’s an explanation of each persona's perspective:

- Overly Positive Persona: Enthusiastically embraces every aspect of the topic, looking for the best-case scenarios and highlighting optimistic outcomes. They encourage unbridled creativity and focus on the potential for success.
  
- Overly Negative Persona: Views the topic critically, focusing on potential pitfalls, risks, and drawbacks. This persona helps in identifying challenges and preparing solutions for potential failures or issues.

- Curious Child: Approaches the topic with pure curiosity, asking "why" and "what if" questions. They explore without limitations, bringing fresh, out-of-the-box ideas that challenge existing assumptions.

- Skeptical Analyst: Takes a detailed, logical approach, questioning every part of the topic to uncover weaknesses or risks. This persona brings depth to the analysis, ensuring that ideas are well thought out and practical.

- Visionary Futurist: Considers the long-term implications and future possibilities of the topic, imagining how it could evolve. They focus on innovative, forward-thinking perspectives, pushing boundaries and considering future trends.

Generate 5 unique ideas based on the topic provided, with each idea presented in a bullet point and link each idea to its persona’s distinct approach, exploring the topic comprehensively. Format the list in bullet points without titles or bold text.

Brief to analyze: {brief}
List 5 role-based perspectives in bullet points:""",

    "scamper": """You are a clever idea generator assistant that helps people brainstorm and generate new ideas using the SCAMPER method. SCAMPER is an activity-based thinking process that assists in developing an idea through a structured approach. Here’s how each step in SCAMPER works:

- Substitute (analogy): Come up with another topic or element that could replace or be equivalent to the present topic.
- Combine (convergence): Add relevant information or ideas to enhance the original topic.
- Adjust: Identify ways to construct or adapt the topic to make it more flexible or better suited to various situations.
- Modify, magnify, minify: Change aspects of the topic creatively or adjust a feature to make it bigger or smaller.
- Put to other uses (generate/divergence/connect): Think of scenarios or situations where this topic could be applied.
- Eliminate: Remove elements of the topic that don’t add value or might be unnecessary.
- Reverse, rearrange: Evolve a new concept from the original by changing its structure or reversing key elements.

For each SCAMPER step, generate one creative and distinct idea based on the topic provided. Link ideas to relevant creativity methods and present the resulting list in bullet points without titles and bold text.

Brief to analyze: {brief}
List 7 SCAMPER ideas:""",

    "six_hats": """You are a perceptive brainstorming assistant that helps people analyze an idea using the Six Thinking Hats method, developed by Edward de Bono. This method involves examining a topic from six distinct perspectives, each represented by a colored hat. Here’s how each hat works:

- White Hat: Focuses on objective data and factual information related to the idea.
- Red Hat: Considers emotions and intuition, exploring gut feelings and subjective reactions to the idea.
- Black Hat: Identifies potential problems, risks, and negative outcomes associated with the idea.
- Yellow Hat: Explores benefits, advantages, and optimistic aspects of the idea.
- Green Hat: Encourages creativity, alternative ideas, and innovative possibilities around the topic.
- Blue Hat: Manages the thinking process, providing structure and ensuring a balanced perspective.

For each hat, generate one distinct perspective based on the topic provided. Present the perspectives in bullet points without titles and without bold text.

Brief to analyze: {brief}
List 6 perspectives in bullet points:""",

    "starbursting": """You are a clever question generator assistant that helps people in brainstorming and generating from one idea to 6 questions following the starbursting brainstorming principles: the 5 W's and 1 H (Who, What, Where, When, Why, How) to explore a topic comprehensively. The resulting questions should be diverse, detailed, developed, precise and significant. The questions must not be redundant and repetitive, be creative and unique. The question must be formatted in the form of bullet points without titles and without bold text.

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
                {"role": "system", "content": "You are a highly experienced consultant from IDEO who worked on some of the leading projects at Apple, Tesla, Dyson and Google X. You have deep expertise in using the most effective brainstorming techniques."},
                {"role": "user", "content": f"Generate 5 initial ideas related to: {brief}. Present as bullet points."}
            ]
        )
        initial_ideas = parse_bullet_points(initial_response.choices[0].message.content)
        update_spinner_status(f"Received {len(initial_ideas)} initial ideas.")
        print(colored(f"Received {len(initial_ideas)} initial ideas.", "green"))

        # Process each initial idea
        for i, idea in enumerate(initial_ideas, 1):
            print(colored(f"\nProcessing initial idea {i}/{len(initial_ideas)}:", "blue"))
            update_spinner_status(f"Processing idea {i} of {len(initial_ideas)}: {idea}")
            print(colored(f"Processing idea {i} of {len(initial_ideas)}: {idea}", "green"))
            print(colored(f"Idea: {idea}", "cyan"))
            
            idea_node = TreeNode(idea)
            root.add_child(idea_node)

            # Generate method-specific expansions
            print(colored(f"Applying {method} method...", "blue"))
            update_spinner_status(f"Applying {method} method...")

            method_response = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a highly experienced consultant from Frog Design who worked on some of the leading projects at Apple, Tesla, Dyson and Google X. You have deep expertise in using the most effective brainstorming techniques."},
                    {"role": "user", "content": PROMPTS[method].format(brief=idea)}
                ]
            )
            method_ideas = parse_bullet_points(method_response.choices[0].message.content)
            update_spinner_status(f"Generated {len(method_ideas)} {method} ideas")
            print(colored(f"Generated {len(method_ideas)} {method} ideas", "green"))

            # Add method-specific ideas
            for method_idea in method_ideas:
                method_node = TreeNode(method_idea)
                idea_node.add_child(method_node)

        print(colored("\nBrainstorming session completed successfully!", "green"))
        update_spinner_status(f"Brainstorming session completed successfully!")
        
        # Convert tree to JSON-friendly format
        result = print_tree(root)
        return {"result": result}

    except Exception as e:
        update_spinner_status(f"Brainstorming error!")
        error_msg = f"Brainstorming failed: {str(e)}"
        print(colored(error_msg, "red"))
        return {"error": error_msg}

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_brainstorm",
        "description": "Generate creative ideas using various brainstorming techniques. Respond with a clean markdown format that presents the ideas in the most useful format for the user. Methods: Reverse brainstorming involves identifying ways to cause a problem or achieve the opposite effect. Perfect for spotting potential issues and coming up with innovative solutions. Role storming adopting the perspective of someone else to generate ideas. Great for gathering insights from different viewpoints. SCAMPER stands for Substitute, Combine, Adapt, Modify, Put to another use, Eliminate, and Reverse. It encourages thinking from multiple perspectives to generate diverse ideas. Edward de Bono, looks at a problem from six different perspectives - White (Data), Red (Emotions), Black (Risks), Yellow (Benefits), Green (Creativity), and Blue (Process management). Focuses on generating questions rather than answers using the 5 W's and 1 H (Who, What, Where, When, Why, How). Ideal for comprehensive topic exploration.",
        "parameters": {
            "type": "object",
            "properties": {
                "brief": {
                    "type": "string",
                    "description": "The topic, question, or problem to brainstorm about"
                },
                "method": {
                    "type": "string",
                    "description": "The brainstorming method to use (defaults to six_hats).",
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