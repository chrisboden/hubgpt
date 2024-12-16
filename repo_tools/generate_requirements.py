# repo_tools/generate_requirements.py
import subprocess
import os
import tempfile
import shutil
from termcolor import colored
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def generate_requirements():
    """Generate requirements.txt using pipreqs, properly excluding .gitignore paths"""
    try:
        print(colored("Generating requirements.txt...", 'blue'))
        
        # Get the root directory (one level up from current script)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(colored(f"Scanning directory: {root_dir}", 'blue'))

        # Read .gitignore patterns
        gitignore_path = os.path.join(root_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
        else:
            gitignore_content = ""
        
        # Create PathSpec object from gitignore patterns
        spec = PathSpec.from_lines(GitWildMatchPattern, gitignore_content.splitlines())

        # Create temporary directory for filtered files
        with tempfile.TemporaryDirectory() as temp_dir:
            print(colored("Creating filtered project copy...", 'blue'))
            
            # Walk through the directory and copy non-ignored files
            for root, dirs, files in os.walk(root_dir):
                # Get relative path from project root
                rel_root = os.path.relpath(root, root_dir)
                
                # Remove ignored directories from dirs list (in-place)
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.join(rel_root, d))]
                
                for file in files:
                    rel_path = os.path.join(rel_root, file)
                    if not spec.match_file(rel_path) and file.endswith('.py'):
                        # Create target directory
                        target_dir = os.path.join(temp_dir, rel_root)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(
                            os.path.join(root, file),
                            os.path.join(temp_dir, rel_path)
                        )

            # Use pipreqs on the filtered directory
            print(colored("Running pipreqs on filtered files...", 'blue'))
            pipreqs_path = "/Library/Frameworks/Python.framework/Versions/3.11/bin/pipreqs"
            requirements_temp = os.path.join(temp_dir, 'requirements.txt')
            command = f"{pipreqs_path} --force --savepath {requirements_temp} {temp_dir}"
            
            subprocess.run(command, shell=True, check=True)
            
            # Copy requirements file to original directory
            if os.path.exists(requirements_temp):
                with open(requirements_temp, 'r') as f:
                    packages = f.read().splitlines()
                
                # Write sorted packages
                requirements_path = os.path.join(root_dir, 'requirements.txt')
                with open(requirements_path, 'w') as f:
                    f.write('\n'.join(sorted(packages)))
                
                print(colored("\nFound packages:", 'green'))
                for pkg in sorted(packages):
                    print(colored(f"- {pkg}", 'green'))
            else:
                print(colored("No requirements.txt was generated", 'yellow'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_requirements()