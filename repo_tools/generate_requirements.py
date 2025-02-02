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

        # Get list of our own Python modules to exclude - scan both root and api directory
        local_modules = set()
        
        # Scan root directory
        for f in os.listdir(root_dir):
            if os.path.isfile(os.path.join(root_dir, f)) and f.endswith('.py'):
                local_modules.add(os.path.splitext(f)[0])
            elif os.path.isdir(os.path.join(root_dir, f)):
                if os.path.exists(os.path.join(root_dir, f, '__init__.py')):
                    local_modules.add(f)
                # Also add the directory name with hyphen variant
                local_modules.add(f.replace('_', '-'))
        
        # Scan api directory specifically
        api_dir = os.path.join(root_dir, 'api')
        if os.path.exists(api_dir):
            for f in os.listdir(api_dir):
                if os.path.isfile(os.path.join(api_dir, f)) and f.endswith('.py'):
                    local_modules.add(os.path.splitext(f)[0])
                elif os.path.isdir(os.path.join(api_dir, f)):
                    if os.path.exists(os.path.join(api_dir, f, '__init__.py')):
                        local_modules.add(f)
                    # Also add the directory name with hyphen variant
                    local_modules.add(f.replace('_', '-'))
        
        # Add known internal packages
        internal_packages = {
            'api-utils', 'routers', 'services', 'tool-utils', 'models',
            'api_utils', 'tool_utils', 'log_utils', 'log-utils'
        }
        local_modules.update(internal_packages)
        
        print(colored(f"Excluding local modules: {', '.join(sorted(local_modules))}", 'blue'))

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
                'tavily': 'tavily-python',
                'genai': 'google-generativeai',
                'wikipediaapi': 'Wikipedia-API',
                'dateutil': 'python-dateutil',  # Map dateutil to python-dateutil
                'pil': 'Pillow',  # Map PIL/pil imports to Pillow package
                'PIL': 'Pillow',  # Also map uppercase PIL to Pillow
                'fastapi': 'uvicorn',  # Add uvicorn when FastAPI is used
                'starlette': 'uvicorn',  # Add uvicorn when Starlette is used
                # Add more mappings as needed
            }
            
            # Normalize package names (replace - with _)
            normalized_packages = {pkg.replace('-', '_').lower() for pkg in packages}
            
            # Add mapped package names and filter out local modules
            for imp in all_imports:
                imp_lower = imp.lower()
                if imp_lower in package_mappings:
                    normalized_name = package_mappings[imp_lower].replace('-', '_').lower()
                    normalized_packages.add(normalized_name)
                elif imp_lower not in local_modules:  # Only add if not a local module
                    normalized_packages.add(imp_lower)
            
            # Filter out standard library modules, built-in packages, and local modules
            stdlib_modules = set([
                'os', 'sys', 'json', 'datetime', 'time', 'uuid', 'shutil', 
                'tempfile', 'pathlib', 'mimetypes', 'ast', 're', 'typing',
                'traceback', 'subprocess', 'inspect', 'logging', 'importlib',
                'glob', 'urllib', 'dataclasses',  # dataclasses is built-in for Python 3.7+
                'collections', 'contextlib', 'copy', 'enum', 'functools',
                'itertools', 'math', 'operator', 'random', 'string', 'threading',
                'warnings', 'weakref', 'xml', 'html', 'http', 'argparse',
                'base64', 'bisect', 'calendar', 'configparser', 'csv',
                'curses', 'dbm', 'decimal', 'difflib', 'email', 'fileinput',
                'fnmatch', 'fractions', 'getopt', 'getpass', 'gettext',
                'gzip', 'hashlib', 'hmac', 'imaplib', 'imp', 'io',
                'ipaddress', 'json', 'keyword', 'linecache', 'locale',
                'mailbox', 'mmap', 'numbers', 'pickle', 'pipes', 'platform',
                'plistlib', 'poplib', 'posixpath', 'pprint', 'profile',
                'pty', 'pwd', 'py_compile', 'queue', 'quopri', 'selectors',
                'shelve', 'signal', 'smtplib', 'socket', 'socketserver',
                'sqlite3', 'ssl', 'stat', 'statistics', 'struct', 'sunau',
                'symbol', 'symtable', 'sysconfig', 'tabnanny', 'tarfile',
                'telnetlib', 'tempfile', 'textwrap', 'threading', 'token',
                'tokenize', 'turtle', 'tty', 'unicodedata', 'unittest',
                'urllib', 'uu', 'wave', 'webbrowser', 'winreg', 'wsgiref',
                'xdrlib', 'xml', 'xmlrpc', 'zipfile', 'zipimport', 'zlib'
            ])
            normalized_packages = {
                pkg for pkg in normalized_packages 
                if pkg not in stdlib_modules and 
                pkg.replace('-', '_') not in local_modules and 
                pkg.replace('_', '-') not in local_modules
            }
            
            # Remove any duplicate package names (considering normalized names)
            final_packages = set()
            for pkg in normalized_packages:
                # Convert back to preferred format (with hyphens)
                preferred_name = pkg.replace('_', '-')
                final_packages.add(preferred_name)
            
            # Remove duplicates where one is a suffix of another
            final_packages = {
                pkg for pkg in final_packages 
                if not any(alt for alt in final_packages 
                          if (alt != pkg and 
                              (alt.endswith(pkg.replace('-', '_')) or 
                               alt.endswith(pkg.replace('_', '-')))))
            }
            
            # Validate packages against PyPI
            print(colored("\nValidating packages on PyPI...", 'blue'))
            invalid_packages = set()
            for pkg in final_packages:
                if not validate_package_on_pypi(pkg):
                    print(colored(f"Warning: Package '{pkg}' not found on PyPI", 'yellow'))
                    invalid_packages.add(pkg)
            
            # Remove invalid packages
            final_packages = final_packages - invalid_packages
            
            if invalid_packages:
                print(colored("\nRemoved invalid packages:", 'yellow'))
                for pkg in sorted(invalid_packages):
                    print(colored(f"- {pkg}", 'yellow'))

            # Write final requirements.txt
            requirements_path = os.path.join(root_dir, 'requirements.txt')
            with open(requirements_path, 'w') as f:
                f.write('\n'.join(sorted(final_packages)))
            
            print(colored("\nFound packages:", 'green'))
            for pkg in sorted(final_packages):
                print(colored(f"- {pkg}", 'green'))
                
    except Exception as e:
        print(colored(f"Error generating requirements: {str(e)}", 'red'))

if __name__ == "__main__":
    generate_requirements()