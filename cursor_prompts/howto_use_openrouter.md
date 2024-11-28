When building AI apps, my preference is to use a platform called OpenRouter which is a unified interface for LLMs, rather than directly integrating with openai/anthropic/google etc. Openrouter has s ingle api which uses the same python client as OpenAI (and other popular LLMs). The reason for giving you this guide is that your training data cutoff does not include the latest API specs and instead includes deprecated api information. Use this instead as your guide.

This is README guide with examples for using OpenRouter with the OpenAI Python SDK, including instructions for handling tool calling (previously function calling), and different file types (for multimodality).

# **Quickstart for how to use the OpenAI python client with OpenRouter**

```python

from openai import OpenAI
import os

# gets API Key from my .env file for API_BASE_URL (which we use to override the openai url) and we set the OPENROUTER_API_KEY

client = OpenAI(
    base_url=os.getenv('API_BASE_URL'),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

completion = client.chat.completions.create(
  model="openai/gpt-3.5-turbo",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)
print(completion.choices[0].message.content)
```

## **Handling LLM responses: non-streamed vs streamed**

### **Non-streaming response structure:**

If the 'stream' parameter is not set or set to false, the non-streamed completion from the llm comes back in one accumulated response, in this format:

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "\n\nHello there, how may I assist you today?",
    },
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

Handling non-streamed response structure:

```python
completion = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        },
    ],
)
print(completion.choices[0].message.content)
```

### **Streaming response structure:**

If the stream parameter is set to true then the streamed completion returns in chunks and looks like this:

```json
{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

{"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini", "system_fingerprint": "fp_44709d6fcb", "choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}
```

Handling streamed response:

```python

stream = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "How do I output all files in a directory using Python?",
        },
    ],
    stream=True,
    tools=tools,
    tool_choice="auto"
)
for chunk in stream:
    if not chunk.choices:
        continue

    print(chunk.choices[0].delta.content, end="")
print()

```

Importantly, when dealing with streamed response, the app will need to accumulate chunks and parse the chunks for the tool call and arguments.


# **Using Tool Calls with OpenRouter**

### **Understanding Tool Calls**

**Tool Calls** let the LLM suggest tools to handle specific tasks by indicating:
1. **Suggested tool** and parameters.
2. **Developer invokes** the tool with the provided arguments.
3. **Tool results** are returned to the LLM.
4. The **LLM formats** a response using the tool's output.

### **Tool Call Process Overview**

1. **System message (optional) with User message and Available Tools**
2. **LLM replies with an Assistant message and a Tool eg get_current_weather along with a tool_call_id**
3. **Developer Invokes the Tool with a matching function, ie get_current_weather **
4. **Developer sends back Tool message with tool results to the LLM along with the corresponding tool_call_id**
5. **LLM Generates Final Response with an Assistant message**

### **Step-by-Step Guide**

### **1. User Request with Available Tools**

An example of the five-turn sequence:

The user asks a question, while supplying a list of available tools in a JSON schema format:

```json

...
"messages": [{
  "role": "user",
  "content": "What is the weather like in Boston?"
}],
"tools": [{
  "type": "function",
  "function": {
    "name": "get_current_weather",
    "description": "Get the current weather in a given location",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "The city and state, e.g. San Francisco, CA"
        },
        "unit": {
          "type": "string",
          "enum": [
            "celsius",
            "fahrenheit"
          ]
        }
      },
      "required": [
        "location"
      ]
    }
  }
}],

```

### **2. The LLM responds with tool suggestion, together with appropriate arguments:**


```json

// Some models might include their reasoning in content
"message": {
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_9pw1qnYScqvGrCH58HWCvFH6",
      "type": "function",
      "function": {
        "name": "get_current_weather",
        "arguments": "{ \"location\": \"Boston, MA\"}"
      }
    }
  ]
},


```

### **3. Developer Invokes the Tool Separately**

Use the provided tool arguments to call the tool, for example, a weather API:

```python
# Example function for weather data retrieval
def get_weather(location):
    return {"temperature": "22", "unit": "celsius", "description": "Sunny"}

# Invoke the tool based on LLM suggestion
weather_data = get_weather("Boston, MA")
```

### **4. Developer Provides Tool Results to LLM**

```json

...
"messages": [
  {
    "role": "user",
    "content": "What is the weather like in Boston?"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_9pw1qnYScqvGrCH58HWCvFH6",
        "type": "function",
        "function": {
          "name": "get_current_weather",
          "arguments": "{ \"location\": \"Boston, MA\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "name": "get_current_weather",
    "tool_call_id": "call_9pw1qnYScqvGrCH58HWCvFH6",
    "content": "{\"temperature\": \"22\", \"unit\": \"celsius\", \"description\": \"Sunny\"}"
  }
],

```

### **The LLM formats the tool result into a natural language response:**

```json
...
"message": {
  "role": "assistant",
  "content": "The current weather in Boston, MA is sunny with a temperature of 22°C."
}
```

---

## **Advanced OpenRouter Usage**



### **Handling Images & Multimodal Requests**

OpenRouter supports sending images as either URLs or base64-encoded strings.

#### **Sending an Image URL**

```python
image_request = {
    "model": "mistralai/mixtral-8x7b-instruct",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
            ]
        }
    ]
}
image_response = client.chat.completions.create(**image_request)
```

#### **Sending a Base64-Encoded Image**

```python
base64_image_request = {
    "type": "image_url",
    "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
}
base64_response = client.chat.completions.create(**base64_image_request)
```

Supported image formats: `image/png`, `image/jpeg`, `image/webp`.

### **Stream Cancellation**

Use Python’s `signal` module for stream control and cancellation:

```python
import signal
import time

# Define a handler to cancel streaming
def timeout_handler(signum, frame):
    raise TimeoutError("Stream cancelled")

# Set timeout for 10 seconds
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 seconds

try:
    stream = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[{"role": "user", "content": "Tell me a long story"}],
        stream=True
    )
    for chunk in stream:
        print(chunk.choices[0].delta.content, end="")
except TimeoutError:
    print("Stream timed out and was cancelled.")
finally:
    signal.alarm(0)  # Disable alarm
```