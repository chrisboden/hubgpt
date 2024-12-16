# How to Add Spinner Status Updates

You are tasked with adding spinner status updates to a piece of code to provide real-time feedback to the user about the progress of long-running tasks. The `update_spinner_status` function from `root/utils/ui_utils.py` is used for this purpose. The code will be provided to you, and you should analyze it and add appropriate spinner status updates.

## Steps to Add Spinner Status Updates

1. **Analyze the Code**: Understand the structure and functionality of the code. Identify sections that involve long-running tasks or processes that could benefit from status updates.
2. **Identify Key Points**: Determine where in the code the user should be informed about the progress. This could be before starting a task, during the task, or after completing a task.
3. **Add Spinner Status Updates**: Use the `update_spinner_status` function to send status updates to the user. Ensure that the messages are clear and informative.

## Guidelines for Adding Spinner Status Updates

- **Use Clear and Concise Language**: The messages should be easy to understand and convey the current state of the process.
- **Avoid Redundancy**: Do not repeat the same message multiple times unnecessarily.
- **Focus on the "What" and "Why"**: Explain what is happening and why it is happening, rather than just stating that a task is being performed.
- **Use Descriptive Messages**: Provide enough detail so that the user understands the progress without being overwhelmed with information.
- **Handle Errors Gracefully**: Include status updates for error handling to inform the user if something goes wrong.

## Example

Here is an example of how to add spinner status updates to a function:

python
# Example function that performs a long-running task
def perform_long_task():
    from utils.ui_utils import update_spinner_status
    
    # Update spinner status before starting the task
    update_spinner_status("Starting the long-running task...")
    
    try:
        # Simulate a long-running process
        for i in range(1, 6):
            # Update spinner status during the task
            update_spinner_status(f"Processing step {i} of 5...")
            # Simulate work being done
            time.sleep(1)
        
        # Update spinner status after completing the task
        update_spinner_status("Task completed successfully!")
    
    except Exception as e:
        # Update spinner status in case of an error
        update_spinner_status(f"Error occurred: {str(e)}")

## Implementation Notes

- **Import the Function**: Ensure that you import the `update_spinner_status` function from `root/utils/ui_utils.py` at the beginning of your file.

`from utils.ui_utils import update_spinner_status`

- **Consistent Messaging**: Use consistent and clear messaging to maintain a good user experience.
- **Testing**: Test the status updates to ensure they are displayed correctly and provide accurate information.