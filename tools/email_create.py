# /tools/email_create.py
import os
import requests
from typing import List, Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def format_body_content(content):
    paragraphs = content.split('\n\n')
    formatted_paragraphs = []
    for para in paragraphs:
        if para.strip():
            # Use traditional email-safe markup with font tags and basic attributes
            formatted = (
                f'<table width="100%" border="0" cellpadding="0" cellspacing="0"><tr><td>'
                f'<font face="Lora, Georgia, Times New Roman, serif" size="5" color="#2b2b2b">'
                f'{para}'
                f'</font>'
                f'</td></tr></table>'
                f'<table width="100%" border="0" cellpadding="0" cellspacing="0" style="height:20px"><tr><td>&nbsp;</td></tr></table>'
            )
            formatted_paragraphs.append(formatted)
    return '\n'.join(formatted_paragraphs)

def apply_template(subject: str, body_content: str) -> str:
    formatted_body = format_body_content(body_content)
    # Create a simpler, more traditional email template
    html = f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Lora:wght@400&display=swap" rel="stylesheet">
<title>Peregian Digital Hub</title>
</head>
<body bgcolor="#F9F6F2" style="margin: 0; padding: 0;">
<table width="100%" border="0" cellpadding="0" cellspacing="0" bgcolor="#F9F6F2">
    <tr>
        <td align="center" valign="top">
            <table width="600" border="0" cellpadding="0" cellspacing="0">
                <!-- Header with images -->
                <tr>
                    <td bgcolor="#0f1328" style="padding: 10px 20px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                                <td width="50%" align="right" style="padding-right: 10px;">
                                    <img src="https://www.peregianhub.com.au/img/email/whale.png" width="250" alt="Whale" style="display: block; width: 100%; max-width: 250px;">
                                </td>
                                <td width="50%" align="left" style="padding-left: 10px;">
                                    <img src="https://www.peregianhub.com.au/img/email/tokenizer.png" width="250" alt="Tokenizer" style="display: block; width: 100%; max-width: 250px;">
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <!-- Subject -->
                <tr>
                    <td style="padding: 40px 40px 20px 40px;">
                        <font face="Lora, Georgia, Times New Roman, serif" size="6" color="#2b2b2b">
                            {subject}
                        </font>
                    </td>
                </tr>
                <!-- Content -->
                <tr>
                    <td style="padding: 0 40px;">
                        {formatted_body}
                    </td>
                </tr>
                <!-- Signature -->
                <tr>
                    <td style="padding: 20px 40px;">
                        <font face="Lora, Georgia, Times New Roman, serif" size="5" color="#2b2b2b">
                            Regards<br><br>
                            Chris Boden<br>
                            Director, Peregian Digital Hub<br>
                            0421850424
                        </font>
                    </td>
                </tr>
                <!-- Logo and Footer -->
                <tr>
                    <td align="center" style="padding: 40px 0;">
                        <img src="https://www.peregianhub.com.au/img/email/logo.png" width="155" alt="Peregian Digital Hub" style="display: block; width: 155px;">
                        <table width="100%" border="0" cellpadding="20" cellspacing="0">
                            <tr>
                                <td align="center">
                                    <font face="Lora, Georgia, Times New Roman, serif" size="3" color="#2b2b2b">
                                        <a href="https://www.peregianhub.com.au/" style="color: #2b2b2b; text-decoration: underline;">peregianhub.com.au</a>
                                    </font>
                                </td>
                            </tr>
                            <tr>
                                <td align="center">
                                    <table border="0" cellpadding="5" cellspacing="0">
                                        <tr>
                                            <td><a href="https://facebook.com/peregianhub"><img src="https://www.peregianhub.com.au/img/email/fb.png" width="20" alt="Facebook"></a></td>
                                            <td><a href="https://linkedin.com/company/peregianhub"><img src="https://www.peregianhub.com.au/img/email/li.png" width="21" alt="LinkedIn"></a></td>
                                            <td><a href="https://www.youtube.com/@peregiandigitalhub4239"><img src="https://www.peregianhub.com.au/img/email/yt.png" width="20" alt="YouTube"></a></td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center">
                                    <font face="Lora, Georgia, Times New Roman, serif" size="3" color="#2b2b2b">
                                        253-255 David Low Way<br>
                                        Peregian Beach QLD 4573, Australia
                                    </font>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
'''
    return html

def execute(
    to: Optional[List[str]], 
    subject: str, 
    content: str,
    body: Optional[str] = None,
    cc: Optional[List[str]] = None, 
    bcc: Optional[List[str]] = None, 
    from_email: Optional[str] = 'chris.boden@noosa.qld.gov.au'
):
    webhook_url = os.getenv('ZAPIER_EMAIL_WEBHOOK_URL')
    if not webhook_url:
        raise ValueError("ZAPIER_EMAIL_WEBHOOK_URL is not set in environment variables")

    final_html = apply_template(subject, content)
    payload = {
        'to': to,
        'subject': subject,
        'html_body': final_html
    }

    if body:
        payload['body'] = body
    else:
        payload['body'] = content

    if cc:
        payload['cc'] = cc
    if bcc:
        payload['bcc'] = bcc
    if from_email:
        payload['from_email'] = from_email

    try:
        response = requests.post(
            webhook_url, 
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            return f"Successfully sent email: {subject}"
        else:
            return f"Failed to send email: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

def send_email(
    to: Union[str, List[str]], 
    subject: str, 
    content: str,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    from_email: Optional[str] = None
):
    to_list = [to] if isinstance(to, str) else to
    cc_list = [cc] if cc and isinstance(cc, str) else cc
    bcc_list = [bcc] if bcc and isinstance(bcc, str) else bcc

    try:
        return execute(
            to=to_list,
            subject=subject,
            content=content,
            cc=cc_list,
            bcc=bcc_list,
            from_email=from_email
        )
    except Exception as e:
        return f"Error in send_email: {str(e)}"

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "email_create",
        "description": "Send an HTML email using the Hub's branded template. Perfect for sending announcements, newsletters, or any communication that should have the Hub's professional look.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Single email address or list of recipient email addresses"
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line of the email"
                },
                "content": {
                    "type": "string",
                    "description": "The main content of the email. Can be plain text - will be automatically formatted with the Hub's styling."
                },
                "cc": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Optional - Single email address or list of CC recipients"
                },
                "bcc": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Optional - Single email address or list of BCC recipients"
                },
                "from_email": {
                    "type": "string",
                    "description": "Optional - Sender email address. Defaults to Hub's official email."
                }
            },
            "required": ["to", "subject", "content"]
        }
    }
}