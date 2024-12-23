# Hubgpt

A conversational AI agent framework that allows the creation of personalised advisors with tool support. Developed for low code tinkering by members and friends of the Peregian Digital Hub.

The Hubgpt project is a customisable conversational AI framework that allows users to create AI-powered advisors using prompt templates and tools. Each advisor is configured with specific LLM parameters (like model and temperature) and system instructions, offering granular control over the advisor's behavior and expertise. 

A key feature is the ability to include external files directly in the system prompts using a special tag notation. This enables developers to inject rich context into the advisor’s instructions by specifying custom files, such as personal biographies or detailed guidelines. This functionality not only personalises the output but also allows the AI to be grounded in extensive data sources, like long-form biographies or research documents. This is particularly powerful when leveraging large context window models that can accept prompts containing hundreds of thousands of tokens, enabling the advisor to operate with far deeper and more nuanced knowledge. 

Built on Streamlit for an intuitive user interface, the app makes it easy to interact with advisors, load chat histories, and integrate new tools and context-rich instructions for highly customized AI experiences.

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

- Advisors populate a dropdown list in the sidebar.
- Upon selecting an advisor, the current chat history is loaded into the UI, allowing for long-running conversations. The conversation history is saved in the `/chats` directory
- The "Clear Conversation" button archives the current chat history to a JSON file in the `/archive` directory.
- Each assistant (aka advisor) message includes:
    - A **Save** button to append the message to a `snippets.json` file in the `/ideas` directory.
    - A **Copy** button to add the content to your clipboard.