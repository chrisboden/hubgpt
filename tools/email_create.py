# tools/email_create.py
import os
import requests
from typing import List, Optional

def execute(
    to: Optional[List[str]] , 
    subject: str, 
    html_body: str,
    body: Optional[str] = None,  # Made optional with default None
    cc: Optional[List[str]] = None, 
    bcc: Optional[List[str]] = None, 
    from_email: Optional[str] = 'chris.boden@noosa.qld.gov.au'
):
    # Get Zapier webhook URL from environment variable
    webhook_url = os.getenv('ZAPIER_EMAIL_WEBHOOK_URL')
    
    if not webhook_url:
        raise ValueError("ZAPIER_EMAIL_WEBHOOK_URL is not set in environment variables")

    # Prepare payload with html_body as primary content
    payload = {
        'to': to,
        'subject': subject,
        'html_body': html_body
    }

    # Add plain text body if provided
    if body:
        payload['body'] = body

    # Add optional fields if provided
    if cc:
        payload['cc'] = cc
    if bcc:
        payload['bcc'] = bcc
    if from_email:
        payload['from_email'] = from_email

    # Send the email via webhook
    try:
        response = requests.post(
            webhook_url, 
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Check response
        if response.status_code == 200:
            return f"Successfully sent email: {subject}"
        else:
            return f"Failed to send email: {response.status_code} - {response.text}"
    
    except Exception as e:
        return f"Error sending email: {str(e)}"

# Update Tool metadata for LLM integration
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "email_create",
        "description": "Send an HTML email using a Zapier webhook. Creates rich HTML emails with optional plain text fallback.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses"
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line of the email"
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML content of the email. This is the primary email content."
                },
                "body": {
                    "type": "string", 
                    "description": "Optional plain text version of the email content for fallback"
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of CC email addresses"
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of BCC email addresses"
                },
                "from_email": {
                    "type": "string",
                    "description": "Optional sender email address. Defaults to chris.boden@noosa.qld.gov.au"
                }
            },
            "required": ["subject", "html_body"]
        }
    }
}