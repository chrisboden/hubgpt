# tools/use_agents.py
import os
import json
import logging
from termcolor import colored
from openai import OpenAI
from utils import prompt_utils
from utils.ui_utils import update_spinner_status
from utils.log_utils import log_llm_request, log_llm_response

def execute(llm_client=None, advisor_name=None, query=None, provide_latest_news=False):
    """Provides advice from the specified advisor using the corresponding prompt template."""
    print(colored("Starting get_advice tool execution", "cyan"))
    
    if not llm_client:
        raise ValueError("An LLM client must be provided.")
    if not advisor_name or not query:
        raise ValueError("Both 'advisor_name' and 'query' are required parameters.")

    try:
        print(colored(f"Selected advisor: {advisor_name}", "yellow"))
        update_spinner_status(f"🔗 Selected Advisor: {advisor_name}")
        advisor_data = prompt_utils.load_advisor_data(advisor_name)

        initial_messages = advisor_data.get("messages", [])

        # Handle news context if required
        if provide_latest_news:
            print(colored("Fetching latest news context", "yellow"))
            try:
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

                # Log news API request
                news_api_params = {
                    "model": "perplexity/llama-3.1-sonar-huge-128k-online",
                    "messages": news_messages,
                    "temperature": 1.15,
                    "max_tokens": 8092,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    "stream": False
                }
                log_llm_request(news_api_params)
                print(colored("Making news context API call", "yellow"))

                news_response = llm_client.chat.completions.create(**news_api_params)
                log_llm_response({"news_context": news_response.choices[0].message.content})

                news_context = news_response.choices[0].message.content
                print(colored("Successfully retrieved news context", "green"))
                update_spinner_status("🔗 Enhancing query with news results")
                enhanced_query = f"{query}\n\nYou may find this additional context useful: {news_context}"
            except Exception as news_error:
                print(colored(f"News fetching failed: {news_error}", "red"))
                logging.error(f"News fetching failed: {news_error}")
                enhanced_query = query
        else:
            enhanced_query = query

        # Prepare final messages
        messages = initial_messages + [
            {
                "role": "user", 
                "content": enhanced_query
            }
        ]

        # Prepare API parameters for main advice call
        api_params = {
            "model": advisor_data.get('model', 'openai/gpt-4o-mini'),
            "messages": messages,
            "temperature": advisor_data.get('temperature', 1.0),
            "max_tokens": advisor_data.get('max_output_tokens', 8092),
            "top_p": advisor_data.get('top_p', 1),
            "frequency_penalty": advisor_data.get('frequency_penalty', 0),
            "presence_penalty": advisor_data.get('presence_penalty', 0),
            "stream": True
        }

        # Log the main API request
        log_llm_request(api_params)
        print(colored("Making main advisor API call", "yellow"))

        # Create the completion with streaming
        stream = llm_client.chat.completions.create(**api_params)
        
        print(colored("Successfully received stream response", "green"))
        logging.info("\n" + "="*50 + "\nDIRECT STREAM RESPONSE:\n" + "="*50 + 
                    f"\nReturning stream object for advisor: {advisor_name}\n" + "="*50)

        return {
            "result": stream,
            "direct_stream": True
        }

    except Exception as e:
        error_msg = f"Failed to get advice: {str(e)}"
        print(colored(error_msg, "red"))
        logging.error(error_msg)
        return {
            "error": error_msg
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
                "agent_name": {
                    "type": "string",
                    "description": "The name of the agent you think is best suited to the task for this step of the workflow.",
                    "enum":["Planning_Agent","Execution_Agent","Observation_Agent"]
                },
                "query": {
                    "type": "string",
                    "description": "The query or message seeking advice"
                }
            },
            "required": ["advisor_name", "query"]
        }
    },
    "direct_stream": True
}