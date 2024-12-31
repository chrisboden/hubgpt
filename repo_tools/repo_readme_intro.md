# Hubgpt

A conversational AI agent framework that allows the creation of personalised advisors/agents with tool support. Developed for low code tinkering by members and friends of the Peregian Digital Hub. 

The Hubgpt project is a customisable conversational AI framework that allows users to create AI-powered advisors using prompt templates and tools. Each advisor is configured with specific LLM parameters (like model and temperature) and system instructions, offering granular control over the advisor's behavior and expertise. 

## Backend

The code is written in python and rather than using a database, it mostly uses flat files to keep things simple for beginners. It avoids front end development as much as possible by using the python front end framework, Streamlit, for the UI. The system works well locally but not yet optimised for efficient cloud hosting.

## Prompt Engineering

A key feature is the ability to include external text files eg .json, .md, .txt, etc - but not .pdf or .doc, directly in the 'advisor' system prompts using a special tag notation. This enables developers to inject rich context into the advisor’s instructions by specifying custom files, such as personal biographies or detailed guidelines or work docs. This functionality not only personalises the output but also allows the AI to be grounded in extensive data sources, like long-form biographies or research documents. This is particularly powerful when leveraging large context window models that can accept prompts containing hundreds of thousands of tokens, enabling the advisor to operate with far deeper and more nuanced knowledge.

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