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