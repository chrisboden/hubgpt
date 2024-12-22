# Hub GPT Utils

The `utils` directory contains various utility modules designed to support the functionality of the main application. Each module provides specific utilities for different tasks, such as database management, language model interactions, file handling, and more. Below is a detailed overview of each module:

## Modules Overview

### `db_utils.py`
- **Purpose**: Provides utilities for managing a DuckDB database, specifically for storing and retrieving agent run data.
- **Classes**:
  - `AgentRunsDB`: Manages database connections and operations.
- **Methods**:
  - `__init__`: Initializes the database connection and creates necessary tables.
  - `_create_tables`: Creates the `runs` and `steps` tables if they do not exist.
  - `create_run`: Creates a new run entry in the database.
  - `add_step`: Adds a new step to a specific run.
  - `get_all_runs`: Retrieves all run entries.
  - `get_steps_for_run`: Retrieves all steps for a specific run.
  - `clear_database`: Clears all data from the database (useful for testing).

### `llm_utils.py`
- **Purpose**: Provides utilities for interacting with language models, handling responses, and managing chat history.
- **Classes**:
  - `ResponseHandler`: Manages LLM response processing and UI updates.
  - `ChatHistoryManager`: Manages chat history updates and persistence.
- **Functions**:
  - `get_llm_response`: Retrieves a response from an LLM based on provided messages and chat history.

### `chat_utils.py`
- **Purpose**: Provides utilities for managing chat history, including loading and saving chat data.
- **Functions**:
  - `load_chat_history`: Loads chat history from a JSON file.
  - `save_chat_history`: Saves chat history to a JSON file.
  - `clear_chat_history`: Clears the chat history file.

### `file_utils.py`
- **Purpose**: Provides utilities for handling file paths and ensuring file safety.
- **Functions**:
  - `sanitize_filename`: Sanitizes a filename to remove invalid characters.
  - `is_safe_path`: Checks if a file path is within a safe directory.
  - `get_safe_filepath`: Gets a safe file path and optionally creates intermediate directories.

### `tool_utils.py`
- **Purpose**: Provides utilities for dynamically loading and executing tools.
- **Functions**:
  - `load_tools`: Dynamically loads and registers tool modules from a specified directory.
  - `execute_tool`: Executes a specified tool with given arguments and standardizes its response.

### `notion_utils.py`
- **Purpose**: Provides utilities for interacting with the Notion API, including creating pages and converting Markdown to Notion blocks.
- **Classes**:
  - `NotionClient`: Manages interactions with the Notion API.
- **Methods**:
  - `create_page`: Creates a new page in Notion.
  - `_markdown_to_notion_blocks`: Converts Markdown text to Notion blocks.
  - `_parse_markdown_table`: Converts a Markdown table to Notion table blocks.

### `prompt_utils.py`
- **Purpose**: Provides utilities for processing prompts, including handling file and directory inclusions and parsing Markdown messages.
- **Functions**:
  - `include_directory_content`: Recursively includes contents of files matching a directory pattern.
  - `include_file_content`: Includes contents of a specific file with support for nested inclusions.
  - `process_inclusions`: Processes file and directory inclusions in text content.
  - `parse_markdown_messages`: Parses markdown content into a structured list of messages.
  - `load_advisor_data`: Loads advisor configuration from either Markdown or JSON file.
  - `load_prompt`: Prepares prompt messages by incorporating conversation history.

### `scrape_utils.py`
- **Purpose**: Provides utilities for scraping web content.
- **Classes**:
  - `Scraper`: Base class for web scrapers.
  - `BasicScraper`: Implements a basic web scraper with enhanced resilience.
  - `ResilientScraper`: Tries scraping with each provider until one succeeds.
- **Methods**:
  - `scrape`: Scrapes content from a URL and returns markdown content.

### `search_utils.py`
- **Purpose**: Provides utilities for searching the web using various search providers.
- **Classes**:
  - `SearchProvider`: Base class for search providers.
  - `DDGSearchProvider`: Implements a search provider using the DuckDuckGo API.
  - `TavilySearchProvider`: Implements a search provider using the Tavily API.
  - `ResilientSearcher`: Tries searching with each provider until one succeeds.
- **Functions**:
  - `generate_search_query`: Generates an optimized search query using an LLM.
  - `perform_search`: High-level search function that combines query generation and execution.

### `message_utils.py`
- **Purpose**: Provides utilities for managing and displaying chat messages in a Streamlit interface.
- **Functions**:
  - `display_messages`: Renders messages in a Streamlit chat interface with interactive features.
  - `remove_message`: Removes a message from the list based on its index.

### `ui_utils.py`
- **Purpose**: Provides utilities for managing UI elements, such as spinners.
- **Functions**:
  - `update_spinner_status`: Updates the spinner status message dynamically.

## Usage

Each module is designed to be imported and used in other parts of the application. For example, to use the `AgentRunsDB` class for managing agent run data, you can import it as follows:

```python
from utils.db_utils import AgentRunsDB
db = AgentRunsDB()
run_id = db.create_run()
print(f"New run created with ID: {run_id}")
```

Similarly, to use the `ResponseHandler` class for managing LLM responses, you can import it as follows:

```python
from utils.llm_utils import ResponseHandler
response_handler = ResponseHandler(client, status_placeholder, response_placeholder)
full_response, function_call_data = response_handler.handle_streamed_response(stream)
```
