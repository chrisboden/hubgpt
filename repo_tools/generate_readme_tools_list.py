# repo_tools/generate_tools_readme.py

import os
import importlib.util
import sys
from termcolor import colored

def import_module_from_path(file_path):
    """Import a module from file path with improved error handling."""
    try:
        # Add project root and tools directory to sys.path
        project_root = os.path.dirname(os.path.dirname(file_path))
        tools_dir = os.path.dirname(file_path)
        
        for path in [project_root, tools_dir]:
            if path not in sys.path:
                sys.path.insert(0, path)
        
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except ImportError as e:
        print(colored(f"Import error in {file_path}: {str(e)}", "yellow"))
        # Print the current Python path to help diagnose
        print(colored(f"Current sys.path: {sys.path}", "cyan"))
        return None
    except Exception as e:
        print(colored(f"Unexpected error importing {file_path}: {str(e)}", "red"))
        return None
    finally:
        # Clean up paths
        for path in [project_root, tools_dir]:
            if path in sys.path:
                sys.path.remove(path)

def truncate_description(description, max_words=60):
    """Truncate the description to a maximum number of words and add an ellipsis if necessary."""
    words = description.split()
    if len(words) > max_words:
        return ' '.join(words[:max_words]) + '...'
    return description

def generate_tools_list():
    """Generate a detailed markdown list of tools with their descriptions."""
    tools_dir = "tools"
    if not os.path.exists(tools_dir):
        print(colored("Tools directory not found!", "red"))
        return
    
    # Collect successful and failed imports
    successful_tools = []
    failed_imports = []
    
    # Iterate through Python files
    for filename in sorted(os.listdir(tools_dir)):
        if filename.endswith('.py') and not filename.startswith('__'):
            file_path = os.path.join(tools_dir, filename)
            module = import_module_from_path(file_path)
            
            # Check if module has TOOL_METADATA
            if module and hasattr(module, 'TOOL_METADATA'):
                try:
                    tool_name = module.TOOL_METADATA['function']['name']
                    tool_description = module.TOOL_METADATA['function']['description']
                    
                    successful_tools.append((tool_name, tool_description))
                    print(colored(f"Added tool: {tool_name}", "green"))
                except (KeyError, TypeError) as e:
                    failed_imports.append((filename, str(e)))
                    print(colored(f"Error processing {filename}: {str(e)}", "yellow"))
            elif module:
                failed_imports.append((filename, "No TOOL_METADATA found"))
    
    # Write successful tools with their descriptions to repo_readme_tool_list.md
    with open('repo_tools/repo_readme_tool_list.md', 'w') as f:
        for index, (tool_name, tool_description) in enumerate(sorted(successful_tools), start=1):
            truncated_description = truncate_description(tool_description)
            f.write(f"{index}. `{tool_name}`: {truncated_description}\n")
    
    # Print summary of failed imports
    if failed_imports:
        print(colored("\nFailed Imports:", "red"))
        for filename, error in failed_imports:
            print(colored(f"{filename}: {error}", "yellow"))

if __name__ == "__main__":
    generate_tools_list()