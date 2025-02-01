# Hubgpt

A conversational AI agent framework that allows the creation of personalised advisors/agents with tool support. Developed for low code tinkering by members and friends of the Peregian Digital Hub. 

The Hubgpt project is a customisable conversational AI framework that allows users to create AI-powered advisors using prompt templates and tools. Each advisor is configured with specific LLM parameters (like model and temperature) and system instructions, offering granular control over the advisor's behavior and expertise. 

## Backend

The code is written in python and rather than using a database, it mostly uses flat files to keep things simple for beginners. It avoids front end development as much as possible by using the python front end framework, Streamlit, for the UI. The system works well locally but not yet optimised for efficient cloud hosting.

## Prompt Engineering

A key feature is the ability to include external text files eg .json, .md, .txt, etc - but not .pdf or .doc, directly in the 'advisor' system prompts using a special tag notation. This enables developers to inject rich context into the advisor's instructions by specifying custom files, such as personal biographies or detailed guidelines or work docs. This functionality not only personalises the output but also allows the AI to be grounded in extensive data sources, like long-form biographies or research documents. This is particularly powerful when leveraging large context window models that can accept prompts containing hundreds of thousands of tokens, enabling the advisor to operate with far deeper and more nuanced knowledge.

## LLM Models

The system uses OpenRouter as an LLM gateway. This allows users to have a single LLM account (with openrouter) and obviates the need for maintaining developer accounts with each Llm provider. This enables the developer to tap into hundreds of models with varying capabilities, costs, etc.

## Front end

Built on Streamlit for an intuitive user interface, the app makes it easy to interact with advisors, load chat histories, and integrate new tools and context-rich instructions for highly customised AI experiences. This allows beginners to focus on writing simple python functions and editing json/markdown files.

# Get Started

## Clone the Repository

```bash
git clone https://github.com/chrisboden/hubgpt.git
```

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


## The UI

This app uses [Streamlit](https://streamlit.io/), a Python framework for rapid prototyping.

- Advisors populate a dropdown list in the sidebar. Advisors can be added and edited through json or md files in the `/advisors` directory - some examples are included
- Upon selecting an advisor, the current chat history is loaded into the UI, allowing for long-running conversations.
- The conversation history is saved in the `/chats` directory
- The "Clear Conversation" button archives the current chat history to a JSON file in the `/archive` directory.
- Each assistant (aka advisor) message includes:
    - A **Save** button to append the message to a `snippets.json` file in the `/ideas` directory.
    - A **Copy** button to add the content to your clipboard.

# Repository Structure

```
├── .DS_Store
├── .cursorignore
├── .cursorrules
├── .env_copy
├── .gitignore
├── .streamlit
│   └── config.toml
├── README.md
├── advisors
│   ├── .DS_Store
│   ├── Bob_Smith.json
│   ├── Mr_Feedreader.json
│   ├── Naval_Ravikant.json
│   ├── Ted_Smith.md
│   ├── Yuval_Harari.json
│   ├── archive
│   ├── chats
│   └── jane_smith.md
├── advisors.py
├── agents.py
├── content
├── cursor_prompts
│   ├── howto_add_comments.md
│   ├── howto_add_logging.md
│   ├── howto_add_spinner_status.md
│   ├── howto_computer-use.md
│   ├── howto_researcher.md
│   ├── howto_understand_this_app.md
│   ├── howto_use_openrouter.md
│   ├── howto_write_docs.md
│   ├── howto_write_tools.md
│   ├── linkedin_tool_notes.txt
│   ├── tools.py
│   └── use_and_make_tools.md
├── data
├── logs
├── main.py
├── me
│   ├── example_aboutme.txt
│   ├── example_custom_instructions.txt
│   ├── example_tips_copywriting.txt
├── notepads
│   ├── default
│   │   ├── .DS_Store
│   │   ├── files
│   │   │   ├── .DS_Store
│   │   │   └── example_paper.pdf
│   │   └── index.json
│   └── notepad_prompt.json
├── notepads.py
├── papers
├── repo_tools
│   ├── README.md
│   ├── generate_env_file.py
│   ├── generate_readme_tools_list.py
│   ├── generate_repo_readme.py
│   ├── generate_repo_tree.py
│   ├── generate_requirements.py
│   ├── generate_tools_readme.py
│   ├── repo_readme_advisors.md
│   ├── repo_readme_intro.md
│   ├── repo_readme_notepads.md
│   ├── repo_readme_tool_list.md
│   ├── repo_readme_tree.md
│   ├── tools_readme_howto.md
│   └── tools_readme_intro.md
├── requirements.txt
├── snippets
├── static
│   ├── README.md
│   ├── css
│   │   ├── advisors.css
│   │   └── style.css
│   └── images
│       ├── logo.png
│       └── logo_full.png
├── tools
│   ├── .DS_Store
│   ├── README.md
│   ├── code_run.py
│   ├── code_write.py
│   ├── email_create.py
│   ├── file_operations.py
│   ├── get_advice.py
│   ├── get_company_updates.py
│   ├── get_current_weather.py
│   ├── get_hacker_news.py
│   ├── get_news.py
│   ├── get_research.py
│   ├── get_transcription.py
│   ├── get_tweets.py
│   ├── get_website.py
│   ├── get_wikipedia.py
│   ├── handoff_to_agent.py
│   ├── handoff_to_coordinator.py
│   ├── linkedin_bio_writer.py
│   ├── linkedin_research.py
│   ├── make_artifact.py
│   ├── make_book.py
│   ├── use_ai.py
│   ├── use_brainstorm.py
│   ├── use_github.py
│   ├── use_notion.py
│   ├── use_reasoning.py
│   ├── use_todo_list.py
│   ├── web_image_search.py
│   ├── web_read_page.py
│   ├── web_scrape.py
│   └── web_search.py
└── utils
    ├── README.md
    ├── chat_utils.py
    ├── db_utils.py
    ├── file_utils.py
    ├── llm_utils.py
    ├── log_utils.py
    ├── message_utils.py
    ├── notion_utils.py
    ├── prompt_utils.py
    ├── scrape_utils.py
    ├── search_utils.py
    ├── tool_utils.py
    └── ui_utils.py
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

1. `code_run`: Executes a Python script file and returns its output. The script will have access to all agent tools.
2. `code_write`: Creates or overwrites a Python script with the provided code. The script will automatically have access to all agent tools through pre-configured imports. Example usage patterns: 1. Using the AI tool: from tools import use_ai result = use_ai.execute( messages=[{'role': 'user', 'content': 'Your prompt here'}] ) 2. Using web search: from tools import web_search results = web_search.execute(query='Your search query') 3. File...
3. `email_create`: Send an HTML email using a Zapier webhook. Creates rich HTML emails with optional plain text fallback.
4. `file_operations`: A secure tool for performing various file system operations including reading, writing, editing files, managing directories, and downloading files from the web.

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
5. `get_advice`: Get advice from a specified advisor based on the given query posed by a user
6. `get_company_updates`: Fetch the recent LinkedIn updates posted by a given list of companies
7. `get_current_weather`: Provide the current weather for a given location when asked by a user
8. `get_hacker_news`: Retrieve and summarize the top headlines from Hacker News
9. `get_news`: Use this tool if you need to get up to date news from the web about a specific subject or topic. This tool provides the latest news and works best with a detailed search query. Make sure to rephrase the user's question as a detailed search_query
10. `get_research`: This tool is a very intelligent web research agent that can search, find, gather and synthesise highly relevant information for a given topic. Use this tool whenever you are asked to perform research on topic. You simply give the agent a research_brief in natural language, eg 'please research the spacex starship launch schedule'. It will return a comprehensive research dossier...
11. `get_transcription`: Download captions and transcript from a YouTube video, with optional AI-powered summarization
12. `get_tweets`: Get the latest tweets from a given Twitter list
13. `get_website`: Get the definitive website url for a given term
14. `get_wikipedia`: Retrieve comprehensive Wikipedia content for a given search term and use that content to provide an information dense response to the user. Response MUST be >500 words
15. `handoff_to_agent`: Use this to hand off work to another agent when their expertise is needed
16. `handoff_to_coordinator`: Use this to hand work back to the coordinator agent when you have completed your part
17. `linkedin_bio_writer`: Generate a professional biography from a LinkedIn profile
18. `linkedin_research`: This tool performs comprehensive LinkedIn research on a person or company, collecting profile data and posts, analyzing them, and providing detailed insights.
19. `make_artifact`: Generate self-contained HTML artifacts (widgets) with embedded JavaScript and CSS
20. `make_book`: Generate a complete book with multiple chapters on any topic using AI. The tool handles research, writing, and formatting.
21. `use_ai`: Makes a call to an AI language model API with specified messages and model selection. Importantly, this tool supports file inclusion in message content using special syntax. Key Features: 1. File Inclusion: Use <$filename$> syntax to include file contents 2. Directory Inclusion: Use <$dir:pattern$> for multiple files 3. Context Preservation: Include previous results or conversation history Common Usage Patterns: 1....
22. `use_brainstorm`: Generate creative ideas using various brainstorming techniques. Respond with a clean markdown format that presents the ideas in the most useful format for the user. Methods: Reverse brainstorming involves identifying ways to cause a problem or achieve the opposite effect. Perfect for spotting potential issues and coming up with innovative solutions. Role storming adopting the perspective of someone else to...
23. `use_github`: Interact with GitHub repositories to perform various operations like searching repos, getting file contents, managing PRs and issues, etc. Repository information can be provided via URL or owner/repo parameters. Can also analyze repositories and answer questions about them.
24. `use_notion`: The use_notion tool allows you to interact with Notion by either creating new pages or fetching existing page content.
25. `use_sequential_thinking`: A tool for dynamic, reflective, and self-directed sequential reasoning. It stores a chain of thoughts, supports revisions and branching, and can optionally suggest next steps using an LLM if needed.
26. `use_todo_list`: Use a todo list to keep track of activities. You can use `create` to create a new todo list, optionally with initial items. Use `read` to read a given todo list by passing in the id. Use `update` to update the state of the todo list, eg by marking an item as 'done'. Each item follows a structured schema with...
27. `web_image_search`: Perform an image search to find the best matching image for a given user request
28. `web_read_page`: Fetches and returns a clean markdown version of a webpage.
29. `web_scrape`: Fetches and extracts textual content from a specified URL and saves it to a file. The content is saved in markdown format with proper formatting and structure. Use this tool to gather information from web pages for learning, data analysis, or incorporating external knowledge into your responses. This is helpful when you need to access the latest information or data...
30. `web_search`: Performs a comprehensive web search using multiple search providers (Brave, Tavily, DuckDuckGo, etc.). The tool optimizes the search query using AI and returns ranked results. Use this tool when you need to find current information about any topic, verify facts, or gather data from multiple sources. Results include titles, URLs, and descriptions from various web pages.


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

