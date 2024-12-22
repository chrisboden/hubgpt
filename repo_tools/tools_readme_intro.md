## Intro

This tools directory contains a collection of tools that can be used by the AI assistant. Each tool is implemented as a separate Python module and provides specific functionality that can be called by the AI.

Below is a comprehensive list of all available tools, their source files, and descriptions.

## How to Create Tools for the HubGPT Framework

### Tool Structure Guidelines

Each tool in this framework follows a consistent structure to ensure seamless integration and usability:

#### 1. Basic Tool Requirements
- Create a Python file in the `tools/` directory
- Implement an `execute()` function as the primary entry point
- Define a `TOOL_METADATA` dictionary for tool description and parameters

#### 2. Execute Function Template
```python
def execute(llm_client=None, **kwargs):
    """
    Primary function for tool execution
    
    Parameters:
    - llm_client (optional): LLM client for additional processing
    - **kwargs: Flexible keyword arguments for tool-specific inputs
    
    Returns:
    - dict: Structured response with tool results
    """
    # Tool-specific implementation
    return {
        "result": ...,  # Primary result of the tool
        "additional_info": ...  # Optional additional context
    }
```
### 2.1 Advanced Tool Processing with LLM Integration

Here's a simplified example demonstrating how to leverage an LLM client for language translation:

```python
def execute(text, target_language="Spanish", llm_client=None):
    """
    Translate input text to target language
    
    Parameters:
    - text: Text to be translated
    - target_language: Language to translate to
    - llm_client (optional): LLM client for translation
    
    Returns:
    - dict: Structured response with translation results
    """
    try:
        # Initial processing
        original_text = text.strip()
        
        # Optional LLM translation
        if llm_client:
            # Define LLM messages for translation
            llm_messages = [
                {
                    "role": "system", 
                    "content": "You are a professional translator."
                },
                {
                    "role": "user", 
                    "content": f"Translate the following text to {target_language}: {original_text}"
                }
            ]
            
            # Use LLM to translate text
            llm_response = llm_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=llm_messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Extract translated text
            translated_text = llm_response.choices[0].message.content
            
            return {
                "original_text": original_text,
                "translated_text": translated_text,
                "target_language": target_language,
                "processing_method": "LLM translation"
            }
        
        # Fallback if no LLM client provided
        return {
            "result": original_text,
            "processing_method": "No translation"
        }
    
    except Exception as e:
        return {
            "error": f"Translation failed: {str(e)}",
            "status": "error"
        }
```

#### Key LLM Integration Patterns:
- Provide optional `llm_client` parameter
- Use system and user messages to define context
- Leverage `chat.completions.create()` for processing
- Return structured dictionary with original and enhanced results
- Include comprehensive error handling


#### 3. Tool Metadata Structure
```python
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "Concise description of tool's purpose",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of parameter"
                }
            },
            "required": ["param1"]
        }
    }
}
```

### Best Practices
- Always include error handling
- Support optional `llm_client` for advanced processing
- Use type hints and docstrings
- Return structured dictionary responses
- Define clear, descriptive metadata

### Example: Weather Tool
```python
def execute(llm_client=None, location="San Francisco", unit="celsius"):
    """Get current weather for a location"""
    weather_info = {
        "location": location,
        "temperature": "18",
        "unit": unit
    }
    return weather_info

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Retrieve current weather for a specified location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. 'San Francisco, CA'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"]
        }
    }
}
```

### Tool Integration
- Tools are automatically discovered and registered by `utils/tool_utils.py`
- No manual registration required
- Supports dynamic tool loading and execution

### Streaming Tool Responses with `direct_stream`

#### Overview of `direct_stream`
The `direct_stream` option is a powerful feature in our tool framework that enables real-time, streaming responses from Large Language Model (LLM) tools directly to the user interface.

#### Key Benefits
- **Real-time Output**: Allows immediate rendering of LLM responses as they are generated
- **Reduced Latency**: Users see results progressively instead of waiting for full completion
- **Enhanced User Experience**: Provides a more interactive and responsive interface

#### How `direct_stream` Works
1. When a tool's `TOOL_METADATA` includes `"direct_stream": True`, the `execute_tool()` function in `tool_utils.py` preserves the streaming response
2. The response is passed back with a `direct_stream` flag set to `True`
3. The UI can then handle the streaming response appropriately

#### Example: Advice Tool Streaming
In the `get_tanscription.py` tool, streaming is enabled in the tool metadata with `"direct_stream": True` - in this case we ask the llm to take the youtube captions (which get returned by the youtube api as a messy list of half sentences) and turn it into a clean transcription and in doing so, to stream that clean transcription to the ui directly.

```python
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_transcription",
        "description": "Download captions and transcript from a YouTube video, with optional AI-powered summarization",
        "parameters": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "The URL of the YouTube video to transcribe"
                }
            },
            "required": ["video_url"]
        }
    },
    "direct_stream": True
}

```

#### Implementation Details
- Supported in tools like `get_advice.py` that generate progressive responses
- Requires UI-side logic to handle streaming responses
- Provides flexibility for tools that generate real-time, incremental content

#### Best Practices
- Use `direct_stream` for tools generating progressive or lengthy responses from an llm where you don't want that response to be passed back to the main llm loop and regurgitated
- Ensure the LLM API call is made with `stream=True`