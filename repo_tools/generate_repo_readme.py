# repo_tools/generate_repo_readme.py

import os
import subprocess

def run_script(script_path):
    """Run a Python script using subprocess."""
    try:
        print(f"Running script: {script_path}")
        result = subprocess.run(['python3', script_path], check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running script {script_path}: {e.stderr}")
        return False
    return True

def read_file_content(file_path):
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return ""

def generate_repo_readme():
    """Generate the repository README by combining multiple markdown files."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the paths to the scripts
    scripts = [
        "generate_repo_tree.py",
        "generate_readme_tools_list.py",
        "generate_requirements.py",
        "generate_tools_readme.py"
    ]
    
    # Run the scripts
    for script in scripts:
        script_path = os.path.join(script_dir, script)
        if not run_script(script_path):
            print(f"Failed to run script {script}. Exiting.")
            return
    
    readme_files = [
        "repo_readme_intro.md",
        "repo_readme_tree.md",
        "repo_readme_advisors.md",
        "repo_readme_tool_list.md",
        "repo_readme_notepads.md"
    ]
    
    readme_content = ""
    
    for file_name in readme_files:
        file_path = os.path.join(script_dir, file_name)
        content = read_file_content(file_path)
        if content:
            if readme_content:  # Add a newline between sections
                readme_content += "\n\n"
            readme_content += content
    
    # Write the combined content to the README.md file in the root directory
    root_dir = os.path.dirname(script_dir)
    readme_path = os.path.join(root_dir, "README.md")
    
    with open(readme_path, 'w') as readme_file:
        readme_file.write(readme_content)
    
    print(f"README.md generated successfully at {readme_path}.")


if __name__ == "__main__":
    generate_repo_readme()