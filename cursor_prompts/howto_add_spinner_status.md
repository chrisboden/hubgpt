# How to Add Spinner Status Updates in Tools

## Overview

Spinner status updates are a critical component of creating user-friendly, transparent tools that keep users informed during long-running or complex processes. By leveraging the `update_spinner_status()` function from `utils/ui_utils.py`, you can provide real-time feedback about the progress of your tool's execution. Your directive is to add spinner status, not to refactor, remove or edit other code. 

## Key Principles

1. **Transparency**: Keep users informed about what's happening
2. **Clarity**: Use concise, descriptive messages
3. **Progressive Communication**: Update status at key stages of execution
4. **Error Handling**: Provide informative error messages

## Implementation Strategy

### 1. Import Required Modules

```python
from termcolor import colored
from utils.ui_utils import update_spinner_status
```

### 2. Identify Key Process Stages

Analyze your tool's workflow and identify critical stages where users would benefit from status updates:
- Before starting a task
- During task execution
- After completing subtasks
- Upon encountering errors

### 3. Add Status Updates with Best Practices

#### Basic Status Update Pattern
```python
# Before starting a task
update_spinner_status("Initializing process...")
print(colored("Initializing process...", "green"))

# During task execution
update_spinner_status(f"Processing item {current_item} of {total_items}")
print(colored(f"Processing item {current_item} of {total_items}", "green"))

# After completing a task
update_spinner_status("Task completed successfully")
print(colored("Task completed successfully", "green"))

# Error handling
update_spinner_status(f"Error occurred: {str(error)}")
print(colored(f"Error occurred: {str(error)}", "red"))
```

### 4. Real-World Example: Brainstorming Tool

Let's examine the `use_brainstorm.py` tool to see spinner status updates in action:

```python
def execute(llm_client=None, brief: str = None, method: str = "six_hats") -> str:
    try:
        # Initial status update
        update_spinner_status("Generating initial ideas...")
        print(colored("Generating initial ideas...", "green"))
        
        # Generate initial ideas
        initial_response = llm_client.chat.completions.create(...)
        initial_ideas = parse_bullet_points(initial_response.choices[0].message.content)
        
        # Progress update
        update_spinner_status(f"Received {len(initial_ideas)} initial ideas.")
        print(colored(f"Received {len(initial_ideas)} initial ideas.", "green"))
        
        # Process each idea with updates
        for i, idea in enumerate(initial_ideas, 1):
            update_spinner_status(f"Processing idea {i} of {len(initial_ideas)}: {idea}")
            print(colored(f"Processing idea {i} of {len(initial_ideas)}: {idea}", "green"))
            
            # Idea processing logic...
        
        # Final stage update
        update_spinner_status("Converting tree to Markdown...")
        print(colored("Converting tree to Markdown...", "green"))
        
        return markdown_result

    except Exception as e:
        update_spinner_status(f"Error occurred: {str(e)}")
        print(colored(f"Error occurred: {str(e)}", "red"))
        return f"Error: {str(e)}"
```

## Advanced Techniques

### Conditional Status Updates
```python
def execute(...):
    try:
        # Only update if a significant change occurs
        if len(results) > threshold:
            update_spinner_status(f"Processed {len(results)} significant items")
    except Exception as e:
        update_spinner_status(f"Processing interrupted: {str(e)}")
```

### Logging Integration
```python
import logging

def execute(...):
    try:
        logging.info("Starting process")
        update_spinner_status("Initializing...")
        # Tool logic
    except Exception as e:
        logging.error(f"Process failed: {str(e)}")
        update_spinner_status(f"Error: {str(e)}")
```

## Common Pitfalls to Avoid

1. **Avoid Spam**: Don't update status too frequently
2. **Be Specific**: Provide meaningful context in updates
3. **Handle Errors Gracefully**: Always have an error status update
4. **Use Consistent Formatting**: Maintain a uniform update style
5. Do not make changes to existing code, just add spinner status
6. Do not remove docstrings or comments

## Recommended Practices

- Use `colored()` for visual differentiation
- Combine `update_spinner_status()` with `print()`
- Provide both technical and user-friendly messages
- Include progress indicators when possible (e.g., "Processing 3/10 items")

## Conclusion

Effective spinner status updates transform user experience by providing transparency, reducing uncertainty, and creating a more interactive tool. By following these guidelines, you'll create tools that are not just functional, but also user-friendly and communicative.