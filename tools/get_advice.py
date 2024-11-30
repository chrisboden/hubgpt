# tools/get_advice.py
import os
import json
from openai import OpenAI
from utils import prompt_utils  # Import the prompt utils
from utils.llm_utils import update_spinner_status

def execute(llm_client=None, advisor_name=None, query=None, provide_latest_news=False):
    """
    Provides advice from the specified advisor using the corresponding prompt template.

    Parameters:
    - llm_client (OpenAI): The LLM client for making API calls.
    - advisor_name (str): The name of the advisor, matching a JSON file in the 'advisors' directory.
    - query (str): The user's query or message seeking advice.
    - provide_latest_news (bool): Whether to fetch latest news context for the query.

    Returns:
    - dict: A dictionary containing the advisor's response.
    """
    if not llm_client:
        raise ValueError("An LLM client must be provided.")
    if not advisor_name or not query:
        raise ValueError("Both 'advisor_name' and 'query' are required parameters.")

    try:
        # Use load_advisor_data to process file inclusions
        print(f"Selected advisor: {advisor_name}")
        update_spinner_status(f"🔗 Selected Advisor: {advisor_name}")
        advisor_data = prompt_utils.load_advisor_data(advisor_name)

        # Construct the messages with the processed advisor data
        initial_messages = advisor_data.get("messages", [])

        # Check if latest news should be provided
        if provide_latest_news:
            try:
                # Use the get_news tool to fetch latest context
                update_spinner_status("🔗 Getting latest news")
                news_messages = [
                    {
                        "role": "system",
                        "content": "You are a highly reliable source of web search content"
                    },
                    {
                        "role": "user",
                        "content": f"Provide the current major news updates about {query}"
                    }
                ]

                news_response = llm_client.chat.completions.create(
                    model="perplexity/llama-3.1-sonar-huge-128k-online",
                    messages=news_messages,
                    temperature=1.15,
                    max_tokens=8092,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stream=False
                )

                # Append news context to the original query
                news_context = news_response.choices[0].message.content
                update_spinner_status("🔗 Enhancing query with news results")
                enhanced_query = f"{query}\n\nYou may find this additional context useful: {news_context}"
            except Exception as news_error:
                # If news fetching fails, use original query
                enhanced_query = query
                print(f"News fetching failed: {news_error}")
        else:
            enhanced_query = query

        # Prepare the final messages for the advisor
        messages = initial_messages + [
            {
                "role": "user", 
                "content": enhanced_query
            }
        ]

        # Create the completion with streaming
        stream = llm_client.chat.completions.create(
            model=advisor_data.get('model', 'openai/gpt-4o-mini'),
            messages=messages,
            temperature=advisor_data.get('temperature', 1.0),
            max_tokens=advisor_data.get('max_output_tokens', 8092),
            top_p=advisor_data.get('top_p', 1),
            frequency_penalty=advisor_data.get('frequency_penalty', 0),
            presence_penalty=advisor_data.get('presence_penalty', 0),
            stream=True  # Enable streaming
        )

        # Return the stream directly
        return {
            "result": stream,
            "direct_stream": True
        }

    except Exception as e:
        return {
            "error": f"Failed to get advice: {str(e)}"
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_advice",
        "description": "Get advice from a specified advisor based on the given query posed by a user",
        "parameters": {
            "type": "object",
            "properties": {
                "advisor_name": {
                    "type": "string",
                    "description": "The name of the advisor you think is best suited to the task of answering the user's query (e.g., 'Naval_Ravikant').",
                    "enum":["Naval_Ravikant","Chris_Voss","Charlie_Munger","Steve_Jobs","Yuval_Harari","Charlie_Munger","Daniel_Kahneman","Elon_Musk", "Jim_Collins","Nassim_Taleb","Peter_Thiel","Shane_Parrish","Matt_Ridley","David_Deutsch"]
                },
                "query": {
                    "type": "string",
                    "description": "The query or message seeking advice"
                },
                "provide_latest_news": {
                    "type": "boolean",
                    "description": "This parameter determines whether the advisor should be given contemporary information to help them answer the user. Most advisor's are provided with detailed content from books, eg their biographies, to help ground their answers. Most of those books will not include contemporary information about the latest news and happenings. For example, if the advisor Steve Jobs is asked about the latest model of the iPhone, this parameter should be 'true' such that his book content can be supplemented with the latest news to enable him to answer questions on current issues. If the user's question does not involve contemporary issues then the parameter should be 'false'. The default for this parameter should be 'false'",
                    "default": False
                }
            },
            "required": ["advisor_name", "query"]
        }
    },
    "direct_stream": True  # Maintain the direct streaming flag
}