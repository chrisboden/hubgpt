#Modules

Advisors - system prompt to ground persona in expert bio, with tools
Teams - agents with tools working in a team to complete a project
Notepads - collection of document files for q&a/synthesis, etc via llm


#Common components

## Streamlit ui
* Chat pane
*- show user inputs, llm responses, tool calls (todo)
*- save snippet, copy to clipboard, delete message
* Sidebar
*- Tabbed navigation: Advisors, Notepads, Teams
*- Dropdown selector for Advisors, Teams, Notepads
*- File upload

## Logging
* common log file across modules

## Chat histories
* load chat history
* clear chat
* archive chat

## Snippets
* Save snippets

## Prompt construction
* File/directory includes
* LLM param handling

## Tools
* Common tool spec (def execute)
* Tool utils for tool registry & handling available to each module
* Tools accessible to prompts/agents in each module

## Autodev
* Scripts that create readme's and cursor prompts to describe the code base and underlying api specs (eg llms), for the purposes of automating further development
