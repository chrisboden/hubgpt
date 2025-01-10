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
