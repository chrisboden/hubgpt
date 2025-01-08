from typing import Dict, Any, List, Optional
import requests
import base64
import os
from termcolor import colored
from utils.ui_utils import update_spinner_status
import re
from urllib.parse import urlparse

"""GitHub tool for interacting with repositories and performing various GitHub operations.

This tool provides a comprehensive interface to GitHub's API, allowing operations like:
- Repository management (search, details)
- File operations (read, write, update)
- Pull request handling
- Issue tracking
- Branch management
- Repository analysis and Q&A

Required environment variables:
- GITHUB_TOKEN: Personal access token for authentication
"""


class GitHubTools:
    """Class containing GitHub API operations."""
    
    @staticmethod
    def parse_github_url(url: str) -> Dict[str, str]:
        """Extract owner and repo from a GitHub URL.
        
        Args:
            url: GitHub repository URL (e.g., https://github.com/owner/repo)
            
        Returns:
            Dict containing owner and repo names
            
        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        try:
            # Handle both HTTPS and SSH URLs
            if url.startswith('git@github.com:'):
                path = url.split('git@github.com:')[1]
            else:
                parsed = urlparse(url)
                if parsed.netloc != 'github.com':
                    raise ValueError("Not a GitHub URL")
                path = parsed.path.lstrip('/')
            
            # Remove .git suffix if present
            path = re.sub(r'\.git$', '', path)
            
            # Split into owner and repo
            parts = path.split('/')
            if len(parts) != 2:
                raise ValueError("URL does not match expected format owner/repo")
                
            return {
                "owner": parts[0],
                "repo": parts[1]
            }
        except Exception as e:
            raise ValueError(f"Invalid GitHub URL: {str(e)}")

    @staticmethod
    def _get_headers(auth_required: bool = False) -> Dict[str, str]:
        """Get HTTP headers for GitHub API requests.
        
        Args:
            auth_required: If True, will raise error when token is missing
        
        Returns:
            Dict containing necessary headers
            
        Raises:
            ValueError: If auth_required is True and GITHUB_TOKEN is not set
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        token = os.getenv('GITHUB_TOKEN')
        if auth_required and not token:
            raise ValueError("This operation requires GITHUB_TOKEN environment variable")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def search_repositories(query: str, sort: str = "stars", max_results: int = 10) -> Dict[str, Any]:
        """Search GitHub repositories based on query parameters."""
        update_spinner_status("Searching GitHub repositories...")
        print(colored("Initiating repository search...", "cyan"))
        
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": min(max_results, 100)
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            update_spinner_status(f"Found {data['total_count']} repositories")
            print(colored(f"Found {data['total_count']} repositories", "green"))

            return {
                "total_count": data["total_count"],
                "incomplete_results": data["incomplete_results"],
                "items": data["items"][:max_results]
            }
        except requests.exceptions.RequestException as e:
            update_spinner_status(f"Error searching repositories: {str(e)}")
            print(colored(f"Error searching repositories: {str(e)}", "red"))
            raise

    @staticmethod
    def get_repo_details(owner: str, repo: str) -> Dict[str, Any]:
        """Get detailed information about a specific repository."""
        update_spinner_status(f"Fetching details for {owner}/{repo}...")
        print(colored(f"Fetching repository details...", "cyan"))
        
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            update_spinner_status("Repository details retrieved successfully")
            print(colored("Repository details retrieved", "green"))
            
            return response.json()
        except requests.exceptions.RequestException as e:
            update_spinner_status(f"Error fetching repository details: {str(e)}")
            print(colored(f"Error fetching repository details: {str(e)}", "red"))
            raise

    @staticmethod
    def get_file_content(owner: str, repo: str, path: str) -> Dict[str, Any]:
        """Get content of a file from a repository."""
        update_spinner_status(f"Fetching file: {path}")
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}/contents/{path}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                "content": base64.b64decode(data["content"]).decode('utf-8'),
                "sha": data["sha"],
                "size": data["size"],
                "name": data["name"],
                "path": data["path"]
            }
        except Exception as e:
            update_spinner_status(f"Error fetching file: {str(e)}")
            print(colored(f"Error fetching file: {str(e)}", "red"))
            raise

    @staticmethod
    def list_pull_requests(owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": state}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        def simplify_pr(pr: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "html_url": pr["html_url"],
                "user": {
                    "login": pr["user"]["login"],
                    "id": pr["user"]["id"]
                }
            }

        return [simplify_pr(pr) for pr in response.json()]

    @staticmethod
    def get_pull_request(owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Get details of a specific pull request."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}/pulls/{pull_number}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def list_repo_issues(owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List issues for a repository."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}/issues"
        params = {"state": state}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        def simplify_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "html_url": issue["html_url"],
                "user": {
                    "login": issue["user"]["login"],
                    "id": issue["user"]["id"]
                },
                "comments": issue["comments"]
            }

        return [simplify_issue(issue) for issue in response.json()]

    @staticmethod
    def create_issue_comment(owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Create a comment on an issue."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"

        data = {"body": body}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_directory_structure(owner: str, repo: str, path: str = "") -> Dict[str, Any]:
        """Get the directory structure of a repository."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers()
        url = f"{base_url}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        contents = response.json()

        if not isinstance(contents, list):
            contents = [contents]

        structure = {}
        for item in contents:
            structure[item["name"]] = {
                "type": item["type"],
                "size": item.get("size"),
                "path": item["path"]
            }
        return structure

    @staticmethod
    def check_github_diff(base: str, head: str) -> Dict[str, Any]:
        GitHubTools.configure() 
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"https://api.github.com/repos/{GitHubTools._owner}/{GitHubTools._repo}/compare/{base}...{head}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return {
            "files_changed": [f["filename"] for f in data["files"]],
            "total_changes": {
                "additions": sum(f.get("additions", 0) for f in data["files"]),
                "deletions": sum(f.get("deletions", 0) for f in data["files"]),
                "changes": sum(f.get("changes", 0) for f in data["files"])
            },
            "commits": [
                {
                    "sha": c["sha"],
                    "message": c["commit"]["message"],
                    "author": c["commit"]["author"]["name"]
                }
                for c in data["commits"]
            ]
        }

    @staticmethod
    def update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str) -> Dict[str, Any]:
        """Update or create a file in the repository."""
        update_spinner_status(f"Updating file: {path}")
        print(colored(f"Updating file: {path}", "cyan"))
        
        headers = GitHubTools._get_headers(auth_required=True)
        base_url = "https://api.github.com"
        url = f"{base_url}/repos/{owner}/{repo}/contents/{path}"

        try:
            # Handle binary content properly
            try:
                content_bytes = content.encode('utf-8')
            except AttributeError:
                content_bytes = content
                
            # Get current file SHA if it exists
            try:
                update_spinner_status("Checking for existing file...")
                current_file = GitHubTools.get_file_content(owner, repo, path)
                sha = current_file["sha"]
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise
                sha = None
                update_spinner_status("Creating new file...")

            data = {
                "message": message,
                "content": base64.b64encode(content_bytes).decode(),
                "branch": branch
            }
            if sha:
                data["sha"] = sha

            update_spinner_status("Committing changes...")
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            
            update_spinner_status("File updated successfully")
            print(colored("File updated successfully", "green"))
            
            return response.json()
            
        except Exception as e:
            update_spinner_status(f"Error updating file: {str(e)}")
            print(colored(f"Error updating file: {str(e)}", "red"))
            raise

    @staticmethod
    def create_branch(branch_name: str) -> Dict[str, Any]:
        GitHubTools.configure() 
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        
        # Get default branch's SHA
        url = f"{base_url}/repos/{GitHubTools._owner}/{GitHubTools._repo}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        default_branch = response.json()["default_branch"]
        
        # Get SHA of default branch
        ref_url = f"{base_url}/repos/{GitHubTools._owner}/{GitHubTools._repo}/git/ref/heads/{default_branch}"
        ref_response = requests.get(ref_url, headers=headers)
        ref_response.raise_for_status()
        base_sha = ref_response.json()["object"]["sha"]

        # Create new branch
        create_url = f"{base_url}/repos/{GitHubTools._owner}/{GitHubTools._repo}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }

        response = requests.post(create_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def create_pull_request(title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        GitHubTools.configure() 
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"{base_url}/repos/{GitHubTools._owner}/{GitHubTools._repo}/pulls"

        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_repo_markdown(url: str) -> str:
        """Get markdown representation of a repository from UIthub.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            str: Markdown representation of the repository
            
        Raises:
            ValueError: If URL is invalid or repository not found
        """
        try:
            # Convert github.com to uithub.com
            uithub_url = url.replace("github.com", "uithub.com")
            
            update_spinner_status(f"Fetching repository markdown from UIthub...")
            print(colored(f"Fetching repository markdown from {uithub_url}", "cyan"))
            
            response = requests.get(uithub_url)
            response.raise_for_status()
            
            update_spinner_status("Repository markdown retrieved successfully")
            return response.text
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching repository markdown: {str(e)}"
            update_spinner_status(error_msg)
            print(colored(error_msg, "red"))
            raise ValueError(error_msg)

    @staticmethod
    def ask_about_repo(url: str, question: str, llm_client) -> Dict[str, str]:
        """Ask questions about a repository using LLM analysis.
        
        Args:
            url: GitHub repository URL
            question: Question about the repository
            llm_client: LLM client for analysis
            
        Returns:
            Dict containing question and answer
        """
        try:
            update_spinner_status("Analyzing repository...")
            print(colored("Starting repository analysis...", "cyan"))
            
            # Get repository markdown
            repo_markdown = GitHubTools.get_repo_markdown(url)
            
            # Prepare messages for LLM
            messages = [
                {
                    "role": "system",
                    "content": """You are REPO-SCHOLAR, an expert at analyzing and explaining codebases with exceptional attention to detail. Your role is to provide clear, comprehensive answers about repository structure, functionality, and implementation details.

CORE DIRECTIVES:
- Provide detailed technical explanations while maintaining clarity
- Focus on architecture, patterns, and key components
- Explain how different parts of the codebase interact
- Include relevant code examples when helpful
- Maintain technical accuracy while being accessible
- Consider both high-level overview and specific implementation details

FORMAT GUIDELINES:
1. Start with a concise summary
2. Break down complex topics into digestible sections
3. Use examples to illustrate key concepts
4. Reference specific files/components when relevant
5. Explain architectural decisions and their implications

Remember: Your goal is to help users understand both the what and why of the codebase."""
                },
                {
                    "role": "user",
                    "content": f"Repository content:\n\n{repo_markdown}\n\nQuestion: {question}"
                }
            ]
            
            update_spinner_status("Generating response...")
            response = llm_client.chat.completions.create(
                model="google/gemini-flash-1.5-8b",
                messages=messages,
                max_tokens=3000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            update_spinner_status("Analysis complete")
            print(colored("Repository analysis complete", "green"))
            
            return {
                "question": question,
                "answer": answer
            }
            
        except Exception as e:
            error_msg = f"Error analyzing repository: {str(e)}"
            update_spinner_status(error_msg)
            print(colored(error_msg, "red"))
            raise ValueError(error_msg)

    @staticmethod
    def check_if_starred(owner: str, repo: str) -> bool:
        """Check if the authenticated user has starred a repository."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"{base_url}/user/starred/{owner}/{repo}"
        
        try:
            response = requests.get(url, headers=headers)
            # GitHub returns 204 if starred, 404 if not starred
            return response.status_code == 204
        except Exception as e:
            update_spinner_status(f"Error checking star status: {str(e)}")
            print(colored(f"Error checking star status: {str(e)}", "red"))
            raise

    @staticmethod
    def list_starred_repos() -> List[Dict[str, Any]]:
        """List all repositories starred by the authenticated user."""
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"{base_url}/user/starred"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            def simplify_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "html_url": repo["html_url"],
                    "stargazers_count": repo["stargazers_count"],
                    "owner": {
                        "login": repo["owner"]["login"],
                        "id": repo["owner"]["id"]
                    }
                }
            
            return [simplify_repo(repo) for repo in response.json()]
        except Exception as e:
            update_spinner_status(f"Error fetching starred repos: {str(e)}")
            print(colored(f"Error fetching starred repos: {str(e)}", "red"))
            raise

    @staticmethod
    def create_gist(description: str, files: Dict[str, Dict[str, str]], public: bool = True) -> Dict[str, Any]:
        """Create a GitHub Gist.
        
        Args:
            description: A description of the gist
            files: Dict of filename to file content. Format: {"file.txt": {"content": "file content"}}
            public: Whether the gist should be public (default: True)
            
        Returns:
            Dict containing the created gist information
        """
        base_url = "https://api.github.com"
        headers = GitHubTools._get_headers(auth_required=True)
        url = f"{base_url}/gists"
        
        data = {
            "description": description,
            "public": public,
            "files": files
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            update_spinner_status(f"Error creating gist: {str(e)}")
            print(colored(f"Error creating gist: {str(e)}", "red"))
            raise

def execute(operation: str, params: Dict[str, Any], llm_client=None) -> Dict[str, Any]:
    """Execute GitHub operations using the GitHubTools class."""
    try:
        update_spinner_status(f"Initializing GitHub operation: {operation}")
        print(colored(f"Executing GitHub operation: {operation}", "cyan"))
        
        # Extract owner/repo from URL if provided
        if "url" in params and operation != "ask":  # Don't extract for ask operation
            try:
                repo_info = GitHubTools.parse_github_url(params["url"])
                params["owner"] = repo_info["owner"]
                params["repo"] = repo_info["repo"]
                del params["url"]  # Remove URL from params
            except ValueError as e:
                return {"error": f"Invalid GitHub URL: {str(e)}"}
        
        # Map operations to GitHubTools methods
        operations = {
            "search_repositories": GitHubTools.search_repositories,
            "get_repo_details": GitHubTools.get_repo_details,
            "get_file_content": GitHubTools.get_file_content,
            "list_pull_requests": GitHubTools.list_pull_requests,
            "get_pull_request": GitHubTools.get_pull_request,
            "list_repo_issues": GitHubTools.list_repo_issues,
            "create_issue_comment": GitHubTools.create_issue_comment,
            "get_directory_structure": GitHubTools.get_directory_structure,
            "check_github_diff": GitHubTools.check_github_diff,
            "update_file": GitHubTools.update_file,
            "create_branch": GitHubTools.create_branch,
            "create_pull_request": GitHubTools.create_pull_request,
            "ask": lambda url, question: GitHubTools.ask_about_repo(url, question, llm_client),
            "check_if_starred": GitHubTools.check_if_starred,
            "list_starred_repos": GitHubTools.list_starred_repos,
            "create_gist": GitHubTools.create_gist
        }
        
        if operation not in operations:
            error_msg = f"Unknown operation: {operation}"
            update_spinner_status(error_msg)
            print(colored(error_msg, "red"))
            return {"error": error_msg}
            
        # Execute the operation with provided parameters
        update_spinner_status(f"Executing {operation}...")
        result = operations[operation](**params)
        
        update_spinner_status("Operation completed successfully")
        print(colored("GitHub operation completed successfully", "green"))
        
        return {"result": result}
        
    except Exception as e:
        error_msg = f"Error executing GitHub operation: {str(e)}"
        update_spinner_status(error_msg)
        print(colored(error_msg, "red"))
        return {"error": error_msg}

# Tool metadata for HubGPT framework
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_github",
        "description": "Interact with GitHub repositories to perform various operations like searching repos, getting file contents, managing PRs and issues, etc. Repository information can be provided via URL or owner/repo parameters. Can also analyze repositories and answer questions about them.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The GitHub operation to perform",
                    "enum": [
                        "search_repositories",
                        "get_repo_details",
                        "get_file_content",
                        "list_pull_requests",
                        "get_pull_request",
                        "list_repo_issues",
                        "create_issue_comment",
                        "get_directory_structure",
                        "check_github_diff",
                        "update_file",
                        "create_branch",
                        "create_pull_request",
                        "ask",
                        "check_if_starred",
                        "list_starred_repos",
                        "create_gist"
                    ]
                },
                "params": {
                    "type": "object",
                    "description": "Parameters specific to the chosen operation. You can provide either 'url' OR 'owner'/'repo' parameters:\n\n" +
                        "URL format: params.url = 'https://github.com/owner/repo'\n\n" +
                        "Required parameters by operation:\n" +
                        "- search_repositories: query\n" +
                        "- get_repo_details: url OR (owner, repo)\n" +
                        "- get_file_content: (url OR (owner, repo)) AND path\n" +
                        "- list_pull_requests: url OR (owner, repo)\n" +
                        "- get_pull_request: (url OR (owner, repo)) AND pull_number\n" +
                        "- list_repo_issues: url OR (owner, repo)\n" +
                        "- create_issue_comment: (url OR (owner, repo)) AND issue_number, body\n" +
                        "- get_directory_structure: url OR (owner, repo)\n" +
                        "- check_github_diff: (url OR (owner, repo)) AND base, head\n" +
                        "- update_file: (url OR (owner, repo)) AND path, content, message, branch\n" +
                        "- create_branch: (url OR (owner, repo)) AND branch_name\n" +
                        "- create_pull_request: (url OR (owner, repo)) AND title, body, head, base\n" +
                        "- ask: url AND question\n" +
                        "- check_if_starred: (owner, repo)\n" +
                        "- list_starred_repos: no parameters required\n" +
                        "- create_gist: description, files, public (optional)",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "GitHub repository URL. Example: 'https://github.com/microsoft/vscode'"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query string for repositories. Example: 'language:python stars:>1000'"
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort criteria for repository search",
                            "enum": ["stars", "forks", "help-wanted-issues", "updated"],
                            "default": "stars"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        },
                        "owner": {
                            "type": "string",
                            "description": "Repository owner/organization name. Example: 'microsoft'"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name. Example: 'vscode'"
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the file within the repository. Example: 'docs/README.md'"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file. For binary files, this should be base64 encoded."
                        },
                        "message": {
                            "type": "string",
                            "description": "Commit message for file updates. Example: 'Update README.md'"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name for file operations or PR creation. Example: 'feature/new-docs'"
                        },
                        "state": {
                            "type": "string",
                            "description": "State of PRs/issues to return",
                            "enum": ["open", "closed", "all"],
                            "default": "open"
                        },
                        "pull_number": {
                            "type": "integer",
                            "description": "Pull request number to fetch details for. Example: 123"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the pull request. Example: 'Add new feature'"
                        },
                        "body": {
                            "type": "string",
                            "description": "Description/body text for pull request or issue comment. Supports markdown."
                        },
                        "head": {
                            "type": "string",
                            "description": "Name of the branch containing changes. Example: 'feature/new-docs'"
                        },
                        "base": {
                            "type": "string",
                            "description": "Name of the branch to merge into. Example: 'main'"
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number for commenting. Example: 456"
                        },
                        "base": {
                            "type": "string",
                            "description": "Base reference (commit SHA, branch, or tag) for comparison. Example: 'main'"
                        },
                        "head": {
                            "type": "string",
                            "description": "Head reference to compare against base. Example: 'feature/new-docs'"
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Name for the new branch to create. Example: 'feature/new-docs'"
                        },
                        "question": {
                            "type": "string",
                            "description": "Question to ask about the repository. Example: 'How does the authentication system work?'"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for the gist"
                        },
                        "files": {
                            "type": "object",
                            "description": "Dictionary of filename to file content. Example: {'example.txt': {'content': 'Hello World'}}"
                        },
                        "public": {
                            "type": "boolean",
                            "description": "Whether the gist should be public",
                            "default": True
                        }
                    }
                }
            },
            "required": ["operation", "params"]
        }
    }
}