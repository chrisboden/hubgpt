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
        tools_dir = os.path.join(project_root, "tools")
        
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

def get_intro_text():
    """Read intro text from template file if it exists."""
    template_path = os.path.join("repo_tools", "tools_readme_intro.md")
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read().strip() + "\n\n"
        else:
            print(colored(f"No intro template found at {template_path}", "yellow"))
            return ""
    except Exception as e:
        print(colored(f"Error reading intro template: {str(e)}", "red"))
        return ""
    
def get_howto_text():
    """Read intro text from template file if it exists."""
    template_path = os.path.join("repo_tools", "tools_readme_howto.md")
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read().strip() + "\n\n"
        else:
            print(colored(f"No intro template found at {template_path}", "yellow"))
            return ""
    except Exception as e:
        print(colored(f"Error reading intro template: {str(e)}", "red"))
        return ""

def generate_tools_list():
    """Generate a detailed markdown list of tools with their descriptions."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_dir = os.path.join(project_root, "tools")
    print(colored(f"Checking for tools directory at: {tools_dir}", "magenta"))
    if not os.path.exists(tools_dir):
        print(colored("Tools directory not found!", "red"))
        return
    
    # Open the output file
    with open(os.path.join(tools_dir, "README.md"), "w") as f:
        # Write the title
        f.write("# Working with Tools in HubGPT\n\n")
        
        # Write the intro text
        intro_text = get_intro_text()
        if intro_text:
            f.write(intro_text)
            print(colored("Added intro text to README", "green"))
        
        # Write the howto text
        howto_text = get_howto_text()
        if howto_text:
            f.write(howto_text)
            print(colored("Added howto text to README", "green"))
        

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
                        
                        successful_tools.append((tool_name, tool_description, filename))
                        print(colored(f"Added tool: {tool_name}", "green"))
                    except (KeyError, TypeError) as e:
                        failed_imports.append((filename, str(e)))
                        print(colored(f"Error processing {filename}: {str(e)}", "yellow"))
                elif module:
                    failed_imports.append((filename, "No TOOL_METADATA found"))
        
        # Write successful tools to file with markdown sections
        for tool_name, tool_description, filename in sorted(successful_tools):
            f.write(f"## {tool_name}\n\n")
            f.write(f"**Source File:** `{filename}`\n\n")
            f.write(f"**Description:** {tool_description}\n\n")
            f.write("---\n\n")  # Markdown horizontal rule as separator
        
        # Print summary of failed imports
        if failed_imports:
            print(colored("\nFailed Imports:", "red"))
            for filename, error in failed_imports:
                print(colored(f"{filename}: {error}", "yellow"))

if __name__ == "__main__":
    generate_tools_list()