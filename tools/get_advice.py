# tools/get_advice.py
import os
import json
from openai import OpenAI
from utils import prompt_utils  # Import the prompt utils

def execute(llm_client=None, advisor_name=None, query=None):
    """
    Provides advice from the specified advisor using the corresponding prompt template.

    Parameters:
    - llm_client (OpenAI): The LLM client for making API calls.
    - advisor_name (str): The name of the advisor, matching a JSON file in the 'advisors' directory.
    - query (str): The user's query or message seeking advice.

    Returns:
    - dict: A dictionary containing the advisor's response.
    """
    if not llm_client:
        raise ValueError("An LLM client must be provided.")
    if not advisor_name or not query:
        raise ValueError("Both 'advisor_name' and 'query' are required parameters.")

    try:
        # Use load_advisor_data to process file inclusions
        advisor_data = prompt_utils.load_advisor_data(advisor_name)

        # Construct the messages with the processed advisor data
        initial_messages = advisor_data.get("messages", [])
        initial_messages.append({"role": "user", "content": query})

        # Extract LLM parameters from the advisor data
        llm_params_keys = [
            "model", "temperature", "max_tokens", "top_p", 
            "frequency_penalty", "presence_penalty", "stream"
        ]
        llm_params = {key: advisor_data[key] for key in llm_params_keys if key in advisor_data}

        # Make the API call
        response_stream = llm_client.chat.completions.create(
            model=llm_params["model"],
            messages=initial_messages,
            stream=llm_params.get("stream", False),
            **{key: llm_params[key] for key in llm_params if key not in ["model", "stream"]}
        )

        # Process the streamed response
        full_response = ""
        for chunk in response_stream:
            if not chunk.choices:
                continue
            full_response += chunk.choices[0].delta.content or ""

        return {"advisor": advisor_name, "response": full_response}

    except Exception as e:
        raise ValueError(f"Error processing advisor data: {str(e)}")

# Metadata remains the same
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
                    "description": "The name of the advisor (e.g., 'Naval Ravikant')",
                    "enum":["Naval Ravikant","Chris Voss","Charlie Munger","Steve Jobs"]
                },
                "query": {
                    "type": "string",
                    "description": "The query or message seeking advice"
                }
            },
            "required": ["advisor_name", "query"]
        }
    },
    "direct_stream": True  # New flag for direct streaming
}