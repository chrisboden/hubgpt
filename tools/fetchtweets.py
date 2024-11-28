import os
import requests
import json
from dotenv import load_dotenv
from pathlib import Path

# Get the current script's directory
current_dir = Path(__file__).resolve().parent

# Get the parent directory (root of the project)
root_dir = current_dir.parent

# Load environment variables from .env file in the root directory
load_dotenv(dotenv_path=root_dir / '.env')

# Constants
API_URL = "https://twitter241.p.rapidapi.com/list-timeline"
DEFAULT_LIST_ID = "1609883077026918400"
DEFAULT_MAX_PAGES = 5  # Set the default maximum number of pages to fetch
OUTPUT_FILE = "tools/tweets.json"
LAST_FETCH_FILE = "tools/last_fetch_id.txt"
VERBOSE = True  # Set to True to enable detailed logging

# Load API key from environment variable
API_KEY = os.getenv("RAPIDAPI_KEY")
if not API_KEY:
    raise ValueError("Please set the RAPIDAPI_KEY environment variable.")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "twitter241.p.rapidapi.com"
}

def get_last_fetch_id():
    """Read the last fetched tweet ID from file."""
    if os.path.exists(LAST_FETCH_FILE):
        with open(LAST_FETCH_FILE, 'r') as f:
            last_id = f.read().strip()
            if VERBOSE:
                print(f"Last fetched tweet ID: {last_id}")
            return last_id
    if VERBOSE:
        print("No last fetched tweet ID found.")
    return None

def save_last_fetch_id(tweet_id):
    """Save the last fetched tweet ID to file."""
    with open(LAST_FETCH_FILE, 'w') as f:
        f.write(tweet_id)
    if VERBOSE:
        print(f"Saved last fetched tweet ID: {tweet_id}")

def save_tweets(tweets):
    """Save tweets to the output file."""
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(tweets, f, indent=2)

def fetch_tweets(list_id=DEFAULT_LIST_ID, max_pages=DEFAULT_MAX_PAGES):
    """Fetch tweets from the API, paginating until reaching previously fetched tweets or max pages."""
    print("fetching tweets")
    last_fetch_id = get_last_fetch_id()
    params = {"listId": list_id}
    tweets = []
    stop_fetching = False
    page_count = 0  # Keep track of the number of pages fetched

    while not stop_fetching:
        page_count += 1
        if VERBOSE:
            print(f"\nFetching page {page_count}...")
            print(f"Request params: {params}")

        try:
            response = requests.get(API_URL, headers=HEADERS, params=params)
            if VERBOSE:
                print(f"API response status code: {response.status_code}")
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            if VERBOSE:
                print("API response received.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tweets: {e}")
            break

        # Extract tweets from the response
        instructions = data.get('result', {}).get('timeline', {}).get('instructions', [])
        if not instructions:
            print("No instructions found in the response.")
            break

        entries = instructions[0].get('entries', [])
        if VERBOSE:
            print(f"Number of entries found: {len(entries)}")

        if not entries:
            print("No entries found in the response.")
            break

        for entry in entries:
            content = entry.get('content', {})
            if content.get('__typename') not in ('TimelineTimelineModule', 'TimelineTimelineItem'):
                continue  # Skip non-tweet entries

            if content.get('__typename') == 'TimelineTimelineModule':
                items = content.get('items', [])
                if VERBOSE:
                    print(f"Number of items in entry: {len(items)}")

                for item in items:
                    tweet = item.get('item', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                    if not tweet:
                        continue

                    tweet_id = tweet.get('rest_id')
                    if VERBOSE:
                        print(f"Processing tweet ID: {tweet_id}")

                    if tweet_id == last_fetch_id:
                        if VERBOSE:
                            print("Reached previously fetched tweet. Stopping fetch.")
                        stop_fetching = True
                        break  # Stop fetching when reaching last fetched tweet

                    processed_tweet = process_tweet(tweet)
                    tweets.append(processed_tweet)

                    # Update last_fetch_id with the most recent tweet ID
                    if len(tweets) == 1:
                        last_fetch_id = tweet_id

                if stop_fetching:
                    break

            elif content.get('__typename') == 'TimelineTimelineItem':
                tweet = content.get('itemContent', {}).get('tweet_results', {}).get('result', {})
                if not tweet:
                    continue

                tweet_id = tweet.get('rest_id')
                if VERBOSE:
                    print(f"Processing tweet ID: {tweet_id}")

                if tweet_id == last_fetch_id:
                    if VERBOSE:
                        print("Reached previously fetched tweet. Stopping fetch.")
                    stop_fetching = True
                    break  # Stop fetching when reaching last fetched tweet

                processed_tweet = process_tweet(tweet)
                tweets.append(processed_tweet)

                # Update last_fetch_id with the most recent tweet ID
                if len(tweets) == 1:
                    last_fetch_id = tweet_id

        # After processing the page, save tweets incrementally
        if tweets:
            save_tweets(tweets)
            if VERBOSE:
                print(f"Saved {len(tweets)} tweets after page {page_count}.")

        # Get the next cursor for pagination
        cursor_bottom = data.get('cursor', {}).get('bottom')
        if VERBOSE:
            print(f"Cursor bottom: {cursor_bottom}")

        if cursor_bottom and not stop_fetching:
            if page_count >= max_pages:
                if VERBOSE:
                    print("Reached maximum number of pages to fetch.")
                break  # Reached the maximum number of pages to fetch
            params['cursor'] = cursor_bottom
        else:
            if VERBOSE:
                print("No more pages to fetch.")
            break  # No more pages to fetch

    # After all pages are fetched, save the last fetched tweet ID
    if tweets:
        save_last_fetch_id(tweets[0]['tweet_id'])  # Most recent tweet ID
    else:
        if VERBOSE:
            print("No tweets fetched; not updating last fetched tweet ID.")

    return tweets

def process_tweet(tweet):
    """Process a tweet JSON object to extract required fields."""
    legacy = tweet.get('legacy', {})
    user = tweet.get('core', {}).get('user_results', {}).get('result', {})
    user_legacy = user.get('legacy', {})

    tweet_content = legacy.get('full_text', '')
    # Remove URLs from the tweet content
    tweet_content_clean = ' '.join(word for word in tweet_content.split() if not word.startswith('http'))

    processed_tweet = {
        "tweet_id": tweet.get('rest_id', ''),
        "user_id": user.get('rest_id', ''),
        "user_handle": user_legacy.get('screen_name', ''),
        "user_name": user_legacy.get('name', ''),
        "user_avatar_url": user_legacy.get('profile_image_url_https', ''),
        "tweet_content": tweet_content_clean,
        "tweet_media_urls": extract_media_urls(legacy),
        "tweet_created_at": legacy.get('created_at', ''),
    }

    # Handle quote tweets
    if 'quoted_status_result' in tweet:
        quoted_status = tweet['quoted_status_result']['result']
        quoted_tweet = process_quoted_tweet(quoted_status)
        processed_tweet['quoted_tweet'] = quoted_tweet

    # Handle retweets
    if 'retweeted_status_result' in tweet:
        retweeted_status = tweet['retweeted_status_result']['result']
        retweeted_tweet = process_quoted_tweet(retweeted_status)
        processed_tweet['retweeted_tweet'] = retweeted_tweet

    if VERBOSE:
        print(f"Processed tweet: {processed_tweet}")

    return processed_tweet

def process_quoted_tweet(tweet):
    """Process a quoted or retweeted tweet."""
    legacy = tweet.get('legacy', {})
    user = tweet.get('core', {}).get('user_results', {}).get('result', {})
    user_legacy = user.get('legacy', {})

    tweet_content = legacy.get('full_text', '')
    # Remove URLs from the tweet content
    tweet_content_clean = ' '.join(word for word in tweet_content.split() if not word.startswith('http'))

    processed_quoted_tweet = {
        "tweet_id": tweet.get('rest_id', ''),
        "user_id": user.get('rest_id', ''),
        "user_handle": user_legacy.get('screen_name', ''),
        "user_name": user_legacy.get('name', ''),
        "user_avatar_url": user_legacy.get('profile_image_url_https', ''),
        "tweet_content": tweet_content_clean,
        "tweet_media_urls": extract_media_urls(legacy),
        "tweet_created_at": legacy.get('created_at', ''),
    }

    return processed_quoted_tweet

def extract_media_urls(legacy):
    """Extract media URLs from tweet's extended entities."""
    media_urls = []
    extended_entities = legacy.get('extended_entities', {})
    media = extended_entities.get('media', [])
    for item in media:
        media_url = item.get('media_url_https')
        if not media_url:
            # Check for video URLs
            video_info = item.get('video_info', {})
            variants = video_info.get('variants', [])
            for variant in variants:
                if variant.get('content_type') == 'video/mp4':
                    media_url = variant.get('url')
                    break
        if media_url:
            media_urls.append(media_url)
    return media_urls

def execute(list_id=DEFAULT_LIST_ID, max_pages=DEFAULT_MAX_PAGES, llm_client=None):
    """Execute function to fetch tweets and return the content of tweets.json as a string."""
    if VERBOSE:
        print("Starting tweet fetching process...")
    tweets = fetch_tweets(list_id, max_pages)
    if tweets:
        print(f"Fetched a total of {len(tweets)} tweets.")
    
    # Read the contents of the file and return directly as a string (no need for json.dumps)
    with open(OUTPUT_FILE, 'r') as f:
        tweets_content = f.read()
    
    return tweets_content


# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "fetchtweets",
        "description": "Get the latest tweets from a Twitter list",
        "parameters": {
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "The id of the twitter list to use"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "The maximum number of pages to page through in the twitter api call. It is approximately 3 pages of tweets per day so if the user asks for the last week, it would be 21 pages, if they ask for today, it would be 3. Never more than 21"
                }
            },
            "required": [
                "list_id",
                "max_pages"
            ]
        }
    }
}