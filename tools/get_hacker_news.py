# tools/get_hacker_news_headlines.py
import requests
from bs4 import BeautifulSoup
import logging
from termcolor import colored
from utils.log_utils import log_llm_request, log_llm_response
from utils.prompt_utils import process_inclusions

def execute(llm_client=None, limit=20):
    """
    Fetch the top headlines from Hacker News and create a digest using LLM.
    """
    print(colored(f"Starting get_hacker_news_headlines tool execution (limit: {limit})", "cyan"))
    
    try:
        # Fetch Hacker News homepage
        url = "https://news.ycombinator.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(colored("Fetching Hacker News headlines...", "yellow"))
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = []
        
        # Find all story rows first
        story_rows = soup.find_all('tr', class_='athing')
        print(colored(f"Found {len(story_rows)} total stories", "green"))
        
        # Process only up to the limit
        for i, story_row in enumerate(story_rows[:limit], 1):
            print(colored(f"Processing story {i}/{limit}", "yellow"))
            # Extract title and link
            title_cell = story_row.find('span', class_='titleline')
            if not title_cell:
                print(colored(f"No title cell found for row {i}", "red"))
                continue

            title_link = title_cell.find('a')
            if not title_link:
                print(colored(f"No title link found for row {i}", "red"))
                continue

            title = title_link.text
            link = title_link.get('href', '')
            
            # Find the corresponding subtitle row
            subtitle_row = story_row.find_next_sibling('tr')
            if not subtitle_row:
                print(colored(f"No subtitle row found for story {i}", "red"))
                continue
            
            # Try to find points and comments
            try:
                points_elem = subtitle_row.find('span', class_='score')
                points = points_elem.text if points_elem else "N/A"
                
                comments_elem = subtitle_row.find_all('a')[-1]
                comments = comments_elem.text if comments_elem and 'comment' in comments_elem.text.lower() else "0 comments"
            except Exception as e:
                print(colored(f"Error extracting points/comments for story {i}: {e}", "red"))
                points = "N/A"
                comments = "0 comments"

            headlines.append({
                "rank": i,
                "title": title,
                "link": link,
                "points": points,
                "comments": comments
            })

        print(colored(f"Successfully extracted {len(headlines)} headlines", "green"))

        # Create digest using LLM
        if llm_client and headlines:
            print(colored("Creating digest with LLM...", "yellow"))
            
            # Format headlines for prompt
            headlines_text = "\n".join([
                f"{h['rank']}. {h['title']} ({h['points']}, {h['comments']})\n   Link: {h['link']}"
                for h in headlines
            ])
            
            # System message with file inclusion
            system_message = """
            ABOUT ME: <$files/me/aboutme.md$>
            
            ---
            
            ABOUT YOU: You are a seasoned technology journalist and thought leader with expertise in startups, AI, venture capital, and innovation ecosystems. You have a talent for weaving together seemingly disparate tech stories into compelling narratives that reveal broader industry patterns and implications.
            
            Your task is to create an engaging, essay-style digest of current technology news that's specifically curated for the user.
            
            Primary Objective:
            Craft a cohesive, narrative-driven analysis of relevant Hacker News stories, organizing them thematically rather than chronologically. The output should read like a well-crafted blog post or newsletter essay that connects dots between different stories and offers deeper insights.
            
            Process to follow:
            1. First, analyze the provided headlines through the lens of the user's interests and experience. 
            2. Then, identify 2-3 major themes emerging from the most relevant stories. These themes should form the backbone of your narrative.
            3. Write a flowing narrative that:
            - Opens with a compelling hook that introduces the most significant theme
            - Weaves story references naturally into paragraphs using inline links
            - Connects stories to broader industry trends
            - Includes thoughtful analysis relevant to the user's context
            - Maintains a sophisticated, conversational tone
            - Concludes with implications or future considerations
            - Strictly use UK English

            Format Specifications:
            - Length: 400-600 word
            - Style: Professional but conversational, similar to high-quality tech newsletter
            - Structure: 4-6 paragraphs organized by theme rather than individual storie
            - Links: Include as inline references within sentences, not as lists or bullet
            - Tone: Analytical and insightful, drawing on deep industry knowledge
            
            Example opening paragraph:
            
            'The artificial intelligence landscape continues its rapid evolution this week, with several developments suggesting a significant shift in how AI capabilities are being democratized. As OpenAI unveils [their latest API improvements](link), smaller players are finding innovative ways to carve out niches in what was previously a big-tech dominated space. This democratization trend particularly resonates with regional innovation hubs like ours at Peregian Digital Hub, where...'
            
            Constraints:
            - Avoid listing headlines or using bullet points
            - Don't force-fit irrelevant stories just because they're trending
            - Skip technical deep-dives unless specifically relevant to the user's interests
            - Maintain focus on implications rather than just reporting news
            
            The final output should feel like a personalized briefing from a knowledgeable industry insider who understands both the global tech landscape and the specific context of building a tech ecosystem in a regional area."
            
            """

            # Process any file inclusions in the system message
            processed_system_message = process_inclusions(system_message, depth=5)
            
            messages = [
                {
                    "role": "system",
                    "content": processed_system_message
                },
                {
                    "role": "user",
                    "content": f"Create a compelling digest from these Hacker News stories:\n\n{headlines_text}"
                }
            ]

            api_params = {
                "model": "x-ai/grok-2-1212",
                "messages": messages,
                "temperature": 1.0,
                "max_tokens": 8092,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "stream": True
            }

            # Log LLM request
            log_llm_request(api_params)
            print(colored("Making LLM API call for digest creation", "yellow"))

            # Get streaming response
            stream = llm_client.chat.completions.create(**api_params)
            
            print(colored("Successfully received stream response", "green"))
            logging.info("\n" + "="*50 + "\nDIRECT STREAM RESPONSE:\n" + "="*50 + 
                        "\nReturning stream object for HN digest\n" + "="*50)

            return {
                "result": stream,
                "direct_stream": True,
                "raw_headlines": headlines  # Include raw headlines for reference
            }

        return {
            "source": "Hacker News",
            "headlines": headlines
        }

    except Exception as e:
        error_msg = f"Failed to fetch Hacker News headlines: {str(e)}"
        print(colored(error_msg, "red"))
        logging.error(error_msg)
        return {
            "error": error_msg,
            "headlines": []
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_hacker_news",
        "description": "Retrieve and summarize the top headlines from Hacker News",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of headlines to retrieve",
                    "minimum": 10,
                    "maximum": 30,
                    "default": 20
                }
            },
            "required": []
        }
    },
    "direct_stream": True
}