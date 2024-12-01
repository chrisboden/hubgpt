
https://x.com/hive_echo/status/1862599826934014053
full cursor rules:
Guidelines for Creating and Utilizing Tools in http://tools.py:

1. Initial Assessment:
- Before creating new tools, read through http://tools.py to understand the existing tools and their functionalities.

2. Tool Creation:
- Create new tools as functions within http://tools.py. If http://tools.py doesn't exist, create it.
- Ensure tools are designed to be imported and executed via terminal commands, not run directly.

3. Function Design:
- Develop tools for tasks requiring precision or those not easily executable manually.
- Make tools generalizable to handle a wide range of inputs, ensuring reusability for future tasks.
- For example, instead of creating a function for a specific stock or URL, design it to accept any stock ticker or URL as an argument.
- Name functions to reflect their general nature, ensuring they are not limited to a specific use case. This enhances flexibility and adaptability for future applications.

4. Output:
- Tools must always print their output.

5. Execution:
- Do not run http://tools.py directly. Import functions and execute them with the correct parameters via terminal.
- Always use the `python -c "..."` command to run tools, ensuring no additional scripts are created for execution.

6. Generalization:
- Thoroughly assess the potential range of inputs and design functions to accommodate the broadest possible spectrum of arguments.
- Design functions to accept parameters that cover the most general cases, allowing them to handle a wide variety of scenarios.
- Ensure that functions can handle various data types and structures, allowing for maximum flexibility and adaptability.
- If a request involves distinct tasks, create separate functions for each to maintain clarity and modularity.
- Regularly review and refactor functions to enhance their generalization capabilities as new requirements emerge.

7. Error Handling:
- If errors occur, rewrite functions to resolve them.

8. Script Management:
- Avoid creating additional .py scripts for function execution. Always import and run with proper arguments using the `python -c "..."` command.

9. Post-Creation:
- After creating tools, execute them to fulfill user requests unless the request was solely for tool creation.
