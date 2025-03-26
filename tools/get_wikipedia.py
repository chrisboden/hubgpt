import requests
from urllib.parse import quote, parse_qs, urlparse
import wikipediaapi

def page_to_markdown(page):
    """Convert a wikipediaapi page object to Markdown format."""
    md_content = f"# {page.title}\n\n"  # Page title as the main header

    def section_to_md(section, level=1):
        # Create Markdown header based on the section level
        md_text = f"{'#' * (level + 1)} {section.title}\n\n{section.text}\n\n"
        for subsection in section.sections:
            md_text += section_to_md(subsection, level + 1)
        return md_text

    # Convert each top-level section
    for section in page.sections:
        md_content += section_to_md(section)
    
    print(f"The markdown content is:\n\n{md_content}")
    return md_content

def execute(term, llm_client):
    """
    Retrieve the full Wikipedia content for a given search term in Markdown format.
    Process the content using the LLM for summarisation or detailed response.

    Parameters:
    - term (str): The search term to find on Wikipedia.
    - llm_client: An LLM client for generating additional context.

    Returns:
    - dict: A dictionary containing the title and processed summary from the LLM.
    """
    if not term:
        raise ValueError("The term parameter is required")

    # Construct the Google "I'm Feeling Lucky" search URL
    search_url = f"https://www.google.com/search?q=site:en.wikipedia.org%20{quote(term)}&btnI=Im+Feeling+Lucky"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # Perform the initial GET request to Google with no redirection
        response = requests.get(search_url, headers=headers, allow_redirects=False)
        
        # If Google provides a redirect URL (302 status), extract the Wikipedia article title
        if response.status_code == 302:
            redirect_url = response.headers.get("Location", "")
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)

            # Extract the target URL from the Google redirect
            target_url = query_params.get("q", [None])[0]
            if target_url and "wikipedia.org" in target_url:
                # Extract the article title from the Wikipedia URL
                article_title = target_url.split("/")[-1].replace("_", " ")
                
                # Configure wikipedia-api with a user-agent
                wiki_wiki = wikipediaapi.Wikipedia(
                    language="en",
                    user_agent="phub/1.0 (https://peregianhub.com.au)"
                )
                
                # Fetch the Wikipedia page content
                page = wiki_wiki.page(article_title)
                
                if page.exists():
                    # Convert page to Markdown
                    content_md = page_to_markdown(page)

                    # Always send content to LLM for summarisation
                    messages = [
                        {"role": "system", "content": "You are WIKI-SCHOLAR, an expert at extracting and presenting Wikipedia article content with exceptional attention to detail and narrative completeness. Your role is to provide rich, comprehensive information while maintaining clarity and proper organization.\n\nCORE DIRECTIVES:\n- Present the full depth of the subject matter, not just superficial summaries\n- Preserve important historical context, developments, and significance\n- Maintain academic neutrality and include multiple perspectives\n- Include relevant dates, figures, and specific details\n- Exclude meta-elements like edit notices, reference markers, or external link sections\n- Organize content logically while preserving narrative flow\n\nFORMAT GUIDELINES:\n1. Begin with a thorough overview\n2. Use hierarchical organization:\n   - Major sections with descriptive headers\n   - Subsections for detailed exploration\n   - Chronological ordering where appropriate\n3. Include significant:\n   - Dates and timelines\n   - Key figures and their contributions\n   - Critical developments and turning points\n4. Preserve important debates or controversies\n5. Maintain academic tone while ensuring readability\n\nQUALITY STANDARDS:\n- Never oversimplify complex topics\n- Include specific examples and illustrations\n- Present competing theories or interpretations where relevant\n- Maintain historical context\n- Preserve nuance in scientific or technical discussions\n\nRemem  ber: Your role is to provide thorough, well-organized information that captures the full depth and complexity of the subject matter. When in doubt, include more detail rather than less, but maintain clear organization and readability."},
                        {"role": "user", "content": f"Wikipedia article content:\n\n{content_md}"}
                    ]
                    try:
                        response = llm_client.chat.completions.create(
                            model="google/gemini-2.0-flash-001",
                            messages=messages,
                            max_tokens=3000,
                            temperature=1
                        )
                        print(messages)
                        summary = response.choices[0].message.content.strip()
                        print(f"The LLM processed summary is:\n\n {summary}")
                        return {"title": page.title, "summary": summary}
                        
                    except Exception as e:
                        # If there’s an error during LLM processing, return the Markdown content with an error message
                        error_response = {"title": page.title, "content": content_md, "error": "Failed to generate summary."}
                        print(f"Final output from execute function (error case):\n\n{error_response}")
                        return error_response
                
                else:
                    raise ValueError("Wikipedia article does not exist.")
            else:
                raise ValueError("No valid Wikipedia URL found in the Google redirect.")
        else:
            raise ValueError("Google did not return a redirect as expected.")
    
    except requests.RequestException as e:
        raise RuntimeError(f"An error occurred: {e}")

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_wikipedia",
        "description": "Retrieve comprehensive Wikipedia content for a given search term and use that content to provide an information dense response to the user. Response MUST be >500 words",
        "parameters": {
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "The search term to look up on Wikipedia."
                }
            },
            "required": ["term"]
        }
    }
}
