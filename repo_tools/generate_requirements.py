# repo_tools/generate_requirements.py
import subprocess
import os
import fnmatch
from termcolor import colored

def generate_requirements():
    """Generate requirements.txt using pipreqs, excluding dependencies in .gitignore"""
    try:
        print(colored("Generating requirements.txt...", 'blue'))
        
        # Get the root directory (one level up from current script)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        print(colored(f"Scanning directory: {root_dir}", 'blue'))
        
        # Use the full path to pipreqs that we know works
        pipreqs_path = "/Library/Frameworks/Python.framework/Versions/3.11/bin/pipreqs"
        command = f"{pipreqs_path} --force {root_dir}"
        
        # Run pipreqs
        subprocess.run(command, shell=True, check=True)
        
        # Read .gitignore patterns
        gitignore_patterns = set()
        gitignore_path = os.path.join(root_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        gitignore_patterns.add(line)
        
        # Function to check if a package is ignored
        def is_ignored(package):
            for pattern in gitignore_patterns:
                if fnmatch.fnmatch(package, pattern):
                    return True
            return False
        
        # Read and filter requirements.txt
        requirements_path = os.path.join(root_dir, 'requirements.txt')
        with open(requirements_path, 'r') as f:
            packages = [line.strip() for line in f if line.strip() and not is_ignored(line)]
        
        # Write the filtered packages back to requirements.txt
        with open(requirements_path, 'w') as f:
            f.write('\n'.join(sorted(packages)))
        
        print(colored("\nFound packages:", 'green'))
        for pkg in packages:
            print(colored(f"- {pkg}", 'green'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_requirements()