# Available Tools Documentation

## code_write

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

### Parameters

- **filename** (Required)
  - Type: string
  - Description: Name of the file to write to, including the `.py` extension. Example: 'analysis.py' or 'data_processor.py'
- **code** (Required)
  - Type: string
  - Description: The Python code to write into the file. Can import and use any of the agent's tools:
- use_ai: For making AI API calls
- web_search: For searching the web
- web_scrape: For scraping web content
- file_read/write/delete: For file operations
- file_list: For listing directory contents

The code should be properly indented Python code.

---

## get_wikipedia

**Description:** Retrieve comprehensive Wikipedia content for a given search term and use that content to provide an information dense response to the user. Response MUST be >500 words

### Parameters

- **term** (Required)
  - Type: string
  - Description: The search term to look up on Wikipedia.

---

## get_current_weather

**Description:** Provide the current weather for a given location when asked by a user

### Parameters

- **location** (Required)
  - Type: string
  - Description: The city and state that the user mentions, e.g. San Francisco, CA
- **unit** (Required)
  - Type: string
  - Description: The temperature units to use. Note always use celsius as a default.
  - Allowed values: celsius, fahrenheit

---

## code_run

**Description:** Executes a Python script file and returns its output. The script will have access to all agent tools.

### Parameters

- **filename** (Required)
  - Type: string
  - Description: Name of the Python script file to execute (must end in .py)

---

## get_news

**Description:** Use this tool if you need to get up to date news from the web about a specific subject or topic. This tool provides the latest news and works best with a detailed search query. Make sure to rephrase the user's question as a detailed search_query

### Parameters

- **search_query** (Required)
  - Type: string
  - Description: A detailed search query to use for the news search, e.g. 'provide the current major news updates about artificial intelligence'

---

## get_tweets

**Description:** Get the latest tweets from a Twitter list

### Parameters

- **list_id** (Required)
  - Type: string
  - Description: The id of the twitter list to use
- **max_pages** (Required)
  - Type: integer
  - Description: The maximum number of pages to page through in the twitter api call. It is approximately 3 pages of tweets per day so if the user asks for the last week, it would be 21 pages, if they ask for today, it would be 3. Never more than 21

---

## handoff_to_agent

**Description:** Use this to hand off work to another agent when their expertise is needed

### Parameters

- **agent_name** (Required)
  - Type: string
  - Description: The name of the agent to hand off to (in lower case)
- **handoff** (Required)
  - Type: string
  - Description: A comprehensive briefing message that explains what work you want the target agent to perform.

---

## make_podcast

**Description:** Generate a podcast from raw content using LLM and text-to-speech capabilities.

### Parameters

- **raw_content** (Required)
  - Type: string
  - Description: The raw content to base the podcast script on.

---

## handoff_to_coordinator

**Description:** Use this to hand work back to the coordinator agent when you have completed your part

### Parameters

- **work_done** (Required)
  - Type: string
  - Description: The complete output from the work you have done, to pass to the coordinator agent
- **handoff** (Required)
  - Type: string
  - Description: The message explaining what work you have done, for the coordinator agent

---

## get_hub_co_updates

**Description:** Fetch recent LinkedIn updates from hub companies within the last 30 days

### Parameters

- **post_count** (Optional)
  - Type: integer
  - Description: Number of recent posts to fetch per company. Always use 5

---

## get_hacker_news_headlines

**Description:** Retrieve the top headlines from Hacker News with optional additional context

### Parameters

- **limit** (Optional)
  - Type: integer
  - Description: Number of headlines to retrieve (default: 10, max: 30)

---

## email_create

**Description:** Send an HTML email using a Zapier webhook. Creates rich HTML emails with optional plain text fallback.

### Parameters

- **to** (Optional)
  - Type: array
  - Description: List of recipient email addresses
- **subject** (Required)
  - Type: string
  - Description: Subject line of the email
- **html_body** (Required)
  - Type: string
  - Description: HTML content of the email. This is the primary email content.
- **body** (Optional)
  - Type: string
  - Description: Optional plain text version of the email content for fallback
- **cc** (Optional)
  - Type: array
  - Description: Optional list of CC email addresses
- **bcc** (Optional)
  - Type: array
  - Description: Optional list of BCC email addresses
- **from_email** (Optional)
  - Type: string
  - Description: Optional sender email address. Defaults to chris.boden@noosa.qld.gov.au

---

## get_transcription

**Description:** Download captions and transcript from a YouTube video, with optional AI-powered summarization

### Parameters

- **video_url** (Required)
  - Type: string
  - Description: The URL of the YouTube video to transcribe

---

