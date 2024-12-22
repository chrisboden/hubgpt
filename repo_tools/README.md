# Repository Tools

This directory contains utility scripts to help manage and document various aspects of the HubGPT repository. Below is a list of the tools and their purposes:

## Tools

### 1. `generate_repo_tree.py`
- **Purpose:** Generates a tree-like directory structure of the repository, excluding files and directories specified in the `.gitignore` file.
- **Output:** Saves the directory tree to `repo_tools/repo_readme_tree.md`.
- **Usage:** Run the script directly.
  ```bash
  python repo_tools/generate_repo_tree.py
  ```

### 2. `generate_env_file.py`
- **Purpose:** Creates a stripped version of the `.env` file, where all key values are set to empty strings, useful for sharing without exposing sensitive information.
- **Output:** Generates a `.env_copy` file in the root directory.
- **Usage:** Run the script directly.
  ```bash
  python repo_tools/generate_env_file.py
  ```

### 3. `generate_requirements.py`
- **Purpose:** Automatically generates a `requirements.txt` file by scanning Python files for import statements and validating the packages against PyPI.
- **Output:** Saves the `requirements.txt` file in the root directory.
- **Usage:** Run the script directly.
  ```bash
  python repo_tools/generate_requirements.py
  ```

### 4. `generate_tools_readme.py`
- **Purpose:** Generates a `README.md` file in the `tools` directory, listing all available tools with their descriptions and source files.
- **Output:** Creates or updates `tools/README.md`.
- **Usage:** Run the script directly.
  ```bash
  python repo_tools/generate_tools_readme.py
  ```

## How to Use

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Tools:**
   Each tool can be run individually by executing the corresponding Python script as shown above.

## Notes

- Ensure that all scripts have the necessary permissions to read and write files in the repository.
- The scripts are designed to be run from the root directory of the repository to ensure correct path resolution.
- For any issues or errors, refer to the terminal output for detailed error messages and take appropriate actions.