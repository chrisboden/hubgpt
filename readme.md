# Hubgpt

A conversational AI agent framework that allows the creation of personalised advisors with tool support. Developed for low code tinkering by members and friends of the Peregian Digital Hub.

The Hubgpt project is a customisable conversational AI framework that allows users to create AI-powered advisors using prompt templates and tools. Each advisor is configured with specific LLM parameters (like model and temperature) and system instructions, offering granular control over the advisor's behavior and expertise. 

One standout feature is the ability to include external files directly in the system prompts using a special tag notation. This enables developers to inject rich context into the advisor’s instructions by specifying custom files, such as personal biographies or detailed guidelines. This functionality not only personalises the output but also allows the AI to be grounded in extensive data sources, like long-form biographies or research documents. This is particularly powerful when leveraging large context window models that can accept prompts containing hundreds of thousands of tokens, enabling the advisor to operate with far deeper and more nuanced knowledge. 

Built on Streamlit for an intuitive user interface, the app makes it easy to interact with advisors, load chat histories, and integrate new tools and context-rich instructions for highly customized AI experiences.

## Clone the Repository

```bash
git clone https://github.com/chrisboden/hubgpt.git
```

> **Note**: This is a private repo. Ensure you have the appropriate access permissions.

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Setup Environment Variables

1. Rename the `.env_copy` file to `.env`.
2. Add your API keys to the `.env` file.

## Running the App

To run the app, use:

```bash
streamlit run main.py
```

## Adding Tools

Place any tools in the `tools` directory. Each tool must have an `execute` function, like the example below:

```python
# Example Tool: get_current_weather.py
def execute(location, unit="celsius"):
    # Logic to fetch current weather
    return {
        "location": location,
        "temperature": "18",
        "unit": unit,
        "forecast": ["cloudy", "rainy"]
    }
```

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


### Using tools

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

**Available Tools**:

1. `web_search`: Performs comprehensive web searches using multiple search providers
2. `web_scrape`: Extracts and saves textual content from specified web URLs
3. `get_news`: Retrieves up-to-date news articles on specific topics
4. `file_read`: Reads and returns contents of specified files
5. `file_write`: Writes content to files, supporting multiple file types
6. `file_list`: Lists files and directories within a specified path
7. `use_ai`: Makes advanced AI API calls with flexible message and file inclusion
8. `get_research`: Conducts in-depth web research and synthesizes comprehensive information
9. `get_advice`: Generates contextual advice from specified advisors
10. `code_run`: Executes Python scripts and returns their output
11. `code_write`: Creates or overwrites Python scripts
12. `email_create`: Sends HTML emails via Zapier webhook
13. `file_delete`: Removes specified files from the filesystem
14. `get_current_weather`: Provides current weather for a given location
15. `get_hacker_news_headlines`: Retrieves top headlines from Hacker News
16. `get_hub_co_updates`: Fetches recent LinkedIn updates from hub companies
17. `get_transcription`: Downloads and summarizes YouTube video captions
18. `get_tweets`: Retrieves latest tweets from a specified Twitter list
19. `get_website`: Finds definitive website URL for a given term
20. `get_wikipedia`: Retrieves comprehensive Wikipedia content for a search term
21. `handoff_to_agent`: Transfers work to another specialized agent
22. `handoff_to_coordinator`: Returns completed work to the main coordinator
23. `linkedin_research`: Performs in-depth LinkedIn research on people or companies
24. `make_podcast`: Generates podcasts from raw content
25. `use_brainstorm`: Generates creative ideas using various brainstorming techniques
26. `use_notion`: Creates and fetches Notion pages

#### Best Practices

1. **Context Awareness**: Choose tools that best match the specific task
2. **Error Handling**: Always be prepared to handle potential tool execution errors
3. **Streaming Support**: Some tools support `direct_stream` for real-time responses

#### Tool Metadata

Each tool includes metadata describing its:
- Name
- Description
- Required and optional parameters
- Streaming capabilities

#### Advanced Usage

Tools can be used within advisor prompts, in code generation, or dynamically by the AI assistant to complete complex tasks.



## Notepads

## Notepads

Notepads is a powerful document-based chat interface that allows you to:

### Key Features
- Create multiple independent notepads
- Upload and analyze multiple documents per notepad
- Maintain separate chat histories for each notepad
- Sync files between local storage and cloud (Gemini)

### How Notepads Work

1. **Creating Notepads**
   - Click "New Notepad" to create a unique workspace
   - Each notepad gets a unique ID and can be renamed
   - Notepads are stored in the `notepads/` directory

2. **File Management**
   - Upload documents directly into a notepad
   - Select which files to include in your chat context
   - Files are automatically synced with Gemini's cloud storage
   - Supports multiple file types for comprehensive analysis

3. **Chat Functionality**
   - Maintain separate chat histories for each notepad
   - Chat history is automatically saved
   - Clear chat history with a single button
   - Delete individual messages as needed

4. **Document Analysis**
   - Ask questions about uploaded documents
   - AI uses all selected documents to provide context-aware responses
   - Supports complex multi-document queries

### Best Practices
- Use different notepads for different projects or topics
- Regularly sync and manage your files
- Take advantage of the selective file inclusion feature



## The UI

This app uses [Streamlit](https://streamlit.io/), a Python framework for rapid prototyping.

- Advisors populate a dropdown list in the sidebar.
- Upon selecting an advisor, the current chat history is loaded into the UI, allowing for long-running conversations. The conversation history is saved in the `/chats` directory
- The "Clear Conversation" button archives the current chat history to a JSON file in the `/archive` directory.
- Each assistant (aka advisor) message includes:
    - A **Save** button to append the message to a `snippets.json` file in the `/ideas` directory.
    - A **Copy** button to add the content to your clipboard.

## Bonus

One quite powerful tool to use is the get_tweets tool. This gets tweets from a given twitter list and inserts them into a prompt, eg see the Mr Feedreader prompt. Get a free account with RapidAPI (using your google account) and sign up for this particular Twitter api (also free, no credit card) - https://rapidapi.com/davethebeast/api/twitter241/pricing - it allows 500 free api calls per month. Find your rapid api key and put in the env file.

## Testing

This project uses pytest for unit testing.

To run all tests:

```
pytest
```

To run tests with more detailed output:

```
pytest -v -s
```

