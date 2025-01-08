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
        self.data_dir = 'data'
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
                print(colored(f"✓ Created data directory at {self.data_dir}", "green"))
            except Exception as e:
                print(colored(f"✗ Error creating data directory: {str(e)}", "red"))
                raise
        
        self.db_path = os.path.join(self.data_dir, 'linkedin.db')
        self._init_db()
        
        # Add rate limiting parameters
        self.retry_count = 0
        self.max_retries = 3
        self.base_backoff = 2  # seconds
        self.max_backoff = 32  # seconds

    def _get_db(self):
        """Get a fresh database connection"""
        try:
            return duckdb.connect(self.db_path)
        except Exception as e:
            print(colored(f"✗ Error connecting to database: {str(e)}", "red"))
            raise

    def _init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            with self._get_db() as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS person (
                        linkedin_id VARCHAR PRIMARY KEY,
                        profile_raw JSON,
                        profile_summary JSON,
                        posts_raw JSON,
                        posts_summary JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                db.execute("""
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

    def _check_cache(self, linkedin_id: str, entity_type: str) -> Optional[Dict]:
        """Check if we have recent data in the database"""
        try:
            # Define cache expiry (7 days)
            CACHE_EXPIRY_DAYS = 7
            
            with self._get_db() as db:
                result = db.execute(f"""
                    SELECT 
                        linkedin_id,
                        profile_raw,
                        profile_summary,
                        posts_raw,
                        posts_summary,
                        created_at
                    FROM {entity_type}
                    WHERE linkedin_id = ?
                    AND created_at > CURRENT_TIMESTAMP - INTERVAL '{CACHE_EXPIRY_DAYS} days'
                """, [linkedin_id]).fetchone()
            
            if result:
                print(colored(f"✓ Found recent cache entry for {linkedin_id}", "green"))
                return {
                    'linkedin_id': result[0],
                    'profile_raw': json.loads(result[1]) if result[1] else None,
                    'profile_summary': json.loads(result[2]) if result[2] else None,
                    'posts_raw': json.loads(result[3]) if result[3] else None,
                    'posts_summary': json.loads(result[4]) if result[4] else None,
                    'created_at': result[5]
                }
            
            print(colored(f"No recent cache entry found for {linkedin_id}", "yellow"))
            return None
            
        except Exception as e:
            print(colored(f"✗ Error checking cache: {str(e)}", "red"))
            return None

    def _update_api_endpoint(self):
        """Switch to alternate API endpoint and update headers"""
        self.current_api_index = (self.current_api_index + 1) % len(self.api_endpoints)
        new_host = self.api_endpoints[self.current_api_index].replace('https://', '')
        self.headers["x-rapidapi-host"] = new_host
        print(colored(f"Switching to alternate API endpoint: {self.api_endpoints[self.current_api_index]}", "yellow"))

    def _make_api_request(self, endpoint_path: str, params: dict) -> Dict:
        """Make API request with improved rate limit handling"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                current_base = self.api_endpoints[self.current_api_index]
                full_url = f"{current_base}/{endpoint_path}"
                
                print(colored(f"Making API request to: {full_url}", "cyan"))
                print(f"Request params:\n{params}")
                
                # Calculate backoff time
                backoff_time = min(self.base_backoff * (2 ** attempt), self.max_backoff)
                
                response = requests.get(
                    full_url,
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    # Reset retry count on success
                    self.retry_count = 0
                    return response.json()
                    
                elif response.status_code == 429:  # Rate limit exceeded
                    print(colored(f"Rate limit exceeded on {current_base}", "yellow"))
                    print(colored(f"Backing off for {backoff_time} seconds", "yellow"))
                    time.sleep(backoff_time)
                    self._update_api_endpoint()
                    continue
                    
                else:
                    raise Exception(f"API request failed with status {response.status_code}")
                    
            except Exception as e:
                last_error = e
                print(colored(f"Error with endpoint {current_base}: {str(e)}", "red"))
                
                if attempt < self.max_retries - 1:
                    print(colored(f"Retrying in {backoff_time} seconds...", "yellow"))
                    time.sleep(backoff_time)
                    self._update_api_endpoint()
                else:
                    raise Exception(f"All API endpoints failed after {self.max_retries} attempts. Last error: {str(last_error)}")

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
            
            # Enhanced validation and debug logging
            print(colored(f"Raw profile data received: {json.dumps(profile_data, indent=2)}", "cyan"))
            
            # Ensure we have valid profile data - check both the data itself and its structure
            if not profile_data or (isinstance(profile_data, dict) and not profile_data.get('data', {}) and not profile_data.get('firstName')):
                print(colored("No valid profile data found in input", "yellow"))
                return {
                    "status": "no_data",
                    "message": "No profile data available",
                    "timestamp": datetime.now().isoformat()
                }
            
            # If profile_data has a 'data' key, use that, otherwise use profile_data directly
            data_to_summarize = profile_data.get('data', profile_data)
            print(colored(f"Data being sent to LLM for summary: {json.dumps(data_to_summarize, indent=2)}", "cyan"))
                
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
                {"role": "user", "content": f"Here is the data to summarise: {json.dumps(data_to_summarize)}"}
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

    def _clean_posts_data(self, posts_data: List[Dict]) -> List[Dict]:
        """Clean and validate post data"""
        cleaned_posts = []
        for post in posts_data:
            try:
                # Extract essential fields with defaults
                cleaned_post = {
                    "text": post.get("text", "").strip(),
                    "postedAt": post.get("postedAt", "unknown"),
                    "totalReactionCount": post.get("totalReactionCount", 0),
                    "postUrl": post.get("postUrl", ""),
                }
                
                # Only include posts with actual content
                if cleaned_post["text"]:
                    cleaned_posts.append(cleaned_post)
                    
            except Exception as e:
                print(colored(f"Error cleaning post: {str(e)}", "yellow"))
                continue
                
        return cleaned_posts

    def _generate_posts_summary(self, posts_data: List[Dict], entity_type: str) -> Dict:
        """Generate normalized posts summary using LLM with improved error handling"""
        try:
            # Validate input
            if not isinstance(posts_data, list):
                return {
                    "status": "error",
                    "message": "Invalid posts data format",
                    "timestamp": datetime.now().isoformat()
                }
                
            # Clean and validate posts
            cleaned_posts = self._clean_posts_data(posts_data)
            
            if not cleaned_posts:
                return {
                    "status": "no_posts",
                    "message": "No valid posts available",
                    "timestamp": datetime.now().isoformat()
                }
                
            try:
                messages = [
                    {"role": "system", "content": f"""You are an expert at analyzing LinkedIn posting activity. 
                    Create a summary of this {entity_type}'s posting activity.
                    
                    Focus on:
                    1. Key announcements and achievements
                    2. Professional insights and thought leadership
                    3. Major events or milestones
                    4. Industry trends and commentary
                    
                    Return a JSON object with:
                    {{
                        "summary": {{
                            "recentPosts": [
                                {{
                                    "timestamp": "when posted",
                                    "topic": "main topic",
                                    "key_points": ["list of key points"],
                                    "engagement": "engagement metrics"
                                }}
                            ],
                            "topThemes": ["list of recurring themes"],
                            "postingFrequency": "analysis of posting frequency"
                        }}
                    }}"""},
                    {"role": "user", "content": f"Analyze these posts: {json.dumps(cleaned_posts)}"}
                ]
                
                response = self.llm_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                summary = json.loads(response.choices[0].message.content)
                
                if not isinstance(summary, dict) or "summary" not in summary:
                    raise ValueError("Invalid summary format returned from LLM")
                    
                return {
                    "status": "success",
                    "summary": summary["summary"],
                    "timestamp": datetime.now().isoformat()
                }
                
            except json.JSONDecodeError as e:
                print(colored(f"Error parsing summary: {str(e)}", "yellow"))
                return {
                    "status": "error",
                    "message": f"Error parsing summary: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(colored(f"✗ Error generating posts summary: {str(e)}", "red"))
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _validate_profile_data(self, profile_data: Dict) -> bool:
        """Validate profile data before saving"""
        required_fields = ['linkedin_id', 'profile_raw']
        
        try:
            # Check required fields exist
            if not all(field in profile_data for field in required_fields):
                print(colored(f"Missing required fields: {required_fields}", "red"))
                return False
                
            # Validate linkedin_id
            if not profile_data['linkedin_id'] or not isinstance(profile_data['linkedin_id'], str):
                print(colored("Invalid linkedin_id", "red"))
                return False
                
            # Validate profile_raw
            if not profile_data['profile_raw'] or not isinstance(profile_data['profile_raw'], dict):
                print(colored("Invalid profile_raw data", "red"))
                return False
                
            return True
            
        except Exception as e:
            print(colored(f"Error validating profile data: {str(e)}", "red"))
            return False

    def _save_to_db(self, data: Dict, entity_type: str):
        """Save data to appropriate database table with improved validation"""
        try:
            # Validate input data
            if not self._validate_profile_data(data):
                raise ValueError("Invalid profile data")
                
            table = entity_type
            current_timestamp = datetime.now().isoformat()
            
            # Prepare data with proper JSON serialization
            profile_raw = json.dumps(data['profile_raw']) if data['profile_raw'] else None
            profile_summary = json.dumps(data['profile_summary']) if data['profile_summary'] else None
            posts_raw = json.dumps(data['posts_raw']) if data['posts_raw'] else None
            posts_summary = json.dumps(data['posts_summary']) if data['posts_summary'] else None
            
            # Use a fresh connection for the transaction
            with self._get_db() as db:
                db.execute(f"""
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
                    profile_raw,
                    profile_summary,
                    posts_raw,
                    posts_summary,
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
            
            # Check cache before making API calls
            cached_data = self._check_cache(linkedin_id, entity_type)
            if cached_data:
                print(colored("Using cached data...", "green"))
                # Generate final summary from cached data
                messages = [
                    {"role": "system", "content": """You are an expert at synthesizing LinkedIn information into clear, insightful summaries.
                    If there are no posts available, focus on the profile information only."""},
                    {"role": "user", "content": f"""Please create a comprehensive summary based on this cached data:
                    
                    Profile Summary: {json.dumps(cached_data['profile_summary'])}
                    
                    Posts Summary: {json.dumps(cached_data['posts_summary'])}
                    
                    Note: If the posts summary indicates no posts are available, focus on the profile information."""}
                ]
                
                response = self.llm_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            
            # If no cache hit, proceed with API calls
            print(colored("No recent cache found, fetching fresh data...", "cyan"))
            
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
            
            # Generate profile summary - pass profile_data directly, not nested under 'data'
            try:
                profile_summary = self._generate_profile_summary(profile_data, entity_type)
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