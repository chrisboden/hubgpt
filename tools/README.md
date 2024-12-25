# Working with Tools in HubGPT

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

**Description:** A secure tool for performing various file system operations with timeout protection and size limits. 

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

## get_hacker_news_headlines

**Source File:** `get_hacker_news_headlines.py`

**Description:** Retrieve the top headlines from Hacker News with optional additional context

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

## make_podcast

**Source File:** `make_podcast.py`

**Description:** Generate a podcast from raw content using LLM and text-to-speech capabilities.

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

## web_image_search

**Source File:** `web_image_search.py`

**Description:** Perform an image search to find the best matching image for a given user request

---

## web_scrape

**Source File:** `web_scrape.py`

**Description:** Fetches and extracts textual content from a specified URL and saves it to a file. The content is saved in markdown format with proper formatting and structure. Use this tool to gather information from web pages for learning, data analysis, or incorporating external knowledge into your responses. This is helpful when you need to access the latest information or data not available in your existing knowledge base.

---

## web_search

**Source File:** `web_search.py`

**Description:** Performs a comprehensive web search using multiple search providers (Brave, Tavily, DuckDuckGo, etc.). The tool optimizes the search query using AI and returns ranked results. Use this tool when you need to find current information about any topic, verify facts, or gather data from multiple sources. Results include titles, URLs, and descriptions from various web pages.

---

