import os
import json
import ast
import inspect
import re
from pathlib import Path
from termcolor import colored

def get_file_stats(file_path):
    """Get file size and line count."""
    size = os.path.getsize(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = sum(1 for _ in f)
    return f"{size/1024:.1f}KB", lines

def extract_dependencies(content):
    """Extract import statements and potential dependencies."""
    deps = {
        "imports": [],
        "pip_packages": set(),
        "env_vars": set()
    }
    
    # Find all import statements
    import_pattern = r'^(?:from|import)\s+([^\s]+)(?:\s+import\s+(?:[^\s,]+(?:\s*,\s*[^\s,]+)*))?\s*$'
    imports = re.findall(import_pattern, content, re.MULTILINE)
    deps["imports"] = [imp for imp in imports if not imp.startswith('.')]
    
    # Extract potential pip packages (excluding standard library)
    std_lib = {'os', 'sys', 'json', 're', 'datetime', 'time', 'math', 'random', 'pathlib', 'inspect', 'ast', 'uuid', 'typing', 'io', 'urllib'}
    deps["pip_packages"] = {pkg.split('.')[0] for pkg in deps["imports"] if pkg.split('.')[0] not in std_lib}
    
    # Find environment variables
    env_pattern = r'os\.getenv\(["\']([^"\']+)["\']\)'
    env_vars = re.findall(env_pattern, content)
    deps["env_vars"] = set(env_vars)
    
    return deps

def parse_docstring(docstring):
    """Parse docstring to extract parameter descriptions."""
    if not docstring:
        return {}
    
    param_desc = {}
    lines = docstring.split('\n')
    current_param = None
    
    for line in lines:
        line = line.strip()
        param_match = re.match(r'^(?::param|Args?:?\s+)(\w+):\s*(.*)$', line)
        if param_match:
            current_param = param_match.group(1)
            param_desc[current_param] = param_match.group(2)
        elif current_param and line and not line.startswith(':'):
            param_desc[current_param] += ' ' + line
            
    return param_desc

def infer_parameter_type(name, default_value=None, docstring_hint=None):
    """Infer parameter type based on name, default value, and docstring."""
    if default_value is not None:
        if isinstance(default_value, bool):
            return "boolean"
        elif isinstance(default_value, int):
            return "integer"
        elif isinstance(default_value, float):
            return "number"
        elif isinstance(default_value, list):
            return "array"
        elif isinstance(default_value, dict):
            return "object"
    
    # Try to infer from name
    if name in {'id', 'count', 'max', 'min', 'limit', 'offset', 'page', 'max_tokens', 'max_pages'}:
        return "integer"
    elif name in {'is_', 'has_', 'should_', 'enable', 'disable'}:
        return "boolean"
    elif name.endswith('_list') or name.endswith('s') or name == 'messages':
        return "array"
    elif name in {'temperature', 'threshold', 'score'}:
        return "number"
    
    # Default to string
    return "string"

def extract_tool_metadata(file_path):
    """Extract metadata from a tool file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try to find TOOL_METADATA in the file
        metadata_start = content.find('TOOL_METADATA = ')
        if metadata_start != -1:
            # Count opening and closing braces to find the complete dictionary
            start_pos = content.find('{', metadata_start)
            if start_pos != -1:
                pos = start_pos + 1
                brace_count = 1
                in_string = False
                string_char = None
                metadata_str = '{'
                
                while pos < len(content) and brace_count > 0:
                    char = content[pos]
                    metadata_str += char
                    
                    if char == '\\' and in_string:
                        # Skip escaped characters in strings
                        if pos + 1 < len(content):
                            metadata_str += content[pos + 1]
                            pos += 2
                            continue
                    
                    if char in '"\'':
                        if not in_string:
                            in_string = True
                            string_char = char
                        elif in_string and char == string_char:
                            in_string = False
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            
                    pos += 1
                
                if brace_count == 0:
                    try:
                        # Parse the metadata string as JSON first
                        try:
                            metadata = json.loads(metadata_str)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, try Python literal eval
                            metadata = ast.literal_eval(metadata_str)
                            
                        if isinstance(metadata, dict) and "type" in metadata and "function" in metadata:
                            return metadata
                    except Exception as e:
                        print(colored(f"Error evaluating metadata in {file_path.name}: {str(e)}", "red"))
                        return None
                
        return None
    except Exception as e:
        print(colored(f"Error processing {file_path}: {str(e)}", "red"))
        return None

def update_tools_metadata():
    """Update all_tools.json with function metadata for each tool."""
    print(colored("Starting metadata update process...", "cyan"))
    
    # Get the tools directory path
    tools_dir = Path(__file__).parent
    root_dir = tools_dir.parent
    
    tools_data = {"functions": []}
    
    # Process each Python file in the tools directory
    for file_path in tools_dir.glob("*.py"):
        if file_path.name == "update_metadata.py" or file_path.name == "__init__.py":
            continue
            
        print(colored(f"Processing {file_path.name}...", "yellow"))
        
        # Extract metadata
        metadata = extract_tool_metadata(file_path)
        
        if metadata and "type" in metadata and "function" in metadata:
            tools_data["functions"].append(metadata)
            print(colored(f"✓ Found metadata for {file_path.name}", "green"))
        else:
            print(colored(f"⚠ No metadata found for {file_path.name}", "yellow"))
    
    # Sort functions by name
    tools_data["functions"].sort(key=lambda x: x["function"]["name"])
    
    # Write the updated metadata to all_tools.json
    output_path = root_dir / "all_tools.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tools_data, f, indent=4)
    
    print(colored(f"\nMetadata updated successfully! Output written to {output_path}", "green"))

if __name__ == "__main__":
    update_tools_metadata() 