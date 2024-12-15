# repo_tools/generate_requirements.py
import subprocess
import os
from termcolor import colored

def generate_requirements():
    """Generate requirements.txt using pipreqs"""
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
        
        # Read and display results
        with open(os.path.join(root_dir, 'requirements.txt'), 'r') as f:
            packages = f.read().splitlines()
            print(colored("\nFound packages:", 'green'))
            for pkg in sorted(packages):
                print(colored(f"- {pkg}", 'green'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_requirements()