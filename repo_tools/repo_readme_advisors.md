## Advisors

An "Advisor" is created by adding a prompt template (JSON file) to the `advisors` directory. Each prompt template consists of:

1. **LLM API Parameters**: These control aspects such as temperature, model, etc., and are defined in the template rather than in the main code. This allows for individual control at the advisor level.
Here's an updated version of the documentation section, including the new `<$datetime$>` tag:

2. **System Instruction**: Defines the role of the advisor. You can include text files in the system prompt using the `<$file.txt$>` tag notation. For instance, to include an `aboutme.txt` file located in the `/me` directory, you would write `<$me/aboutme.txt$>`. Or if you had a document called `transcript.json` in JSON format in the `/content/raw` directory, you could include that with `<$content/raw/transcript.json$>`. 

You can also include multiple files from a directory using the directory inclusion tag `<$dir:path/to/directory/*.ext$>`. For example, to include all text files from a 'knowledge' directory, you would write `<$dir:knowledge/*.txt$>`. 

Additionally, you can insert the current date or time into the system prompt using the `<$datetime$>` tag. For example, `<$datetime:%Y-%m-%d$>` will be replaced with the current date in the format `YYYY-MM-DD`. This enables you to inject customized instructions, dynamic content, and custom files into the system message. The text of the system instruction is written as escaped markdown.

3. **Tools**: You can optionally specify an array of tools that the advisor has access to. Each tool should correspond to a Python file in the `tools` directory and must have an `execute` function.

### Creating Advisors

To create a new advisor, copy an existing advisor JSON file and modify it as necessary. The app assumes you are using OpenRouter to route your LLM calls.

### Using Tools

Tools in this framework provide powerful, modular functionality that can be leveraged by advisors and the AI assistant. Here's how to effectively use tools:

#### Tool Calling Mechanism

1. **Automatic Discovery**: Tools in the `tools/` directory are automatically discovered and registered.
2. **Dynamic Execution**: Tools can be called dynamically by the AI based on the task requirements.
3. **Flexible Parameters**: Each tool supports various input parameters defined in its metadata.

#### Example Tool Assignment

```json
{
    "model": "openai/gpt-4o-mini",
    "tool_choice": "auto",
    "messages": [
        {
            "role": "system",
            "content": "ABOUT ME:\n\n<$me/aboutme.md$>\n\nABOUT YOU:\n\nYou are a tool-calling LLM assistant. Your goal is to carefully process each user message and determine whether you need to respond naturally or make a tool call to assist the user effectively. You provide helpful and comprehensive answers."
        }
    ],
    "tools": ["get_current_weather","get_research","get_transcription", "get_hacker_news_headlines", "use_notion", "use_brainstorm"]
}
```

#### Tool Capabilities