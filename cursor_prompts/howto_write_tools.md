## How to Write a Tool

### Overview

Writing a tool for this conversational AI framework involves creating a Python module that defines an `execute` function and a `TOOL_METADATA` dictionary. The `execute` function handles the logic for the tool, while `TOOL_METADATA` provides information about the tool's name, description, and parameters.

### Step-by-Step Guide

1. **Create a New Tool File**

   - Navigate to the `tools` directory.
   - Create a new Python file for your tool, e.g., `my_tool.py`.

2. **Define the `execute` Function**

   - The `execute` function should contain the logic for your tool.
   - It can accept arguments and optionally use an LLM client for advanced processing.

   ```python
   def execute(llm_client=None, **kwargs):
       """
       Execute the tool logic.

       Parameters:
       - llm_client (optional): An LLM client for generating additional information.
       - **kwargs: Additional arguments specific to the tool.

       Returns:
       - dict: A dictionary with the tool's result and any follow-on instructions.
       """
       # Example logic
       result = "Your tool result here"

       # Optionally, the tool can make LLM calls if llm_client is provided
       if llm_client:
           prompt = f"Process the result: {result}"
           response = llm_client.chat.completions.create(
               model='gpt-4o-mini',
               messages=[{"role": "user", "content": prompt}]
           )
           result = response.choices[0].message.content.strip()

       return {
           "result": result,
           "follow_on_instructions": []  # Optional follow-on instructions
       }
   ```

   - **Using an LLM Call**: If your tool requires additional processing or context, you can make an LLM call. For example, in the `get_hacker_news_headlines.py` tool, an LLM call is used to generate a concise summary of each headline. Here's how you can integrate an LLM call within your tool:

   ```python
   # Example of integrating an LLM call within the execute function
   if llm_client:
       prompt = f"Provide a concise 1-2 sentence summary of the headline: {headline}. Start your response with 'Hola Friends, here's the tech news of the day'"
       response = llm_client.chat.completions.create(
           model='gpt-4o-mini',
           messages=[{"role": "user", "content": prompt}]
       )
       description = response.choices[0].message.content.strip()
   ```

3. **Define the `TOOL_METADATA` Dictionary**

   - The `TOOL_METADATA` dictionary provides information about the tool.
   - It includes the tool's name, description, and parameters.

   ```python
   TOOL_METADATA = {
       "type": "function",
       "function": {
           "name": "my_tool",
           "description": "A brief description of what the tool does.",
           "parameters": {
               "type": "object",
               "properties": {
                   "param1": {
                       "type": "string",
                       "description": "Description of param1"
                   },
                   "param2": {
                       "type": "integer",
                       "description": "Description of param2"
                   }
               },
               "required": ["param1"]
           }
       },
       "direct_stream": False  # Set to True if the tool should stream responses directly to the UI
   }
   ```

4. **Test Your Tool**

   - Ensure your tool works as expected by testing it manually.
   - Check the tool's output and handle any errors appropriately.

5. **Integrate Your Tool**

   - The tool will be automatically discovered and registered by `utils/tool_utils.py`.
   - No manual registration is required.

