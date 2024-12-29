# tools/use_todo_list.py
import os
import json
import uuid
from pathlib import Path
from termcolor import colored

# Ensure data directory exists
DATA_DIR = Path("data/todo")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_todo_list(items=None):
    """Create a new todo list with optional initial items"""
    todo_id = str(uuid.uuid4())[:8]  # Short UUID
    file_path = DATA_DIR / f"{todo_id}.json"
    
    # Initialize with items if provided
    initial_items = [validate_todo_item(item) for item in items] if items else []
    
    with open(file_path, 'w') as f:
        json.dump(initial_items, f)
    
    print(colored(f"SUCCESS: Created new todo list '{todo_id}' with {len(initial_items)} items at {file_path}", "green"))
    return {
        "result": f"New todo list `{todo_id}` has been created at {file_path}. Initial items: {initial_items}",
        "todo_id": todo_id,
        "file_path": str(file_path),
        "items": initial_items
    }

def validate_todo_item(item):
    """Validate and normalize a todo item according to the schema"""
    if isinstance(item, dict):
        return {
            "id": str(uuid.uuid4())[:6],  # Generate tiny UUID
            "todo": item.get("todo", str(item.get("task", ""))),  # Support both 'todo' and 'task' keys
            "done": item.get("done", False),
            "note": item.get("note", "")
        }
    return {
        "id": str(uuid.uuid4())[:6],
        "todo": str(item),  # Convert to string if it's not a dict
        "done": False,
        "note": ""
    }

def read_todo_list(todo_id):
    """Read the contents of a todo list"""
    file_path = DATA_DIR / f"{todo_id}.json"
    
    if not file_path.exists():
        print(colored(f"ERROR: Todo list '{todo_id}' does not exist at {file_path}", "red"))
        return {"error": f"Todo list {todo_id} does not exist"}
    
    with open(file_path, 'r') as f:
        items = json.load(f)
    
    print(colored(f"SUCCESS: Read todo list '{todo_id}' with {len(items)} items", "blue"))
    return {
        "result": f"Current state of todo list `{todo_id}`: {items}",
        "todo_id": todo_id,
        "items": items
    }

def update_todo_list(todo_id, items):
    """Update the contents of a todo list while preserving existing items"""
    file_path = DATA_DIR / f"{todo_id}.json"
    
    if not file_path.exists():
        print(colored(f"ERROR: Todo list '{todo_id}' does not exist at {file_path}", "red"))
        return {"error": f"Todo list {todo_id} does not exist"}
    
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
    
    with open(file_path, 'w') as f:
        json.dump(updated_items, f, indent=2)
    
    print(colored(f"SUCCESS: Updated todo list '{todo_id}' with {len(updated_items)} items", "yellow"))
    return {
        "result": f"Todo list `{todo_id}` has been updated. New state is {updated_items}",
        "todo_id": todo_id,
        "items": updated_items
    }

def execute(llm_client=None, operation=None, todo_id=None, items=None, **kwargs):
    """
    Execute todo list operations
    
    Parameters:
    - operation: 'create', 'read', or 'update'
    - todo_id: Required for read/update operations
    - items: Required for update operation (list of items/tasks)
    """
    try:
        print(colored(f"Executing todo list operation: {operation}", "cyan"))
        
        if operation == "create":
            result = create_todo_list(items)
        elif operation == "read":
            result = read_todo_list(todo_id)
        elif operation == "update":
            if not todo_id:
                print(colored("ERROR: todo_id is required for update operation", "red"))
                return {"error": "todo_id is required for update operation"}
            result = update_todo_list(todo_id, items)
        else:
            print(colored(f"ERROR: Invalid operation '{operation}'", "red"))
            return {"error": f"Invalid operation: {operation}"}
        
        print(colored(f"Operation '{operation}' completed successfully", "green"))
        return result
        
    except Exception as e:
        error_msg = f"ERROR in todo list operation '{operation}': {str(e)}"
        print(colored(error_msg, "red"))
        return {"error": error_msg}

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