# tools/linkedin_research.py
import os
import json
import requests
import time
from datetime import datetime
import duckdb
from termcolor import colored
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv
from utils.search_utils import perform_search

# Load environment variables
load_dotenv()

class LinkedInResearchTool:
    def __init__(self, llm_client):
        # Retrieve API key from environment variable
        self.api_key = os.getenv('RAPIDAPI_KEY')
        
        # Validate API key
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable is not set")
        
        self.llm_client = llm_client
        self.api_endpoints = [
            "https://linkedin-data-api.p.rapidapi.com",
            "https://linkedin-api8.p.rapidapi.com"
        ]
        self.current_api_index = 0
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_endpoints[0].replace('https://', '')
        }
        
        # Ensure data directory exists
        data_dir = 'data'
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
                print(colored(f"✓ Created data directory at {data_dir}", "green"))
            except Exception as e:
                print(colored(f"✗ Error creating data directory: {str(e)}", "red"))
                raise
        
        db_path = os.path.join(data_dir, 'linkedin.db')
        try:
            self.db = duckdb.connect(db_path)
            print(colored(f"✓ Connected to database at {db_path}", "green"))
            self._init_db()
        except Exception as e:
            print(colored(f"✗ Error connecting to database: {str(e)}", "red"))
            raise

    def _init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS person (
                    linkedin_id VARCHAR PRIMARY KEY,
                    profile_raw JSON,
                    profile_summary JSON,
                    posts_raw JSON,
                    posts_summary JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS company (
                    linkedin_id VARCHAR PRIMARY KEY,
                    profile_raw JSON,
                    profile_summary JSON,
                    posts_raw JSON,
                    posts_summary JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print(colored("✓ Database initialized successfully", "green"))
        except Exception as e:
            print(colored(f"✗ Database initialization error: {str(e)}", "red"))
            raise

    def _update_api_endpoint(self):
        """Switch to alternate API endpoint and update headers"""
        self.current_api_index = (self.current_api_index + 1) % len(self.api_endpoints)
        new_host = self.api_endpoints[self.current_api_index].replace('https://', '')
        self.headers["x-rapidapi-host"] = new_host
        print(colored(f"Switching to alternate API endpoint: {self.api_endpoints[self.current_api_index]}", "yellow"))

    def _make_api_request(self, endpoint_path: str, params: dict) -> Dict:
        """Make API request with automatic fallback on rate limit"""
        for attempt in range(len(self.api_endpoints)):
            current_base = self.api_endpoints[self.current_api_index]
            full_url = f"{current_base}/{endpoint_path}"
            
            try:
                print(colored(f"Making API request to: {full_url}", "cyan"))
                print(f"Request params:\n{params}")
                
                response = requests.get(
                    full_url,
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit exceeded
                    print(colored(f"Rate limit exceeded on {current_base}", "yellow"))
                    self._update_api_endpoint()
                    continue
                else:
                    raise Exception(f"API request failed with status {response.status_code}")
                    
            except Exception as e:
                print(colored(f"Error with endpoint {current_base}: {str(e)}", "red"))
                if attempt < len(self.api_endpoints) - 1:
                    self._update_api_endpoint()
                else:
                    raise Exception(f"All API endpoints failed. Last error: {str(e)}")

    

    def _determine_entity_type(self, brief: str) -> str:
        """Determine if the brief is about a person or company"""
        try:
            messages = [
                {"role": "system", "content": "You are an expert at analyzing text to determine whether it's referring to a person or a company. Return a JSON object with the entity_type field set to either 'person' or 'company'."},
                {"role": "user", "content": f"Is this brief about a person or a company? Brief: {brief}"}
            ]
            
            print(colored(f"Calling LLM to determine entity type\n\n: {brief}", "cyan"))
            response = self.llm_client.chat.completions.create(
                model="openai/gpt-4o",
                messages=messages,
                max_tokens=50,
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            print(colored(f"Raw LLM response: {response}", "cyan"))
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("Invalid response from LLM")
                
            content = response.choices[0].message.content
            print(colored(f"Response content: {content}", "cyan"))
            
            if not content:
                raise ValueError("Empty content from LLM")
                
            result = json.loads(content)
            print(colored(f"Parsed JSON: {result}", "cyan"))
            
            entity_type = result.get('entity_type', '').lower()
            
            if entity_type not in ['person', 'company']:
                raise ValueError(f"Invalid entity type determined: {entity_type}")
                
            print(colored(f"✓ Determined entity type: {entity_type}", "green"))
            return entity_type
            
        except Exception as e:
            print(colored(f"✗ Error determining entity type: {str(e)}", "red"))
            print(colored("Full error details:", "red"))
            import traceback
            print(colored(traceback.format_exc(), "red"))
            raise

    def _find_canonical_linkedin_profile(self, brief: str, entity_type: str) -> str:
        """Find canonical LinkedIn profile using web search and reranking"""
        try:
            print(colored("Starting LinkedIn profile search...", "cyan"))
            
            search_results = perform_search(
                objective=f"""The user is looking for a {entity_type}'s LinkedIn profile. 
                Brief: {brief}
                Your task is to construct a search query that will find their LinkedIn profile page.
                Limit search to site:linkedin.com/in/ for people or site:linkedin.com/company/ for companies.
                Focus on finding the main profile page, not news or mentions.""",
                llm_client=self.llm_client
            )
            
            if not search_results:
                raise ValueError("No LinkedIn profiles found in search results")

            formatted_results = "\n".join(
                f"Title: {res['title']}\nURL: {res['url']}\nDescription: {res['description']}\n"
                for res in search_results
            ).strip()

            print(f"These are the search results for the top urls for the search term:\n{formatted_results}")

            messages = [
                {"role": "system", "content": f"""You are an expert at identifying correct LinkedIn profiles.
                
                For a PERSON, look for:
                - Official LinkedIn URL format (/in/)
                - Name matches or closely matches
                - Current role/company aligns with brief
                - Profile completeness indicators
                - Verification signals
                
                For a COMPANY, look for:
                - Official LinkedIn company URL format (/company/)
                - Exact company name matches
                - Industry and description alignment
                - Official company page indicators
                - Verified company signals
                
                Analyze the search results and identify the most likely canonical profile.
                Return a JSON object with the selected profile URL and confidence score."""},
                {"role": "user", "content": f"""Find the correct LinkedIn profile for this brief:
                
                Brief: {brief}
                Entity Type: {entity_type}
                
                Search Results:
                {formatted_results}
                
                Return JSON with:
                {{
                    "linkedin_url": "selected profile URL",
                    "linkedin_username": "username extracted from URL",
                    "confidence": "HIGH/MEDIUM/LOW",
                    "reasoning": "explanation of selection"
                }}"""}
            ]

            response = self.llm_client.chat.completions.create(
                model="openai/gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            
            if result['confidence'] != 'HIGH':
                raise ValueError(f"Could not determine canonical profile with high confidence. {result['reasoning']}")

            print(colored(f"✓ Found canonical profile: {result['linkedin_url']}", "green"))
            return result['linkedin_username']

        except Exception as e:
            print(colored(f"✗ Error finding canonical profile: {str(e)}", "red"))
            raise

    def _get_profile_data(self, linkedin_id: str, entity_type: str) -> Dict:
        """Get full profile data for person or company"""
        try:
            endpoint_path = 'get-company-details' if entity_type == 'company' else ''
            params = {"username": linkedin_id}
            return self._make_api_request(endpoint_path, params)
        except Exception as e:
            print(colored(f"✗ Error getting profile data: {str(e)}", "red"))
            raise

    def _get_posts(self, linkedin_id: str, entity_type: str) -> List[Dict]:
        """Get posts for person or company"""
        try:
            endpoint_path = 'get-company-posts' if entity_type == 'company' else 'get-profile-posts'
            params = {"username": linkedin_id, "start": "0"}
            return self._make_api_request(endpoint_path, params)
        except Exception as e:
            print(colored(f"✗ Error getting posts: {str(e)}", "red"))
            raise

    def _generate_profile_summary(self, profile_data: Dict, entity_type: str) -> Dict:
        """Generate normalized profile summary using LLM"""
        try:
            print(colored("Preparing profile data for summary...", "cyan"))
            
            # Ensure we have valid profile data
            if not profile_data:
                return {
                    "status": "no_data",
                    "message": "No profile data available",
                    "timestamp": datetime.now().isoformat()
                }
                
            print(colored(f"Profile data to summarize: {json.dumps(profile_data, indent=2)}", "cyan"))
            
            messages = [
                {"role": "system", "content": f"""You are an expert at analyzing LinkedIn profiles. 
                Create a normalized summary of this {entity_type}'s profile.
                
                For a company profile, focus on:
                - Company name and type
                - Industry and specialties
                - Company size and location
                - Description and mission
                - Key offerings and expertise
                
                For a person profile, focus on:
                - Creating a short bio. Use the Pareto principle to capture the person's professional background in a holistic way. Come up with a strong topic sentence that describes who this person is and what they do based on the most substantive part of their career. For example, 'Senior Marketing Executive'.\n</scratchpad>\n \nWhen writing the biography, make sure to:\n\n- Highlight their key career achievements, focusing on measurable outcomes where applicable. Mention significant projects or contributions they have made without exaggerating. Give special attention to roles they've held with major brands.\n\n- Describe their main technical and professional specializations. Include any notable expertise that distinguishes them in their field. \n\n- Summarize the progression of their career, including the depth of experience they have in each role. Note the types of roles they have held and the key responsibilities those roles entailed.\n \n - List the most prominent companies they have worked for, especially well-known firms in their industry. Include any startups or significant entrepreneurial ventures they have been involved with.\n\n- Since we are based in Australia and value international experience, make sure to mention any countries or notable cities where they have worked in order to highlight the international scope of their professional background.\n\n- Identify the main industries and vertical sectors they have experience in, particularly those most relevant to their current role and likely future positions.\n\nRemember, the biography should be straightforward and objective, avoiding promotional language or unnecessary fluff and cliches. Aim to provide a clear, fact-based overview of the person's professional capabilities and experience. Make the bio information-dense.\n\nWrite the biography as a 150 word narrative using full paragraphs. Given that this bio will be used in an email intro, you must refer to the person by their first name when talking about their experience. Do not use bullet points or section headings.
                - Current role and company
                - Professional experience
                - Skills and expertise
                - Education and certifications
                - Notable achievements
                
                Return a JSON object with relevant fields based on the profile type."""},
                {"role": "user", "content": f"Here is the data to summarise: {json.dumps(profile_data)}"}
            ]
            
            print(colored(f"Calling LLM for profile summary with:\n\n{messages}"),"cyan")
            response = self.llm_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("Invalid response from LLM")

            content = response.choices[0].message.content
            print(colored(f"LLM response for profile summary with:\n\n{content}"),"cyan")  
            if not content:
                raise ValueError("Empty content from LLM")
                
            summary = json.loads(content)
            print(colored("Successfully generated profile summary", "green"))
            return summary
            
        except Exception as e:
            print(colored(f"✗ Error generating profile summary: {str(e)}", "red"))
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }


    def _generate_posts_summary(self, posts_data: List[Dict], entity_type: str) -> Dict:
        """Generate normalized posts summary using LLM"""
        try:
            messages = [
                {"role": "system", "content": f"""You are an expert at analyzing LinkedIn posting activity. 
                Create a summary of this {entity_type}'s posting activity.
                
                For a company profile, you create an information-dense digest of their recent postings, ensuring to preserve key announcements, etc. This digest should provide an at-a-glance summary of the company's activities without having to read each and every post in full. Make sure to mention if the posts are not recent.
                
                For a person's profile, you create an information-dense digest of their recent postings, ensuring to preserve key achievements, thought-pieces, blog-style posts, annoucements, etc. This digest should provide an at-a-glance summary of the person's posting activities without having to read each and every post in full. Make sure to mention if the posts are not recent.
                
                Return a JSON object with relevant fields based on the profile type."""},
                {"role": "user", "content": f"Here are the posts to summarise: {json.dumps(posts_data)}"}
            ]
            print(f"Calling LLM for posts summary with:\n\n{messages}")
            response = self.llm_client.chat.completions.create(
                model="google/gemini-flash-1.5-8b",
                messages=messages,
                max_tokens=4000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            print(f"Response from LLM for posts summary with:\n\n{response}")
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(colored(f"✗ Error generating posts summary: {str(e)}", "red"))
            raise

    def _save_to_db(self, data: Dict, entity_type: str):
        """Save data to appropriate database table"""
        try:
            table = entity_type
            current_timestamp = datetime.now().isoformat()
            
            self.db.execute(f"""
                INSERT INTO {table} (
                    linkedin_id,
                    profile_raw,
                    profile_summary,
                    posts_raw,
                    posts_summary,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (linkedin_id) DO UPDATE SET
                    profile_raw = EXCLUDED.profile_raw,
                    profile_summary = EXCLUDED.profile_summary,
                    posts_raw = EXCLUDED.posts_raw,
                    posts_summary = EXCLUDED.posts_summary,
                    created_at = EXCLUDED.created_at
            """, [
                data['linkedin_id'],
                json.dumps(data['profile_raw']),
                json.dumps(data['profile_summary']) if data['profile_summary'] else None,
                json.dumps(data['posts_raw']),
                json.dumps(data['posts_summary']) if data['posts_summary'] else None,
                current_timestamp
            ])
            print(colored(f"✓ Data saved to {table} table", "green"))
        except Exception as e:
            print(colored(f"✗ Database save error: {str(e)}", "red"))
            raise


    def research(self, brief: str) -> str:
        """Main research flow"""
        print(colored("Starting LinkedIn research execution...", "cyan"))
        try:
            # Stage 1: Determine entity type and find canonical match
            print(colored("Stage 1: Finding canonical entity...", "cyan"))
            entity_type = self._determine_entity_type(brief)
            linkedin_id = self._find_canonical_linkedin_profile(brief, entity_type)
            
            if not linkedin_id:
                return "No matching LinkedIn profile found. Please provide more specific information."
            
            # Stage 2: Get profile and posts data
            print(colored("Stage 2: Getting profile and posts data...", "cyan"))
            profile_data = self._get_profile_data(linkedin_id, entity_type)
            posts_data = self._get_posts(linkedin_id, entity_type)
            
            # Save raw data first
            print(colored("Stage 3: Saving raw data...", "cyan"))
            initial_data = {
                'linkedin_id': linkedin_id,
                'profile_raw': profile_data,
                'profile_summary': None,  # Will update later
                'posts_raw': posts_data.get('data', []),  # Handle empty posts
                'posts_summary': None  # Will update later
            }
            self._save_to_db(initial_data, entity_type)
            
            # Stage 4: Generate summaries
            print(colored("Stage 4: Generating summaries...", "cyan"))
            
            # Generate profile summary
            try:
                profile_summary = self._generate_profile_summary(profile_data.get('data', {}), entity_type)
            except Exception as e:
                print(colored(f"Warning: Could not generate profile summary: {str(e)}", "yellow"))
                profile_summary = {"error": "Could not generate profile summary"}
            
            # Generate posts summary (only if there are posts)
            posts = posts_data.get('data', [])
            if posts:
                try:
                    posts_summary = self._generate_posts_summary(posts, entity_type)
                except Exception as e:
                    print(colored(f"Warning: Could not generate posts summary: {str(e)}", "yellow"))
                    posts_summary = {"error": "Could not generate posts summary"}
            else:
                print(colored("No posts found for this profile", "yellow"))
                posts_summary = {"note": "No posts available"}
            
            # Update database with summaries
            update_data = {
                'linkedin_id': linkedin_id,
                'profile_raw': profile_data,
                'profile_summary': profile_summary,
                'posts_raw': posts_data.get('data', []),
                'posts_summary': posts_summary
            }
            self._save_to_db(update_data, entity_type)
            
            # Stage 5: Generate final summary
            print(colored("Stage 5: Generating final summary...", "cyan"))
            messages = [
                {"role": "system", "content": """You are an expert at synthesizing LinkedIn information into clear, insightful summaries.
                If there are no posts available, focus on the profile information only."""},
                {"role": "user", "content": f"""Please create a comprehensive summary based on this data:
                
                Profile Summary: {json.dumps(profile_summary)}
                
                Posts Summary: {json.dumps(posts_summary)}
                
                Note: If the posts summary indicates no posts are available, focus on the profile information."""}
            ]
            
            response = self.llm_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(colored(f"✗ Execution error: {str(e)}", "red"))
            return f"Error executing LinkedIn research: {str(e)}"


def execute(llm_client=None, brief=None):
    """
    Execute LinkedIn research for a given brief.
    
    Parameters:
    - brief (str): Description of the person or company to research
    - llm_client: The LLM client for making API calls
    
    Returns:
    - str: A comprehensive summary of the LinkedIn research
    """
    try:
        if not brief:
            return "No brief provided for LinkedIn research."
            
        print(colored("Initializing LinkedIn Research Tool...", "cyan"))
        tool = LinkedInResearchTool(llm_client)
        
        print(colored("Executing research...", "cyan"))
        result = tool.research(brief)
        
        return result
        
    except Exception as e:
        error_msg = f"Error executing LinkedIn research: {str(e)}"
        print(colored(f"✗ {error_msg}", "red"))
        return error_msg

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "linkedin_research",
        "description": "This tool performs comprehensive LinkedIn research on a person or company, collecting profile data and posts, analyzing them, and providing detailed insights.",
        "parameters": {
            "type": "object",
            "properties": {
                "brief": {
                    "type": "string",
                    "description": "A description of the person or company to research on LinkedIn. Be specific to ensure accurate matching."
                }
            },
            "required": ["brief"]
        }
    }
}