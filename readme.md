# HubGPT: A Conversational AI Agent Framework for the Peregian Digital Hub

HubGPT is a conversational AI agent framework designed to empower members and friends of the Peregian Digital Hub.  It utilizes a low-code approach, enabling the creation of sophisticated AI assistants and automated workflows through Python. Users interact with predefined "advisors," each representing an expert persona, and access various tools to perform tasks and answer questions.

## Key Concepts

* **Advisors:**  These are predefined expert personas (e.g., Naval Ravikant, Steve Jobs). Each advisor is represented by a configuration file (`.md` or `.json`) within the `advisors` directory. This configuration specifies:
    * **Instructions:** A detailed system prompt that defines the advisor's persona, knowledge base (often including excerpts from relevant books, articles, or podcasts). These are used to form context for the user interaction or response. This is handled dynamically, adding resilience to how the advisor can access its specific content
    * **Messages:** A set of example conversation starters or background information used to initiate and set context for conversations specific to an advisor type
    * **Tools:** A list of tools this advisor can invoke. These tools are implemented as separate Python modules, offering specific functionalities (e.g., web search, code execution, interacting with an external database, or invoking additional tools).

* **Tools:** These are Python modules within the `tools` directory. Each tool's core is an `execute()` function that can take various inputs, including tools from the `tools/` directory. This allows complex operations (like iterative research or complex workflows), without making errors more difficult to trace, or the code more difficult to modify through separate files. Tools have sophisticated support for direct streaming to the UI (`"direct_stream": True`), enabling real-time information updates making the user interface much more responsive.
    * Flexibility: Tools are designed to be reusable, able to accommodate various data types and formats. They can also call other tools, creating complex workflows.
    * Multimodality: The system can handle text, images, and potentially other media types when appropriate (`image_url` type in messages).

* **Language Model (LLM):** An external Language Model (LLM) API (like OpenAI) acts as the central engine. The LLM:
    * Interprets user prompts and context from conversations.
    *  Decides if a direct response is needed or if it should invoke a tool.
    * Passes instructions and parameters to chosen tools within the `tools/` directory based on tools available to that advisor, and their metadata.
    * Integrates the results of invoked tools back into the conversation.

* **Conversation Memory (Persistent Chat History):** A system for managing conversations,  saving the complete dialogue including the results of executing any tools within each turn to maintain consistency of context between interactions maintaining multi-turn consistency, and providing resilience to unexpected shutdowns or lost connectivity as it is written out to an associated file.


* **Filesystem Handling (`file_utils`):** Addresses file safety and permissions with security in mind. Crucially, this also manages the addition of new directories if a tool or API necessitates it which increases overall robustness when writing external files.

* **Notion Integrations (`notion_utils`):** Permits functionality to link the tools to the notion collaborative tools and platforms

* **Database Logging (`db_utils`):** A robust database logs the entirety of every agent interaction including user input, and tool calls, thus enabling robust debugging, auditing, or retrospective querying on any type of interaction with this application


## Workflow

1. **User Input:** The user interacts with the application via the Streamlit-powered chat interface.
2. **LLM Processing:** The framework prepares relevant information into an LLM request, which could include the history (context) obtained by the chat application, current prompt, plus an array of tool metadata associated with the selected advisor to facilitate tool selection logic by the LLM. (This information is not stored to avoid loss or corruption during unexpected interaction interruptions).  
3. **Tool Invocation (Optional):** If a tool needs to execute and external processes, the LLM provides arguments and the framework uses `subprocess` to execute it in isolation. If the invoked function delivers its tools results, then that result is parsed back to the llm. if a tool outputs a stream of data, then the data is obtained in real time as a stream delivered to the user interface.
4. **LLM Response:** The LLM processes the tool results (or directly answers without a tool call) to create the final response for the user. This is displayed in the Streamlit chat pane. This entire flow is logged to the DuckDB database for monitoring, replay, and auditing purposes.
5. **Conversation Persistence:** The conversation history, including tool executions and responses, is logged into associated files for replay and for use in other areas of the application


The framework aims to provide a flexible and robust platform for creating AI assistants at the Peregian Hub, suitable for handling diverse tasks and intricate interactions.  The inclusion of `.gitignore` based security and robust database handling significantly improves production performance.  Tools in the repo.py are designed for integration with the framework via direct imports and are designed to be dynamically loadable, executable without the need for generating files separately.  These tools support a form of streaming data from interacting external api results or from completing complex internal calculations needed for responding to user inputs in an accessible manner for the end-user