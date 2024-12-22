# repo_tools/generate_repo_tree.py
import os
from termcolor import colored
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def load_gitignore_patterns():
    """Load patterns from .gitignore file and create a PathSpec object."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gitignore_path = os.path.join(root_dir, '.gitignore')
    try:
        with open(gitignore_path, 'r') as f:
            patterns = f.read().splitlines()
        return PathSpec.from_lines(GitWildMatchPattern, patterns)
    except FileNotFoundError:
        print(colored("No .gitignore file found.", 'yellow'))
        return PathSpec([])

def generate_directory_tree(root_dir, gitignore_spec):
    """Generate a tree-like directory structure using ASCII characters."""
    tree = []
    
    def add_to_tree(dirpath, items, prefix=""):
        items = sorted(items)
        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            full_path = os.path.join(dirpath, item)
            rel_path = os.path.relpath(full_path, root_dir)
            
            # Skip .git directory
            if '.git' in rel_path.split(os.sep):
                print(colored(f"Skipping .git: {rel_path}", 'yellow'))
                continue
            
            # Skip __pycache__, __init__.py, and .gitkeep
            if item in ['__pycache__', '__init__.py', '.gitkeep']:
                print(colored(f"Skipping: {rel_path}", 'yellow'))
                continue
            
            # Use pathspec to check if file should be ignored
            if gitignore_spec.match_file(rel_path):
                print(colored(f"Ignoring: {rel_path}", 'red'))
                continue
                
            print(colored(f"Including: {rel_path}", 'green'))
            
            # Choose the appropriate characters based on whether it's the last item
            connector = "└── " if is_last else "├── "
            
            # Add the item to the tree
            tree.append(prefix + connector + item)
            
            # If it's a directory, recursively add its contents
            if os.path.isdir(full_path):
                # Prepare the prefix for children
                child_prefix = prefix + ("    " if is_last else "│   ")
                
                # Get directory contents
                try:
                    dir_items = os.listdir(full_path)
                    add_to_tree(full_path, dir_items, child_prefix)
                except PermissionError:
                    continue
    
    # Start with root directory contents
    root_items = os.listdir(root_dir)
    add_to_tree(root_dir, root_items)
    
    return "\n".join(tree)

def generate_repo_tree():
    """Generate a tree structure and save it to repo_tools/repo_readme_tree.md."""
    try:
        print(colored("Generating repository directory tree...", 'blue'))
        
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.dirname(os.path.abspath(__file__))
        
        print(colored(f"Scanning directory: {root_dir}", 'blue'))
        
        gitignore_spec = load_gitignore_patterns()
        print(colored("Loaded gitignore patterns", 'blue'))
        
        tree = generate_directory_tree(root_dir, gitignore_spec)
        
        output_path = os.path.join(output_dir, 'repo_readme_tree.md')
        with open(output_path, 'w') as f:
            f.write("# Repository Structure\n\n```\n")
            f.write(tree)
            f.write("\n```")
        
        print(colored(f"Directory tree saved to {output_path}", 'green'))
        
    except Exception as e:
        print(colored(f"Error generating repository directory tree: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_repo_tree()