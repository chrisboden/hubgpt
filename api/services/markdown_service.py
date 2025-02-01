import re
import markdown
from typing import Tuple, List
from markdown.extensions import fenced_code
from markdown.extensions import tables
from markdown.extensions import toc
from markdown.extensions import codehilite
from markdown.extensions import nl2br

def extract_title_and_tags(content: str) -> Tuple[str, List[str]]:
    """Extract title and tags from Markdown content"""
    # Extract title from first H1/H2 heading
    title_match = re.search(r'^#\s+(.+)$|^##\s+(.+)$', content, re.MULTILINE)
    title = (title_match.group(1) or title_match.group(2)) if title_match else None

    # Extract hashtags (excluding Markdown headers)
    tag_matches = re.finditer(r'(?<!#)#([a-zA-Z]\w+)', content)
    tags = [match.group(1) for match in tag_matches]

    return title, list(set(tags))  # Deduplicate tags

def render_markdown(content: str) -> str:
    """Render Markdown content to HTML with syntax highlighting"""
    html = markdown.markdown(
        content,
        extensions=[
            'fenced_code',
            'tables',
            'toc',
            'codehilite',
            'nl2br'
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True,
                'noclasses': True,
                'pygments_style': 'monokai'
            }
        }
    )
    return html 