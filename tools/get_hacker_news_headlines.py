# tools/get_hacker_news_headlines.py
import requests
from bs4 import BeautifulSoup
import logging

def execute(llm_client=None, limit=10):
    """
    Fetch the top headlines from Hacker News.

    Parameters:
    - limit (int): Number of headlines to retrieve (default: 10)
    - llm_client (optional): An LLM client for generating additional context

    Returns:
    - dict: A dictionary containing top headlines with titles, links, and optional descriptions
    """
    try:
        # Fetch Hacker News homepage
        url = "https://news.ycombinator.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find headline elements
        headlines = []
        
        # Updated selector to find headline rows
        story_rows = soup.find_all('tr', class_='athing', limit=limit)

        for i, story_row in enumerate(story_rows, 1):
            # Extract title and link
            title_link = story_row.find('span', class_='titleline').find('a')
            
            # Debug print
            if not title_link:
                print(f"No title link found for row {i}")
                continue

            title = title_link.text
            link = title_link.get('href', '')
            
            # Find the corresponding subtitle row
            subtitle_row = story_row.find_next_sibling('tr')
            
            # Try to find points and comments
            try:
                points_elem = subtitle_row.find('span', class_='score')
                points = points_elem.text if points_elem else "N/A"
                
                comments_elem = subtitle_row.find_all('a')[-1]
                comments = comments_elem.text if comments_elem and 'comment' in comments_elem.text.lower() else "0 comments"
            except Exception as e:
                print(f"Error extracting points/comments: {e}")
                points = "N/A"
                comments = "0 comments"

            # Optional LLM enhancement
            description = ""
            if llm_client:
                try:
                    prompt = f"Provide a concise 1-2 sentence summary of the Hacker News headline: {title}. Start your response with 'Hola Friends, here's the tech news of the day'"
                    response = llm_client.chat.completions.create(
                        model='gpt-4o-mini',
                        messages=[{"role": "user", "content": prompt}]
                    )
                    description = response.choices[0].message.content.strip()
                except Exception as e:
                    print(f"LLM description generation failed: {e}")

            headlines.append({
                "rank": i,
                "title": title,
                "link": link,
                "points": points,
                "comments": comments,
                "description": description
            })

        # Debug print
        print(f"Extracted {len(headlines)} headlines")

        return {
            "source": "Hacker News",
            "headlines": headlines
        }

    except Exception as e:
        # Log the full error for debugging
        logging.error(f"Failed to fetch Hacker News headlines: {str(e)}")
        print(f"Full error: {str(e)}")
        
        return {
            "error": f"Failed to fetch Hacker News headlines: {str(e)}",
            "headlines": []
        }

# Tool metadata remains the same
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_hacker_news_headlines",
        "description": "Retrieve the top headlines from Hacker News with optional additional context",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of headlines to retrieve",
                    "minimum": 1,
                    "maximum": 3
                }
            },
            "required": []
        }
    }
}