# Working with Tools in HubGPT

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

# Tool Calling Flow

## Overview
Tool calling (previously known as function calling) allows the LLM to suggest tools to handle specific tasks by indicating:

1. The suggested tool and its parameters
2. The developer invokes the tool with the provided arguments 
3. Tool results are returned to the LLM
4. The LLM formats a response using the tool's output

## Message Flow

The tool calling process follows a 5-step sequence:

1. **Initial Request**: User message is sent along with available tools schema
2. **Tool Selection**: LLM responds with tool suggestion and arguments
3. **Tool Execution**: Developer invokes the selected tool
4. **Tool Response**: Results are sent back to LLM with tool call ID
5. **Final Response**: LLM generates natural language response

### Example Flow

In this example the user is chatting with an agent that has been given a weather tool allowing it to get the current weather in a given location. The idea is that the user can ask a fuzzy question like is it warm in Brisbane today and the LLM will know to call the get_current_weather tool rather than reply directly with a hallucinated answer about the weather.

To understand how the LLM makes that decision requires that you get an understanding of what payload is being sent to the LLM each time a user sends a message. That payload contains the array of messages from the conversation up until now - that array starts with the system message and then generally has user and assistant messages alternating

- system message: You are a helpful assistant
- user: what is the capital of australia?
- assistant: The capital of Australia is Canberra
- user: how about Angola?
- assistant: The capital of Angola is Luanda

With each message the user sends, the system message and the entire user>assistant chat history gets included. That is how we maintain context with the LLM and how it can answer questions where we refer to things mentioned previously.

Also in that payload is the array of tools you make available to the LLM - not actually the tool code itself but metadata about the tool. Think of the metadata as a kind of prompt that explain to the llm what each tool does.

Eg, the tool metadata for the get_current_weather tool may look like this below. Here you see the how tools array is added to the messages array as part of the payload that gets sent to the LLM. Now it knows that it is a helpful assistant and that it has a weather tool, and the tool metadata tells it how to 'call the tool.

Is this case it knows that to use that tool, it should respond not with a regular assistant message but with a tool call message that includes the name of the too `get_current_weather` and the `location` parameter. The description field for the tool and for each paramater are like prompts explaining to the Llm how the tool works.

```json
{
  "messages": [
    {
    "role": "syetem", 
    "content": "You are a helpful assistant"
    },
    {
    "role": "user", 
    "content": "What's the weather in Boston?"
    }
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get current weather in a location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City and state"
          }
        },
        "required": ["location"]
      }
    }
  }]
}
```


Now the LLM responds with a tool call - you can see how that message is different to a regular assistant message. It includes, the tool name, and 'arguments' (ie parameters) that include the location. It also includes a unique tool calls id.

1. LLM Tool Selection:
```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [{
    "id": "call_xyz123",
    "type": "function", 
    "function": {
      "name": "get_current_weather",
      "arguments": "{\"location\": \"Brisbane, QLD\"}"
    }
  }]
}
```

In HubGPT we have code that keeps an eye out for tool calls from the LLM. It looks to see if there is a matching tool name in the `/tools` directory eg `/tools/get_current_weather.py` and if it finds it, it calls that tool, passing in the parameters it received from the LLM, eg `location=Brisbane, QLD`.  

1. Tool Execution (handled by tool_utils.py):
```python
# tool_utils.py executes the tool
response = tool_func(**args)
```

The tool then executes and usually generates a response, eg gets the current weather conditions in Brisbane. Our application makes a call to the LLM with role `tool` rather than the role of `user` and we pass to the LLM the output from the tool.


1. Tool Response:
```json
{
  "role": "tool",
  "name": "get_current_weather",
  "tool_call_id": "call_xyz123",
  "content": "{\"temperature\": 22, \"unit\": \"celsius\", \"description\": \"Sunny\"}"
}
```

Now that the LLM knows what the actual tool result is (ie temperature: 22 and sunny), it can answer the original question in natural language by responding with a regular assistant message.

1. Final LLM Response:
```json
{
  "role": "assistant",
  "content": "The current weather in Brisbane is sunny with a temperature of 22°C."
}
```

### LLM Tool Calling Flow

| **Step** | **Your Code**                                                  | **LLM**                                  |
|----------|----------------------------------------------------------------|------------------------------------------|
| **1**    | Calls the API with your prompt and definitions of tools.       |                                          |
| **2**    |                                                                | Decides whether to respond or call a tool. |
| **3**    | Receives the tool name and arguments from the API.             | Responds with the tool and arguments.    |
| **4**    | Executes the tool with the provided arguments.                 |                                          |
| **5**    | Calls the API again with the prompt and tool result.           |                                          |

The flow continues until the response is complete.


## Implementation Notes

- Tool calling is handled by the `tool_utils.py` module which:
  - Loads and registers all available tools
  - Executes tools with provided arguments
  - Handles response formatting and streaming
  - Manages tool metadata and direct streaming flags

- Tools can specify `direct_stream: True` in their metadata to stream responses directly to the UI without LLM reformatting

- When using streaming responses, the application needs to:
  - Accumulate response chunks
  - Parse chunks for tool calls and arguments
  - Handle progressive/incremental content

## Best Practices

1. Always include clear tool descriptions and parameter schemas
2. Handle tool execution errors gracefully
3. Use direct streaming for tools generating progressive responses
4. Follow the OpenRouter API conventions for message structure
5. Include proper error handling and logging





# List of Tools Available

## code_run

**Source File:** `code_run.py`

**Description:** Executes a Python script file and returns its output. The script will have access to all agent tools.

---

## code_write

**Source File:** `code_write.py`

**Description:** Creates or overwrites a Python script with the provided code. The script will automatically have access to all agent tools through pre-configured imports. 

Example usage patterns:
1. Using the AI tool:
   from tools import use_ai
   result = use_ai.execute(
       messages=[{'role': 'user', 'content': 'Your prompt here'}]
   )

2. Using web search:
   from tools import web_search
   results = web_search.execute(query='Your search query')

3. File operations:
   from tools import file_read, file_write
   content = file_read.execute('input.txt')
   file_write.execute('output.txt', 'new content')

4. Web scraping:
   from tools import web_scrape
   content = web_scrape.execute(url='https://example.com', filename='scraped.txt')

The code will have access to all standard Python libraries plus the agent's tool suite.

---

## email_create

**Source File:** `email_create.py`

**Description:** Send an HTML email using a Zapier webhook. Creates rich HTML emails with optional plain text fallback.

---

## file_operations

**Source File:** `file_operations.py`

**Description:** A secure tool for performing various file system operations including reading, writing, editing files, managing directories, and downloading files from the web.

 Important: Supports multiple operations in a single call for related tasks like create directory and move files. Eg "operations": [
        {
            "operation": "create_directory",
            "path": "/data/files/new_folder"
        },
        {
            "operation": "move_file",
            "source": "/data/files/document.md",
            "destination": "/data/files/new_folder/renamed.md"
        }
    ]

---

## get_advice

**Source File:** `get_advice.py`

**Description:** Get advice from a specified advisor based on the given query posed by a user

---

## get_company_updates

**Source File:** `get_company_updates.py`

**Description:** Fetch the recent LinkedIn updates posted by a given list of companies

---

## get_current_weather

**Source File:** `get_current_weather.py`

**Description:** Provide the current weather for a given location when asked by a user

---

## get_hacker_news

**Source File:** `get_hacker_news.py`

**Description:** Retrieve and summarize the top headlines from Hacker News

---

## get_news

**Source File:** `get_news.py`

**Description:** Use this tool if you need to get up to date news from the web about a specific subject or topic. This tool provides the latest news and works best with a detailed search query. Make sure to rephrase the user's question as a detailed search_query

---

## get_research

**Source File:** `get_research.py`

**Description:** This tool is a very intelligent web research agent that can search, find, gather and synthesise highly relevant information for a given topic. Use this tool whenever you are asked to perform research on topic. You simply give the agent a research_brief in natural language, eg 'please research the spacex starship launch schedule'. It will return a comprehensive research dossier for you to use in your answers.

---

## get_transcription

**Source File:** `get_transcription.py`

**Description:** Download captions and transcript from a YouTube video, with optional AI-powered summarization

---

## get_tweets

**Source File:** `get_tweets.py`

**Description:** Get the latest tweets from a given Twitter list

---

## get_website

**Source File:** `get_website.py`

**Description:** Get the definitive website url for a given term

---

## get_wikipedia

**Source File:** `get_wikipedia.py`

**Description:** Retrieve comprehensive Wikipedia content for a given search term and use that content to provide an information dense response to the user. Response MUST be >500 words

---

## handoff_to_agent

**Source File:** `handoff_to_agent.py`

**Description:** Use this to hand off work to another agent when their expertise is needed

---

## handoff_to_coordinator

**Source File:** `handoff_to_coordinator.py`

**Description:** Use this to hand work back to the coordinator agent when you have completed your part

---

## linkedin_bio_writer

**Source File:** `linkedin_bio_writer.py`

**Description:** Generate a professional biography from a LinkedIn profile

---

## linkedin_research

**Source File:** `linkedin_research.py`

**Description:** This tool performs comprehensive LinkedIn research on a person or company, collecting profile data and posts, analyzing them, and providing detailed insights.

---

## make_artifact

**Source File:** `make_artifact.py`

**Description:** Generate self-contained HTML artifacts (widgets) with embedded JavaScript and CSS

---

## make_book

**Source File:** `make_book.py`

**Description:** Generate a complete book with multiple chapters on any topic using AI. The tool handles research, writing, and formatting.

---

## use_ai

**Source File:** `use_ai.py`

**Description:** Makes a call to an AI language model API with specified messages and model selection. Importantly, this tool supports file inclusion in message content using special syntax. 

Key Features:
1. File Inclusion: Use <$filename$> syntax to include file contents
2. Directory Inclusion: Use <$dir:pattern$> for multiple files
3. Context Preservation: Include previous results or conversation history

Common Usage Patterns:
1. Including previous results:
   - Save results to file: <$files/search_results.txt$>
   - Reference context: <$files/conversation_history.txt$>
2. Processing data files:
   - Analyze data: <$files/data.json$>
   - Process logs: <$files/app.log$>
3. Multi-file analysis:
   - Include multiple files: <$dir:files/*.txt$>

Example Messages:
```python
messages=[
    {"role": "system", "content": "You are analyzing data from previous steps: <$files/analysis.txt$>"},
    {"role": "user", "content": "Based on these search results: <$files/search_results.txt$>, please..."}
]
```

---

## use_brainstorm

**Source File:** `use_brainstorm.py`

**Description:** Generate creative ideas using various brainstorming techniques. Respond with a clean markdown format that presents the ideas in the most useful format for the user. Methods: Reverse brainstorming involves identifying ways to cause a problem or achieve the opposite effect. Perfect for spotting potential issues and coming up with innovative solutions. Role storming adopting the perspective of someone else to generate ideas. Great for gathering insights from different viewpoints. SCAMPER stands for Substitute, Combine, Adapt, Modify, Put to another use, Eliminate, and Reverse. It encourages thinking from multiple perspectives to generate diverse ideas. Edward de Bono, looks at a problem from six different perspectives - White (Data), Red (Emotions), Black (Risks), Yellow (Benefits), Green (Creativity), and Blue (Process management). Focuses on generating questions rather than answers using the 5 W's and 1 H (Who, What, Where, When, Why, How). Ideal for comprehensive topic exploration.

---

## use_notion

**Source File:** `use_notion.py`

**Description:** This tool allows you to interact with Notion by either creating new pages or fetching existing page content. Use 'create_page' to add new content and 'fetch_content' to retrieve existing content.

---

## use_sequential_thinking

**Source File:** `use_reasoning.py`

**Description:** A tool for dynamic, reflective, and self-directed sequential reasoning. It stores a chain of thoughts, supports revisions and branching, and can optionally suggest next steps using an LLM if needed.

---

## use_todo_list

**Source File:** `use_todo_list.py`

**Description:** Use a todo list to keep track of activities. You can use `create` to create a new todo list, optionally with initial items. Use `read` to read a given todo list by passing in the id. Use `update` to update the state of the todo list, eg by marking an item as 'done'. Each item follows a structured schema with id, todo (markdown description), done (boolean status), and note (contextual information).

---

## web_image_search

**Source File:** `web_image_search.py`

**Description:** Perform an image search to find the best matching image for a given user request

---

## web_read_page

**Source File:** `web_read_page.py`

**Description:** Fetches and returns a clean markdown version of a webpage.

---

## web_scrape

**Source File:** `web_scrape.py`

**Description:** Fetches and extracts textual content from a specified URL and saves it to a file. The content is saved in markdown format with proper formatting and structure. Use this tool to gather information from web pages for learning, data analysis, or incorporating external knowledge into your responses. This is helpful when you need to access the latest information or data not available in your existing knowledge base.

---

## web_search

**Source File:** `web_search.py`

**Description:** Performs a comprehensive web search using multiple search providers (Brave, Tavily, DuckDuckGo, etc.). The tool optimizes the search query using AI and returns ranked results. Use this tool when you need to find current information about any topic, verify facts, or gather data from multiple sources. Results include titles, URLs, and descriptions from various web pages.

---

