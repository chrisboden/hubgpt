# tools/use_todo_list.py
# tools/use_todo_list.py
import os
import json
import uuid
from pathlib import Path
from termcolor import colored
from utils.ui_utils import update_spinner_status  # Added spinner status import

# Ensure data directory exists
DATA_DIR = Path("data/todo")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_todo_list(items=None):
    """
    Create a new todo list with optional initial items.
    
    This function generates a unique todo list ID, validates and processes 
    input items, and saves them to a JSON file in the data directory.
    
    Args:
        items (list, optional): Initial todo items to populate the list.
    
    Returns:
        dict: A dictionary containing todo list metadata and creation result.
    """
    # Generate a short unique identifier for the todo list
    todo_id = str(uuid.uuid4())[:8]  
    file_path = DATA_DIR / f"{todo_id}.json"
    
    # Update spinner to show initialization
    update_spinner_status(f"Creating new todo list: {todo_id}")
    
    # Validate and process input items
    initial_items = [validate_todo_item(item) for item in items] if items else []
    
    # Write items to JSON file
    with open(file_path, 'w') as f:
        json.dump(initial_items, f)
    
    # Provide success feedback
    print(colored(f"SUCCESS: Created new todo list '{todo_id}' with {len(initial_items)} items at {file_path}", "green"))
    update_spinner_status(f"Todo list {todo_id} created successfully")
    
    return {
        "result": f"New todo list `{todo_id}` has been created at {file_path}. Initial items: {initial_items}",
        "todo_id": todo_id,
        "file_path": str(file_path),
        "items": initial_items
    }

def validate_todo_item(item):
    """
    Validate and normalize a todo item to ensure consistent schema.
    
    This function handles different input formats and ensures each todo item 
    has a unique ID, description, completion status, and optional note.
    
    Args:
        item (dict or str): The todo item to validate and normalize.
    
    Returns:
        dict: A standardized todo item with required fields.
    """
    # Handle dictionary input with flexible keys
    if isinstance(item, dict):
        return {
            "id": str(uuid.uuid4())[:6],  # Generate tiny UUID
            "todo": item.get("todo", str(item.get("task", ""))),  # Support both 'todo' and 'task' keys
            "done": item.get("done", False),
            "note": item.get("note", "")
        }
    
    # Handle simple string input
    return {
        "id": str(uuid.uuid4())[:6],
        "todo": str(item),  # Convert to string if it's not a dict
        "done": False,
        "note": ""
    }

def read_todo_list(todo_id):
    """
    Read the contents of a specific todo list.
    
    Retrieves and returns the items from a todo list JSON file.
    
    Args:
        todo_id (str): The unique identifier of the todo list.
    
    Returns:
        dict: A dictionary containing the todo list items or an error message.
    """
    file_path = DATA_DIR / f"{todo_id}.json"
    
    # Check if todo list exists
    if not file_path.exists():
        update_spinner_status(f"ERROR: Todo list '{todo_id}' not found")
        print(colored(f"ERROR: Todo list '{todo_id}' does not exist at {file_path}", "red"))
        return {"error": f"Todo list {todo_id} does not exist"}
    
    # Read todo list items
    update_spinner_status(f"Reading todo list: {todo_id}")
    with open(file_path, 'r') as f:
        items = json.load(f)
    
    # Provide success feedback
    print(colored(f"SUCCESS: Read todo list '{todo_id}' with {len(items)} items", "blue"))
    update_spinner_status(f"Successfully read {len(items)} items from todo list")
    
    return {
        "result": f"Current state of todo list `{todo_id}`: {items}",
        "todo_id": todo_id,
        "items": items
    }

def update_todo_list(todo_id, items):
    """
    Update the contents of an existing todo list.
    
    Preserves existing items while allowing selective updates 
    based on item IDs.
    
    Args:
        todo_id (str): The unique identifier of the todo list.
        items (list): List of items to update.
    
    Returns:
        dict: A dictionary containing the updated todo list or an error message.
    """
    file_path = DATA_DIR / f"{todo_id}.json"
    
    # Verify todo list exists
    if not file_path.exists():
        update_spinner_status(f"ERROR: Todo list '{todo_id}' not found")
        print(colored(f"ERROR: Todo list '{todo_id}' does not exist at {file_path}", "red"))
        return {"error": f"Todo list {todo_id} does not exist"}
    
    # Update spinner to show processing
    update_spinner_status(f"Updating todo list: {todo_id}")
    
    # Read existing items
    with open(file_path, 'r') as f:
        existing_items = json.load(f)
    
    # Create a map of existing items by ID for easy lookup
    existing_map = {item['id']: item for item in existing_items}
    
    # Process updates
    for item in items:
        if isinstance(item, dict) and 'id' in item:
            if item['id'] in existing_map:
                # Update existing item while preserving other fields
                existing_map[item['id']].update(item)
    
    # Keep all items in their original order
    updated_items = existing_items
    
    # Write updated items back to file
    with open(file_path, 'w') as f:
        json.dump(updated_items, f, indent=2)
    
    # Provide success feedback
    print(colored(f"SUCCESS: Updated todo list '{todo_id}' with {len(updated_items)} items", "yellow"))
    update_spinner_status(f"Todo list {todo_id} updated successfully")
    
    return {
        "result": f"Todo list `{todo_id}` has been updated. New state is {updated_items}",
        "todo_id": todo_id,
        "items": updated_items
    }

def execute(llm_client=None, operation=None, todo_id=None, items=None, **kwargs):
    """
    Execute todo list operations with comprehensive error handling.
    
    Supports creating, reading, and updating todo lists with flexible input.
    
    Args:
        operation (str): The type of operation to perform ('create', 'read', 'update').
        todo_id (str, optional): Unique identifier for existing todo lists.
        items (list, optional): Todo items for create or update operations.
    
    Returns:
        dict: Operation result or error information.
    """
    try:
        # Initial spinner status
        update_spinner_status(f"Executing todo list operation: {operation}")
        print(colored(f"Executing todo list operation: {operation}", "cyan"))
        
        # Route to appropriate operation
        if operation == "create":
            result = create_todo_list(items)
        elif operation == "read":
            result = read_todo_list(todo_id)
        elif operation == "update":
            # Validate todo_id for update operation
            if not todo_id:
                update_spinner_status("ERROR: Missing todo_id for update")
                print(colored("ERROR: todo_id is required for update operation", "red"))
                return {"error": "todo_id is required for update operation"}
            result = update_todo_list(todo_id, items)
        else:
            # Handle invalid operations
            update_spinner_status(f"ERROR: Invalid operation '{operation}'")
            print(colored(f"ERROR: Invalid operation '{operation}'", "red"))
            return {"error": f"Invalid operation: {operation}"}
        
        # Final success status
        update_spinner_status(f"Operation '{operation}' completed successfully")
        print(colored(f"Operation '{operation}' completed successfully", "green"))
        return result
        
    except Exception as e:
        # Comprehensive error handling
        error_msg = f"ERROR in todo list operation '{operation}': {str(e)}"
        update_spinner_status(error_msg)
        print(colored(error_msg, "red"))
        return {"error": error_msg}

# Tool metadata for integration with AI systems
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_todo_list",
        "description": "Use a todo list to keep track of activities. You can use `create` to create a new todo list, optionally with initial items. Use `read` to read a given todo list by passing in the id. Use `update` to update the state of the todo list, eg by marking an item as 'done'. Each item follows a structured schema with id, todo (markdown description), done (boolean status), and note (contextual information).",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create", "read", "update"],
                    "description": "The operation to perform: create, read, or update the todo list"
                },
                "todo_id": {
                    "type": "string",
                    "description": "The ID of the todo list you wish to use read or update"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "todo": {"type": "string", "description": "Markdown description of the task"},
                            "done": {"type": "boolean", "description": "Whether the task is completed"},
                            "note": {"type": "string", "description": "Contextual information about the task status"}
                        },
                        "required": ["todo"]
                    },
                    "description": "List of todo items following the structured schema. Can be used when creating a new list or updating an existing one."
                }
            },
            "required": ["operation"]
        }
    }
}