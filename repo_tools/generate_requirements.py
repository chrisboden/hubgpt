# repo_tools/generate_requirements.py
import subprocess
import os
import tempfile
import shutil
import ast
from termcolor import colored
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def extract_imports_from_file(file_path):
    """Extract all import statements from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
                    
        return imports
    except Exception as e:
        print(colored(f"Warning: Could not parse {file_path}: {str(e)}", 'yellow'))
        return set()

def generate_requirements():
    """Generate requirements.txt using both pipreqs and direct import scanning"""
    try:
        print(colored("Generating requirements.txt...", 'blue'))
        
        # Get the root directory (one level up from current script)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(colored(f"Scanning directory: {root_dir}", 'blue'))

        # Get list of our own Python modules to exclude
        local_modules = {
            os.path.splitext(f)[0] 
            for f in os.listdir(root_dir) 
            if os.path.isfile(os.path.join(root_dir, f)) and f.endswith('.py')
        }
        local_modules.update({
            d for d in os.listdir(root_dir)
            if os.path.isdir(os.path.join(root_dir, d)) and 
            os.path.exists(os.path.join(root_dir, d, '__init__.py'))
        })
        print(colored(f"Excluding local modules: {', '.join(local_modules)}", 'blue'))

        # Read .gitignore patterns
        gitignore_path = os.path.join(root_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
        else:
            gitignore_content = ""
        
        # Create PathSpec object from gitignore patterns
        spec = PathSpec.from_lines(GitWildMatchPattern, gitignore_content.splitlines())

        # Set to store all direct imports
        all_imports = set()

        # Create temporary directory for filtered files
        with tempfile.TemporaryDirectory() as temp_dir:
            print(colored("Creating filtered project copy...", 'blue'))
            
            # First, handle root-level Python files
            for file in os.listdir(root_dir):
                if file.endswith('.py'):
                    rel_path = file
                    if not spec.match_file(rel_path):
                        source_path = os.path.join(root_dir, file)
                        target_path = os.path.join(temp_dir, file)
                        print(colored(f"Including root file: {file}", 'blue'))
                        shutil.copy2(source_path, target_path)
                        # Extract imports from root file
                        all_imports.update(extract_imports_from_file(source_path))
            
            # Then walk through subdirectories
            for root, dirs, files in os.walk(root_dir):
                if root == temp_dir:
                    continue
                    
                rel_root = os.path.relpath(root, root_dir)
                
                if spec.match_file(rel_root):
                    dirs[:] = []
                    continue
                
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.join(rel_root, d))]
                
                for file in files:
                    if file.endswith('.py'):
                        rel_path = os.path.join(rel_root, file)
                        if not spec.match_file(rel_path):
                            source_path = os.path.join(root, file)
                            target_dir = os.path.join(temp_dir, rel_root)
                            os.makedirs(target_dir, exist_ok=True)
                            target_path = os.path.join(target_dir, file)
                            print(colored(f"Including: {rel_path}", 'blue'))
                            shutil.copy2(source_path, target_path)
                            # Extract imports from this file
                            all_imports.update(extract_imports_from_file(source_path))

            # Use pipreqs on the filtered directory
            print(colored("\nRunning pipreqs on filtered files...", 'blue'))
            pipreqs_path = "/Library/Frameworks/Python.framework/Versions/3.11/bin/pipreqs"
            requirements_temp = os.path.join(temp_dir, 'requirements.txt')
            command = f"{pipreqs_path} --force --savepath {requirements_temp} {temp_dir}"
            
            subprocess.run(command, shell=True, check=True)
            
            # Merge pipreqs output with direct imports
            packages = set()
            if os.path.exists(requirements_temp):
                with open(requirements_temp, 'r') as f:
                    packages.update(line.split('==')[0] for line in f.read().splitlines())
            
            # Add common package mappings for imports that don't match package names
            package_mappings = {
                'google': 'google-generativeai',
                'bs4': 'beautifulsoup4',
                'dotenv': 'python-dotenv',
                'genai': 'google-generativeai',
                # Add more mappings as needed
            }
            
            # Add mapped package names and filter out local modules
            for imp in all_imports:
                if imp in package_mappings:
                    packages.add(package_mappings[imp])
                elif imp not in local_modules:  # Only add if not a local module
                    packages.add(imp)
            
            # Filter out standard library modules
            stdlib_modules = set([
                'os', 'sys', 'json', 'datetime', 'time', 'uuid', 'shutil', 
                'tempfile', 'pathlib', 'mimetypes', 'ast', 're', 'typing',
                'traceback', 'subprocess', 'inspect', 'logging', 'importlib',
                'glob', 'urllib'
            ])
            packages = {pkg for pkg in packages if pkg not in stdlib_modules and pkg not in local_modules}
            
            # Write final requirements.txt
            requirements_path = os.path.join(root_dir, 'requirements.txt')
            with open(requirements_path, 'w') as f:
                f.write('\n'.join(sorted(packages)))
            
            print(colored("\nFound packages:", 'green'))
            for pkg in sorted(packages):
                print(colored(f"- {pkg}", 'green'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_requirements()