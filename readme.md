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

## The UI

This app uses [Streamlit](https://streamlit.io/), a Python framework for rapid prototyping.

- Advisors populate a dropdown list in the sidebar.
- Upon selecting an advisor, the current chat history is loaded into the UI, allowing for long-running conversations. The conversation history is saved in the `/chats` directory
- The "Clear Conversation" button archives the current chat history to a JSON file in the `/archive` directory.
- Each assistant (aka advisor) message includes:
    - A **Save** button to append the message to a `snippets.json` file in the `/ideas` directory.
    - A **Copy** button to add the content to your clipboard.

## Bonus

One quite powerful tool to use is the fetchtweets tool. This gets tweets from a given twitter list and inserts them into a prompt, eg see the Mr Feedreader prompt. Get a free account with RapidAPI (using your google account) and sign up for this particular Twitter api (also free, no credit card) - https://rapidapi.com/davethebeast/api/twitter241/pricing - it allows 500 free api calls per month. Find your rapid api key and put in the env file.

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

