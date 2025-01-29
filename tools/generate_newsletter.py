# tools/generate_newsletter.py
import json
import logging
from termcolor import colored
from typing import Dict, List
from utils import prompt_utils
from utils.log_utils import log_llm_request, log_llm_response

def execute(llm_client=None, theme: str = None, target_audience: str = "tech founders", authors: List[str] = None):
    """Generates a weekly newsletter by coordinating multiple AI authors and curating their inputs."""
    print(colored("Starting newsletter generation tool", "cyan"))
    
    try:
        # Validate inputs first
        if not llm_client:
            raise ValueError("LLM client is required")
        if not theme:
            raise ValueError("Theme parameter is required")
        
        # Step 1: Author prompt generation
        print(colored("\n=== PHASE 1: Author Prompt Generation ===", "yellow"))
        author_prompts = _generate_author_prompts(llm_client, theme, target_audience)
        
        # Step 2: Content generation from AI authors
        print(colored("\n=== PHASE 2: Content Collection ===", "yellow"))
        raw_insights = _query_ai_authors(llm_client, author_prompts)
        
        # Step 3: Content synthesis
        print(colored("\n=== PHASE 3: Content Synthesis ===", "yellow"))
        newsletter_draft = _synthesize_content(llm_client, raw_insights, theme)
        
        # Step 4: Quality assurance
        print(colored("\n=== PHASE 4: Quality Check ===", "yellow"))
        final_output = _perform_quality_check(llm_client, newsletter_draft)
        
        return {
            "result": final_output,
            "status": "success"
        }

    except ValueError as ve:
        return {
            "error": str(ve),
            "status": "invalid_input"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

def _generate_author_prompts(llm_client, theme: str, audience: str) -> List[Dict]:
    """Use LLM to generate author prompts based on book list and theme"""
    print(colored("Generating author prompts with LLM...", "yellow"))
    
    # Load book data
    with open("repo_tools/book_list.json", "r") as f:
        books = json.load(f)
    
    # Get unique authors
    authors = list({f"{b['author']}": b for b in books}.values())
    author_list = "\n".join([f"- {b['author']} ({b['title']})" for b in authors])

    # Create LLM prompt
    prompt = f"""Generate expert prompts for newsletter authors based on this theme: {theme}
Target audience: {audience}

Available authors and their key books:
{author_list}

For each relevant author:
1. Identify how their expertise relates to the theme
2. Create a specific prompt that extracts actionable insights from their work
3. Focus on practical advice for {audience}

Output JSON format:
{{
    "prompts": [
        {{
            "author": "Author Name",
            "prompt": "Detailed prompt text..."
        }}
    ]
}}"""

    try:
        response = llm_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate response structure
        if "prompts" not in result or not isinstance(result["prompts"], list):
            raise ValueError("Invalid response structure from LLM")
            
        valid_authors = [
            "Daniel_Kahneman", "Nassim_Taleb", "Peter_Thiel",
            "Matt_Ridley", "David_Deutsch", "Yuval_Harari"
        ]
        
        # Filter LLM-suggested authors to only valid ones
        filtered_prompts = [p for p in result["prompts"] if p["author"] in valid_authors]
        
        return filtered_prompts or default_authors_prompts
        
    except Exception as e:
        print(colored(f"LLM prompt generation failed: {str(e)}", "red"))
        print(colored("Falling back to default authors", "yellow"))
        
        # Fallback to default authors
        default_authors = [
            "Daniel_Kahneman",
            "Nassim_Taleb",
            "Peter_Thiel",
            "Matt_Ridley"
        ]
        return [{
            "author": author,
            "prompt": f"Provide your most valuable insights about {theme} from your published works, focusing on practical advice for {audience}."
        } for author in default_authors]

def _query_ai_authors(llm_client, prompts: List[Dict]) -> List[str]:
    """Query multiple AI authors using their respective advisor profiles"""
    insights = []
    
    for prompt in prompts:
        try:
            print(colored(f"\nQuerying {prompt['author']}...", "blue"))
            response = _query_ai_advisor(llm_client, prompt["author"], prompt["prompt"])
            insights.append({
                "author": prompt["author"],
                "content": response
            })
        except Exception as e:
            print(colored(f"Error querying {prompt['author']}: {str(e)}", "red"))
            insights.append({
                "author": prompt["author"],
                "error": str(e)
            })
    
    return insights

def _query_ai_advisor(llm_client, advisor_name: str, prompt: str) -> str:
    """Query a specific AI advisor using their prompt template"""
    try:
        print(colored(f"Querying advisor: {advisor_name}", "blue"))
        
        # Normalize advisor name
        normalized_name = advisor_name.replace(" ", "_").replace("-", "_").lower()
        
        # Load advisor data
        try:
            advisor_data = prompt_utils.load_advisor_data(normalized_name)
        except FileNotFoundError:
            print(colored(f"Advisor not found: {normalized_name}", "red"))
            return f"Advisor {normalized_name} unavailable"
            
        messages = advisor_data.get("messages", []) + [{"role": "user", "content": prompt}]
        
        # Create API parameters
        api_params = {
            "model": advisor_data.get('model', 'openai/gpt-4o-mini'),
            "messages": messages,
            "temperature": advisor_data.get('temperature', 0.7),
            "max_tokens": advisor_data.get('max_output_tokens', 1500),
            "stream": False
        }
        
        # Log the request
        log_llm_request(api_params)
        response = llm_client.chat.completions.create(**api_params)
        log_llm_response({"advisor": advisor_name, "response": response})
        
        return response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"Advisor query failed: {advisor_name} - {str(e)}")
        raise

def _synthesize_content(llm_client, insights: List[Dict], theme: str) -> str:
    """Synthesize multiple author insights into a coherent draft"""
    synthesis_prompt = f"""Synthesize these author insights into a newsletter about {theme}:

{json.dumps(insights, indent=2)}

Guidelines:
1. Remove redundant concepts
2. Maintain original insights' core meaning
3. Create logical flow between sections
4. Add engaging introduction and conclusion
5. Keep language accessible"""

    response = llm_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": synthesis_prompt}],
        temperature=0.5,
        max_tokens=3000
    )
    
    return response.choices[0].message.content

def _perform_quality_check(llm_client, draft: str) -> str:
    """Perform final quality assurance check"""
    qa_prompt = f"""Critique this newsletter draft:
{draft}

Evaluate for:
1. Clarity of concepts
2. Actionability of advice
3. Engagement potential
4. Missing perspectives

Suggest 3 concrete improvements."""

    response = llm_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": qa_prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    
    return f"Final Newsletter:\n\n{draft}\n\nEdits Suggested:\n{response.choices[0].message.content}"

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "generate_newsletter",
        "description": "Generates curated newsletters by coordinating multiple AI authors and synthesizing their insights",
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string", 
                    "description": "Central theme/topic for the newsletter"
                },
                "target_audience": {
                    "type": "string",
                    "description": "Primary audience for the content",
                    "enum": ["tech founders", "digital professionals", "remote workers"]
                },
                "authors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of author advisors to include"
                }
            },
            "required": ["theme"]
        }
    },
    "direct_stream": True
} 