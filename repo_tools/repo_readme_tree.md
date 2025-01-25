# Repository Structure

```
├── .DS_Store
├── .cursorignore
├── .cursorrules
├── .env_copy
├── .gitignore
├── .streamlit
│   └── config.toml
├── advisors
│   ├── .DS_Store
│   ├── Bob_Smith.json
│   ├── Mr_Feedreader.json
│   ├── Mr_Tokenizer.md
│   ├── Naval_Ravikant.json
│   ├── Ted_Smith.md
│   ├── Yuval_Harari.json
│   ├── archive
│   ├── chats
│   └── jane_smith.md
├── advisors.py
├── agents.py
├── api
│   ├── PRD.md
│   ├── README.md
│   ├── api_utils
│   │   ├── README.md
│   │   ├── chat_utils.py
│   │   ├── client.py
│   │   ├── db_utils.py
│   │   ├── file_utils.py
│   │   ├── llm_utils.py
│   │   ├── log_utils.py
│   │   ├── message_utils.py
│   │   ├── notion_utils.py
│   │   ├── prompt_utils.py
│   │   ├── scrape_utils.py
│   │   ├── search_utils.py
│   │   ├── tool_utils.py
│   │   └── ui_utils.py
│   ├── config.py
│   ├── dependencies.py
│   ├── index.html
│   ├── inspect_data.py
│   ├── main.py
│   ├── models
│   │   ├── advisors.py
│   │   └── chat.py
│   ├── requirements.txt
│   ├── routers
│   │   ├── advisors.py
│   │   └── chat.py
│   ├── server.log
│   ├── services
│   │   ├── .DS_Store
│   │   ├── advisor_service.py
│   │   ├── chat_service.py
│   │   └── storage_service.py
│   └── static
│       └── index.html
├── content
├── cursor_prompts
│   ├── howto_add_comments.md
│   ├── howto_add_logging.md
│   ├── howto_add_spinner_status.md
│   ├── howto_computer-use.md
│   ├── howto_handle_function_calling.md
│   ├── howto_researcher.md
│   ├── howto_understand_this_app.md
│   ├── howto_use_openrouter.md
│   ├── howto_work_with_supabase.md
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
├── readme.md
├── real_estate_poem.txt
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
├── send_poem.py
├── snippets
├── standalone_tools.py
├── static
│   ├── .DS_Store
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
│   ├── use_crm.py
│   ├── use_github.py
│   ├── use_notion.py
│   ├── use_reasoning.py
│   ├── use_team.py
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
    ├── time_utils.py
    ├── tool_utils.py
    └── ui_utils.py
```