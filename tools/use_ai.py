# tools/use_ai.py

import json
from termcolor import cprint
from openai import OpenAI
from utils.prompt_utils import process_inclusions

def execute(messages=[], model="openai/gpt-4o-mini", temperature=0.7, max_tokens=None, client=None):
    """
    Makes a call to an AI language model API with specified messages and model selection.
    Supports file inclusion syntax in message content using <$filename$> or <$dir:pattern$>.
    
    Args:
        messages (list): Array of message objects with 'role' and 'content' keys.
                        Content can include file references like <$files/data.txt$>
        model (str): The model to use (defaults to 'openai/gpt-4o-mini')
        temperature (float): Controls randomness in the response (0.0 to 1.0)
        max_tokens (int, optional): Maximum length of response
        client: OpenAI client instance
        
    Returns:
        str: The AI model's response content or error message
    """
    try:
        # Input validation
        if not isinstance(messages, list):
            return "Error: messages must be a list"
        
        if not messages:
            return "Error: messages list cannot be empty"
            
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                return "Error: each message must be a dict with 'role' and 'content' keys"

        # Process file inclusions in each message's content
        processed_messages = []
        for msg in messages:
            processed_msg = msg.copy()
            processed_msg['content'] = process_inclusions(msg['content'], depth=5)
            processed_messages.append(processed_msg)

        # Log the request
        cprint(f"\nMaking AI call using model: {model}", "blue")
        cprint("Messages:", "blue")
        cprint(json.dumps(processed_messages, indent=2), "cyan")

        # Use provided client or initialize new one
        ai_client = client or OpenAI()

        # Prepare completion parameters
        completion_params = {
            "model": model,
            "messages": processed_messages,
            "temperature": temperature
        }
        
        # Add max_tokens if specified
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens

        # Make the API call
        completion = ai_client.chat.completions.create(**completion_params)

        # Extract and log response
        response = completion.choices[0].message.content
        cprint(f"\nAI Response:", "green")
        cprint(response, "green")
        
        return response

    except Exception as e:
        error_msg = f"Error in AI call: {str(e)}"
        cprint(error_msg, "red")
        return error_msg

# tools/use_ai.py

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_ai",
        "description": (
            "Makes a call to an AI language model API with specified messages and model selection. "
            "Importantly, this tool supports file inclusion in message content using special syntax. "
            "\n\nKey Features:"
            "\n1. File Inclusion: Use <$filename$> syntax to include file contents"
            "\n2. Directory Inclusion: Use <$dir:pattern$> for multiple files"
            "\n3. Context Preservation: Include previous results or conversation history"
            "\n\nCommon Usage Patterns:"
            "\n1. Including previous results:"
            "\n   - Save results to file: <$files/search_results.txt$>"
            "\n   - Reference context: <$files/conversation_history.txt$>"
            "\n2. Processing data files:"
            "\n   - Analyze data: <$files/data.json$>"
            "\n   - Process logs: <$files/app.log$>"
            "\n3. Multi-file analysis:"
            "\n   - Include multiple files: <$dir:files/*.txt$>"
            "\n\nExample Messages:"
            '\n```python'
            '\nmessages=['
            '\n    {"role": "system", "content": "You are analyzing data from previous steps: <$files/analysis.txt$>"},'
            '\n    {"role": "user", "content": "Based on these search results: <$files/search_results.txt$>, please..."}'
            '\n]'
            '\n```'
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": (
                        "The model to use. Default options include:\n"
                        "- 'openai/gpt-4o-mini' for general use\n"
                        "- 'perplexity/llama-3.1-sonar-huge-128k-online' for web search tasks\n"
                        "- 'google/gemini-2.0-flash-001' for large context tasks"
                    ),
                    "default": "openai/gpt-4o-mini"
                },
                "messages": {
                    "type": "array",
                    "description": (
                        "Array of message objects with 'role' and 'content' keys. The content field supports special file inclusion syntax:\n"
                        "1. Single file: <$filename$> - includes contents of the specified file\n"
                        "2. Multiple files: <$dir:pattern$> - includes all matching files\n"
                        "3. Datetime: <$datetime$> or <$datetime:format$>\n\n"
                        "Examples:\n"
                        '- {"role": "user", "content": "Analyze this data: <$files/data.txt$>"}\n'
                        '- {"role": "system", "content": "Use context from: <$files/previous_step.txt$>"}\n'
                        '- {"role": "user", "content": "Process these logs: <$dir:files/logs/*.log$>"}'
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["system", "user", "assistant"],
                                "description": "The role of the message sender (system, user, or assistant)"
                            },
                            "content": {
                                "type": "string",
                                "description": (
                                    "The message content. Can include file references using <$filename$> syntax.\n"
                                    "Examples:\n"
                                    "- 'Based on these results: <$files/results.txt$>'\n"
                                    "- 'Analyze all logs: <$dir:files/logs/*.txt$>'\n"
                                    "- 'Current time: <$datetime:%Y-%m-%d %H:%M:%S$>'"
                                )
                            }
                        },
                        "required": ["role", "content"]
                    }
                },
                "temperature": {
                    "type": "number",
                    "description": "Controls randomness in the response (0.0 to 1.0)",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum length of response. If not specified, model default is used.",
                    "minimum": 1
                }
            },
            "required": ["messages"]
        }
    }
}