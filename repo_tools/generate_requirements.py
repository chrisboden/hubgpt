# repo_tools/generate_requirements.py
import subprocess
import os
import tempfile
import shutil
import requests
import ast
from termcolor import colored
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
import traceback

def validate_package_on_pypi(package_name):
    """Check if a package exists on PyPI"""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.RequestException:
        return False

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

        # Define target directories for different dependency types
        target_dirs = {
            'api': ['api'],  # Core API dependencies
            'tools': ['tools'],  # Tool-specific dependencies
            'utils': ['utils']  # Utility dependencies
        }

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

        # Dictionary to store imports by category
        category_imports = {
            'api': set(),
            'tools': set(),
            'utils': set()
        }

        # Process each category
        for category, directories in target_dirs.items():
            print(colored(f"\nProcessing {category} dependencies...", 'blue'))
            
            # Create temporary directory for this category
            with tempfile.TemporaryDirectory() as temp_dir:
                for target_dir in directories:
                    dir_path = os.path.join(root_dir, target_dir)
                    if not os.path.exists(dir_path):
                        continue
                        
                    # Walk through the target directory
                    for root, _, files in os.walk(dir_path):
                        rel_root = os.path.relpath(root, root_dir)
                        
                        if spec.match_file(rel_root):
                            continue
                            
                        for file in files:
                            if file.endswith('.py'):
                                rel_path = os.path.join(rel_root, file)
                                if not spec.match_file(rel_path):
                                    source_path = os.path.join(root, file)
                                    target_dir_path = os.path.join(temp_dir, os.path.relpath(root, root_dir))
                                    os.makedirs(target_dir_path, exist_ok=True)
                                    target_path = os.path.join(target_dir_path, file)
                                    print(colored(f"Including: {rel_path}", 'blue'))
                                    shutil.copy2(source_path, target_path)
                                    # Extract imports from this file
                                    category_imports[category].update(extract_imports_from_file(source_path))

                # Use pipreqs on the filtered directory for this category
                print(colored(f"\nRunning pipreqs for {category}...", 'blue'))
                pipreqs_path = "/Library/Frameworks/Python.framework/Versions/3.11/bin/pipreqs"
                requirements_temp = os.path.join(temp_dir, f'requirements_{category}.txt')
                command = f"{pipreqs_path} --force --savepath {requirements_temp} {temp_dir}"
                
                try:
                    subprocess.run(command, shell=True, check=True)
                    if os.path.exists(requirements_temp):
                        with open(requirements_temp, 'r') as f:
                            category_imports[category].update(line.split('==')[0] for line in f.read().splitlines())
                except subprocess.CalledProcessError:
                    print(colored(f"Warning: pipreqs failed for {category}", 'yellow'))

        # Package mappings for imports that don't match package names
        package_mappings = {
            'google': 'google-generativeai',
            'bs4': 'beautifulsoup4',
            'dotenv': 'python-dotenv',
            'tavily': 'tavily-python',
            'genai': 'google-generativeai',
            'wikipediaapi': 'Wikipedia-API',
            'dateutil': 'python-dateutil',
            'PIL': 'pillow',
            'jwt': 'PyJWT',
            'yaml': 'PyYAML'
        }

        # Core dependencies that should always be included
        core_dependencies = {
            'fastapi': '0.109.0',
            'uvicorn': '0.27.0',
            'sqlalchemy': '2.0.25',
            'alembic': '1.13.1',
            'python-jose[cryptography]': '3.3.0',
            'passlib[bcrypt]': '1.7.4',
            'python-multipart': '0.0.6',
            'python-dotenv': '1.0.0',
            'pydantic': '2.5.3',
            'pydantic-settings': '2.1.0',
            'psycopg2-binary': '2.9.9',
            'aiofiles': '23.2.1',
            'python-magic': '0.4.27'
        }

        # Development dependencies
        dev_dependencies = {
            'pytest': '7.4.4',
            'pytest-asyncio': '0.23.4'
        }

        # Filter and normalize packages
        final_packages = {
            'api': set(),
            'tools': set(),
            'utils': set(),
            'dev': set()
        }

        # Standard library modules to exclude
        stdlib_modules = set([
            'os', 'sys', 'json', 'datetime', 'time', 'uuid', 'shutil', 
            'tempfile', 'pathlib', 'mimetypes', 'ast', 're', 'typing',
            'traceback', 'subprocess', 'inspect', 'logging', 'importlib',
            'glob', 'urllib', 'dataclasses', 'collections', 'contextlib', 
            'copy', 'enum', 'functools', 'itertools', 'math', 'operator', 
            'random', 'string', 'threading', 'warnings', 'weakref', 'xml', 
            'html', 'http', 'argparse', 'base64', 'bisect', 'calendar', 
            'configparser', 'csv', 'curses', 'dbm', 'decimal', 'difflib', 
            'email', 'fileinput', 'fnmatch', 'fractions', 'getopt', 
            'getpass', 'gettext', 'gzip', 'hashlib', 'hmac', 'imaplib', 
            'imp', 'io', 'ipaddress', 'json', 'keyword', 'linecache', 
            'locale', 'mailbox', 'mmap', 'numbers', 'pickle', 'pipes', 
            'platform', 'plistlib', 'poplib', 'posixpath', 'pprint', 
            'profile', 'pty', 'pwd', 'py_compile', 'queue', 'quopri', 
            'selectors', 'shelve', 'signal', 'smtplib', 'socket', 
            'socketserver', 'sqlite3', 'ssl', 'stat', 'statistics', 
            'struct', 'sunau', 'symbol', 'symtable', 'sysconfig', 
            'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'textwrap', 
            'threading', 'token', 'tokenize', 'turtle', 'tty', 
            'unicodedata', 'unittest', 'urllib', 'uu', 'wave', 
            'webbrowser', 'winreg', 'wsgiref', 'xdrlib', 'xml', 
            'xmlrpc', 'zipfile', 'zipimport', 'zlib', 'secrets'
        ])

        # Process each category's imports
        for category, imports in category_imports.items():
            for imp in imports:
                if imp in package_mappings:
                    normalized_name = package_mappings[imp].lower()
                elif imp not in stdlib_modules and imp not in local_modules:
                    normalized_name = imp.lower()
                else:
                    continue
                final_packages[category].add(normalized_name)

        # Add core dependencies to API category
        for package, version in core_dependencies.items():
            final_packages['api'].add(f"{package}=={version}")

        # Add dev dependencies
        for package, version in dev_dependencies.items():
            final_packages['dev'].add(f"{package}=={version}")

        # Validate packages against PyPI
        print(colored("\nValidating packages on PyPI...", 'blue'))
        invalid_packages = set()
        for category in final_packages:
            for pkg in final_packages[category].copy():
                pkg_name = pkg.split('==')[0]
                if not validate_package_on_pypi(pkg_name):
                    print(colored(f"Warning: Package '{pkg_name}' not found on PyPI", 'yellow'))
                    invalid_packages.add(pkg)
                    final_packages[category].remove(pkg)

        if invalid_packages:
            print(colored("\nRemoved invalid packages:", 'yellow'))
            for pkg in sorted(invalid_packages):
                print(colored(f"- {pkg}", 'yellow'))

        # Write final requirements.txt
        requirements_path = os.path.join(root_dir, 'requirements.txt')
        with open(requirements_path, 'w') as f:
            f.write("# API Core Dependencies\n")
            f.write('\n'.join(sorted(final_packages['api'])))
            f.write("\n\n# Tools Dependencies\n")
            f.write('\n'.join(sorted(final_packages['tools'])))
            f.write("\n\n# Utils Dependencies\n")
            f.write('\n'.join(sorted(final_packages['utils'])))
            f.write("\n\n# Development Dependencies\n")
            f.write('\n'.join(sorted(final_packages['dev'])))

        print(colored("\nFound packages by category:", 'green'))
        for category in final_packages:
            print(colored(f"\n{category.upper()} Dependencies:", 'green'))
            for pkg in sorted(final_packages[category]):
                print(colored(f"- {pkg}", 'green'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))
        traceback.print_exc()

if __name__ == "__main__":
    generate_requirements()