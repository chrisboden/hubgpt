# tools/email_create.py

"""
Send an HTML email using a Zapier webhook. Creates rich HTML emails with optional plain text fallback.

Key Features:
- Branded HTML email template with responsive design
- Support for plain text and HTML content
- CC and BCC recipient support
- Custom sender email support
- Zapier webhook integration for sending

Common Usage Patterns:
1. Simple email:
   ```python
   from tools.email_create import send_email
   result = send_email(
       to="recipient@example.com",
       subject="Hello",
       content="Your message here"
   )
   ```

2. Multiple recipients with CC/BCC:
   ```python
   result = send_email(
       to=["recipient1@example.com", "recipient2@example.com"],
       subject="Team Update",
       content="Meeting notes...",
       cc="manager@example.com",
       bcc=["archive@example.com"]
   )
   ```

Required Environment Variables:
- ZAPIER_EMAIL_WEBHOOK_URL: Webhook URL for sending emails via Zapier

Note: The email will automatically use the Hub's branded template with proper styling.
"""

import os
import requests
from typing import List, Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

template = """
<!DOCTYPE html>
<html xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">

<head>
 <meta charset="UTF-8" />
 <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
 <!--[if !mso]><!-- -->
 <meta http-equiv="X-UA-Compatible" content="IE=edge" />
 <!--<![endif]-->
 <meta name="viewport" content="width=device-width, initial-scale=1.0" />
 <meta name="format-detection" content="telephone=no" />
 <meta name="format-detection" content="date=no" />
 <meta name="format-detection" content="address=no" />
 <meta name="format-detection" content="email=no" />
 <meta name="x-apple-disable-message-reformatting" />
 <link href="https://fonts.googleapis.com/css?family=Seaweed+Script:ital,wght@0,400" rel="stylesheet" />
 <link href="https://fonts.googleapis.com/css?family=GFS+Didot:ital,wght@0,400" rel="stylesheet" />
 <link href="https://fonts.googleapis.com/css?family=Baskervville:ital,wght@0,400;1,400" rel="stylesheet" />
 <link href="https://fonts.googleapis.com/css?family=Oswald:ital,wght@" rel="stylesheet" />
 <title>Peregian Digital Hub</title>

 <style>
 html,
         body {
             margin: 0 !important;
             padding: 0 !important;
             min-height: 100% !important;
             width: 100% !important;
             -webkit-font-smoothing: antialiased;
             background-color: #F9F6F2 !important;
         }
 
         * {
             -ms-text-size-adjust: 100%;
         }
 
         #outlook a {
             padding: 0;
         }
 
         .ReadMsgBody,
         .ExternalClass {
             width: 100%;
         }
 
         .ExternalClass,
         .ExternalClass p,
         .ExternalClass td,
         .ExternalClass div,
         .ExternalClass span,
         .ExternalClass font {
             line-height: 100%;
         }
 
         table,
         td,
         th {
             mso-table-lspace: 0 !important;
             mso-table-rspace: 0 !important;
             border-collapse: collapse;
         }
 
         u + .body table, u + .body td, u + .body th {
             will-change: transform;
         }
 
         body, td, th, p, div, li, a, span {
             -webkit-text-size-adjust: 100%;
             -ms-text-size-adjust: 100%;
             mso-line-height-rule: exactly;
         }
 
         img {
             border: 0;
             outline: 0;
             line-height: 100%;
             text-decoration: none;
             -ms-interpolation-mode: bicubic;
         }
 
         a[x-apple-data-detectors] {
             color: inherit !important;
             text-decoration: none !important;
         }
                 
         .body .pc-project-body {
             background-color: transparent !important;
         }
 
         @media (min-width: 621px) {
             .pc-lg-hide {
                 display: none;
             } 
 
             .pc-lg-bg-img-hide {
                 background-image: none !important;
             }
         }
 </style>
 <style>
 @media (max-width: 620px) {
 .pc-project-body {min-width: 0px !important;}
 .pc-project-container {width: 100% !important;}
 .pc-sm-hide, .pc-w620-gridCollapsed-1 > tbody > tr > .pc-sm-hide {display: none !important;}
 .pc-sm-bg-img-hide {background-image: none !important;}
 
 /* New mobile-specific styles */
 .mobile-stack {
     display: block !important;
     width: 100% !important;
 }
 .para {
     font-size:19px
 }
 .mobile-stack td {
     display: block !important;
     width: 100% !important;
     padding: 10px 20px !important;
     text-align: center !important;
 }
 .mobile-img {
     width: 80% !important;
     max-width: 300px !important;
     margin: 0 auto !important;
 }
 .mobile-padding {
     padding: 20px 15px !important;
 }
 }
 </style>
 <!--[if mso]>
    <style type="text/css">
        .pc-font-alt {
            font-family: Georgia, Times New Roman, Times, serif !important;
        }
    </style>
    <![endif]-->
 <!--[if gte mso 9]>
    <xml>
        <o:OfficeDocumentSettings>
            <o:AllowPNG/>
            <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
    </xml>
    <![endif]-->
</head>

<body class="body pc-font-alt" style="width: 100% !important; min-height: 100% !important; margin: 0 !important; padding: 0 !important; line-height: 1.5; color: #2D3A41; mso-line-height-rule: exactly; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; font-variant-ligatures: normal; text-rendering: optimizeLegibility; -moz-osx-font-smoothing: grayscale; background-color: #F9F6F2 !important;" bgcolor="#F9F6F2">

 <table class="pc-project-body" style="table-layout: fixed; min-width: 600px; background-color: #F9F6F2 !important;" bgcolor="#F9F6F2" width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
   <tr style="background-color: #0f1328;">
   <td align="center" valign="top">
    <table class="pc-project-container" align="center" width="600" style="width: 600px; max-width: 600px; background-color: #0f1328;" border="0" cellpadding="0" cellspacing="0" role="presentation">
     <tr>
      <td class="mobile-padding" style="padding: 40px 20px;">
       <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation" class="mobile-stack">
        <tr>
         <td align="right" style="padding-right: 5px;" class="mobile-stack">
          <img src="https://www.peregianhub.com.au/img/email/whale.png" width="250" alt="Whale" style="display: block; border: 0; max-width: 100%; height: auto;" class="mobile-img" />
         </td>
         <td align="left" style="padding-left: 5px;" class="mobile-stack">
          <img src="https://www.peregianhub.com.au/img/email/tokenizer.png" width="250" alt="Tokenizer" style="display: block; border: 0; max-width: 100%; height: auto;" class="mobile-img" />
         </td>
        </tr>
       </table>
      </td>
     </tr>
    </table>
   </td>
  </tr>
  <tr>
   <td align="center" valign="top">
    <table class="pc-project-container" align="center" width="600" style="width: 600px; max-width: 600px; background-color: #F9F6F2;" border="0" cellpadding="0" cellspacing="0" role="presentation">
     <tr>
      <td class="pc-w620-padding-20-0-0-0" style="padding: 20px 0px 20px 0px;" align="left" valign="top">
       <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%" style="width: 100%;">
        <tr>
         <td valign="top">
          <!-- BEGIN MODULE: Text -->
          <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
           <tr>
            <td class="pc-w620-spacing-0-0-0-0" style="padding: 0px 0px 0px 0px;">
             <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
              <tr>
               <td valign="top" class="pc-w620-padding-30-40-30-40" style="padding: 30px 60px 30px 60px; border-radius: 0px; background-color: transparent;" bgcolor="transparent">
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                 <tr>
                  <td align="left" valign="top" style="padding: 0px 0px 27px 0px;">
                   <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%" style="border-collapse: separate; border-spacing: 0; margin-right: auto; margin-left: auto;">
                    <tr>
                     <td valign="top" align="left" style="padding: 0px 0px 0px 0px;">
                      <div class="pc-font-alt pc-w620-fontSize-32px" style="line-height: 120%; letter-spacing: -0.8px; font-family: 'Seaweed Script', Georgia, Times New Roman, Times, serif; font-size: 46px; font-weight: normal; font-variant-ligatures: normal; color: #322e27; text-align: left; text-align-last: left;">
                       <div><span>{{SUBJECT}}</span>
                       </div>
                      </div>
                     </td>
                    </tr>
                   </table>
                  </td>
                 </tr>
                </table>
                <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%" style="border-collapse: separate; border-spacing: 0; margin-right: auto; margin-left: auto;">
                 <tr>
                  <td valign="top" align="left">
                   <div class="pc-font-alt" style="line-height: 180%; letter-spacing: 0px; font-family: 'GFS Didot', Georgia, Times New Roman, Times, serif; font-size: 17px; font-weight: normal; font-variant-ligatures: normal; color: #322e27; text-align: left; text-align-last: left;">
                    {{BODY}}
                    <div><span>&#xFEFF;</span>
                    </div>
                    <div><span>Regards</span>
                    </div>
                    <div><span>&#xFEFF;</span>
                    </div>
                    <div><span>Chris Boden</span>
                    </div>
                    <div><span>Director, Peregian Digital Hub</span>
                    </div>
                    <div><span>0421850424</span>
                    </div>
                   </div>
                  </td>
                 </tr>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                 <tr>
                  <td align="center" valign="top" style="padding: 50px 0px 12px 0px;">
                   <img src="https://www.peregianhub.com.au/img/email/logo.png" width="155" height="43" alt="" style="display: block; outline: 0; line-height: 100%; -ms-interpolation-mode: bicubic; width: 155px; height: auto; max-width: 100%; border: 0;" />
                  </td>
                 </tr>
                </table>
                <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%" style="border-collapse: separate; border-spacing: 0; margin-right: auto; margin-left: auto;">
                 <tr>
                  <td valign="top" align="center">
                   <div class="pc-font-alt" style="line-height: 180%; letter-spacing: 0px; font-family: 'Baskervville', Georgia, Times New Roman, Times, serif; font-size: 14px; font-weight: normal; font-variant-ligatures: normal; color: #322e27; text-align: center; text-align-last: center;">
                    <div><span>&#xFEFF;</span><a href="https://www.peregianhub.com.au/" target="_blank" style="text-decoration: none; color: #322e27;"><span style="text-decoration: underline;font-weight: 400;font-style: italic;">peregianhub.com.au</span></a><span>&#xFEFF;</span>
                    </div>
                   </div>
                  </td>
                 </tr>
                </table>
               </td>
              </tr>
             </table>
            </td>
           </tr>
          </table>
          <!-- END MODULE: Text -->
         </td>
        </tr>
        <tr>
         <td valign="top">
          <!-- BEGIN MODULE: Footer -->
          <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
           <tr>
            <td class="pc-w620-spacing-0-0-0-0" style="padding: 0px 0px 0px 0px;">
             <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
              <tr>
               <td valign="top" class="pc-w620-padding-40-30-30-30" style="padding: 20px 40px 20px 40px; border-radius: 0px; background-color: transparent;" bgcolor="transparent">
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width: 100%;">
                 <tr>
                  <td valign="top" style="padding: 0px 0px 50px 0px;">
                   <table width="83" border="0" cellpadding="0" cellspacing="0" role="presentation" style="margin: auto;">
                    <tr>
                     <!--[if gte mso 9]>
                    <td height="1" valign="top" style="line-height: 1px; font-size: 1px; border-bottom: 1px solid #bebebe;">&nbsp;</td>
                <![endif]-->
                     <!--[if !gte mso 9]><!-- -->
                     <td height="1" valign="top" style="line-height: 1px; font-size: 1px; border-bottom: 1px solid #bebebe;">&nbsp;</td>
                     <!--<![endif]-->
                    </tr>
                   </table>
                  </td>
                 </tr>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                 <tr>
                  <td align="center" style="padding: 0px 0px 23px 0px;">
                   <table class="pc-width-hug pc-w620-gridCollapsed-0" align="center" border="0" cellpadding="0" cellspacing="0" role="presentation">
                    <tr class="pc-grid-tr-first pc-grid-tr-last">
                     <td class="pc-grid-td-first pc-w620-itemsSpacings-20-0" valign="top" style="padding-top: 0px; padding-right: 15px; padding-bottom: 0px; padding-left: 15px;">
                      <table style="border-collapse: separate; border-spacing: 0;" border="0" cellpadding="0" cellspacing="0" role="presentation">
                       <tr>
                        <td align="left" valign="top">
                         <table align="left" width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width: 100%;">
                          <tr>
                           <td align="left" valign="top">
                            <table align="left" border="0" cellpadding="0" cellspacing="0" role="presentation">
                             <tr>
                              <td class="pc-w620-spacing-0-30-0-0" valign="top" style="padding: 0px 10px 0px 0px;">
                               <a href="https://facebook.com/peregianhub" target="_blank" style="text-decoration: none;">
                                <img src="https://www.peregianhub.com.au/img/email/fb.png" class="" width="20" height="20" style="display: block; border: 0; outline: 0; line-height: 100%; -ms-interpolation-mode: bicubic; width: 20px; height: 20px;" alt="Facebook" />
                               </a>
                              </td>
                             </tr>
                            </table>
                           </td>
                          </tr>
                         </table>
                        </td>
                       </tr>
                      </table>
                     </td>
                     <td class="pc-w620-itemsSpacings-20-0" valign="top" style="padding-top: 0px; padding-right: 15px; padding-bottom: 0px; padding-left: 15px;">
                      <table style="border-collapse: separate; border-spacing: 0;" border="0" cellpadding="0" cellspacing="0" role="presentation">
                       <tr>
                        <td align="left" valign="top">
                         <table align="left" width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width: 100%;">
                          <tr>
                           <td align="left" valign="top">
                            <table align="left" border="0" cellpadding="0" cellspacing="0" role="presentation">
                             <tr>
                              <td valign="top" style="padding: 0px 10px 0px 0px;">
                               <a href="https://linkedin.com/company/peregianhub" target="_blank" style="text-decoration: none;">
                                <img src="https://www.peregianhub.com.au/img/email/li.png" class="" width="21" height="21" style="display: block; border: 0; outline: 0; line-height: 100%; -ms-interpolation-mode: bicubic; width: 21px; height: 21px;" alt="LinkedIn" />
                               </a>
                              </td>
                             </tr>
                            </table>
                           </td>
                          </tr>
                         </table>
                        </td>
                       </tr>
                      </table>
                     </td>
                     <td class="pc-w620-itemsSpacings-20-0" valign="top" style="padding-top: 0px; padding-right: 15px; padding-bottom: 0px; padding-left: 15px;padding-right: 15px;">
                      <table style="border-collapse: separate; border-spacing: 0;" border="0" cellpadding="0" cellspacing="0" role="presentation">
                       <tr>
                        <td align="left" valign="top">
                         <table align="left" width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width: 100%;">
                          <tr>
                           <td align="left" valign="top">
                            <table align="left" border="0" cellpadding="0" cellspacing="0" role="presentation">
                             <tr>
                              <td valign="top" style="padding: 0px 10px 0px 0px;">
                               <a href="https://www.youtube.com/@peregiandigitalhub4239" target="_blank" style="text-decoration: none;">
                                <img src="https://www.peregianhub.com.au/img/email/yt.png" class="" width="20" height="20" style="display: block; border: 0; outline: 0; line-height: 100%; -ms-interpolation-mode: bicubic; width: 20px; height: 20px;" alt="YouTube" />
                               </a>
                              </td>
                             </tr>
                            </table>
                           </td>
                          </tr>
                         </table>
                        </td>
                       </tr>
                      </table>
                     </td>
                    </tr>
                   </table>
                  </td>
                 </tr>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                 <tr>
                  <td align="center" valign="top" style="padding: 0px 0px 14px 0px;">
                   <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%" style="border-collapse: separate; border-spacing: 0; margin-right: auto; margin-left: auto;">
                    <tr>
                     <td valign="top" align="center">
                      <div class="pc-font-alt" style="line-height: 20px; letter-spacing: -0.2px; font-family: 'Baskervville', Georgia, Times New Roman, Times, serif; font-size: 14px; font-weight: normal; font-variant-ligatures: normal; color: #322e27; text-align: center; text-align-last: center;">
                       <div><span>253-255 David Low Way</span>
                       </div>
                       <div><span>Peregian Beach QLD 4573, Australia</span>
                       </div>
                      </div>
                     </td>
                    </tr>
                   </table>
                  </td>
                 </tr>
                </table>
               </td>
              </tr>
             </table>
            </td>
           </tr>
          </table>
          <!-- END MODULE: Footer -->
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


"""


def format_body_content(content):
    """Format plain text content into template-compatible div spans"""
    paragraphs = content.split(
        '\n\n')  # Split on double newlines for paragraphs
    formatted_paragraphs = []

    for para in paragraphs:
        if para.strip():  # Only process non-empty paragraphs
            formatted = f'<div class="para"><span style = "font-family: \'GFS Didot\', Georgia, Times New Roman, Times, serif;font-size:17px; font-weight: 400;font-style: normal;margin-bottom:1em"> {para}</span><br><br></div>'
            formatted_paragraphs.append(formatted)

    return '\n'.join(formatted_paragraphs)


def apply_template(subject: str, body_content: str) -> str:
    """
    Apply the Hub's HTML template to the email content.

    Args:
        subject: Email subject to include in the template
        body_content: Main content to format and include in the template

    Returns:
        str: Complete HTML email with content properly formatted
    """
    # First format the body content into proper div spans
    formatted_body = format_body_content(body_content)

    # Replace the placeholders
    html = template.replace('{{SUBJECT}}', subject)
    html = html.replace('{{BODY}}', formatted_body)

    return html


def execute(
    to: Optional[List[str]],
    subject: str,
    html_body: str,
    body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    from_email: Optional[str] = 'chris.boden@noosa.qld.gov.au'
):
    """
    Execute the email sending operation with the Hub's template.

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        html_body: Main content of the email (can be plain text, will be formatted)
        body: Optional plain text version of the email
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        from_email: Optional sender email address (defaults to Hub's address)

    Returns:
        str: Success or error message

    Raises:
        ValueError: If ZAPIER_EMAIL_WEBHOOK_URL is not set
        Exception: If email sending fails
    """
    # Get Zapier webhook URL from environment variable
    webhook_url = os.getenv('ZAPIER_EMAIL_WEBHOOK_URL')
    # Only show start of URL for security
    print(f"Using webhook URL: {webhook_url[:20]}...")

    if not webhook_url:
        raise ValueError(
            "ZAPIER_EMAIL_WEBHOOK_URL is not set in environment variables")

    # Apply the template to the HTML body
    print("Applying template to HTML body...")
    final_html = apply_template(subject, html_body)

    # Prepare payload with templated html_body
    print("Preparing email payload...")
    payload = {
        'to': to,
        'subject': subject,
        'html_body': final_html
    }

    # Add plain text body if provided, or use html_body stripped of HTML
    if body:
        payload['body'] = body
    else:
        # Use the original html_body as plain text fallback
        payload['body'] = html_body

    # Add optional fields if provided
    if cc:
        payload['cc'] = cc
        print(f"Adding CC recipients: {cc}")
    if bcc:
        payload['bcc'] = bcc
        print(f"Adding BCC recipients: {bcc}")
    if from_email:
        payload['from_email'] = from_email
        print(f"Setting from email: {from_email}")

    print(f"Final payload (excluding body content):")
    safe_payload = payload.copy()
    safe_payload['html_body'] = '...'
    safe_payload['body'] = '...'
    print(safe_payload)

    # Send the email via webhook
    try:
        print("Sending request to Zapier webhook...")
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")

        # Check response
        if response.status_code == 200:
            return f"Successfully sent email: {subject}"
        else:
            return f"Failed to send email: {response.status_code} - {response.text}"

    except Exception as e:
        print(f"Exception while sending email: {str(e)}")
        return f"Error sending email: {str(e)}"


def send_email(
    to: Union[str, List[str]],
    subject: str,
    content: str,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    from_email: Optional[str] = None
):
    """
    Simplified function for sending an email with the Hub's template.

    This is the recommended way to send emails as it handles common cases
    and provides a simpler interface than the execute() function.

    Args:
        to: Single email address or list of recipient addresses
        subject: Email subject line
        content: Main content of the email (can be plain text)
        cc: Optional single email or list of CC recipients
        bcc: Optional single email or list of BCC recipients
        from_email: Optional sender email address

    Returns:
        str: Success or error message

    Example:
        result = send_email(
            to="john@example.com",
            subject="Hello",
            content="Hi John,\n\nGreat meeting you today!"
        )
        print(result)  # "Successfully sent email: Hello"
    """
    print("Starting send_email function...")

    # Convert single email strings to lists
    to_list = [to] if isinstance(to, str) else to
    cc_list = [cc] if cc and isinstance(cc, str) else cc
    bcc_list = [bcc] if bcc and isinstance(bcc, str) else bcc

    print(f"Recipients - To: {to_list}, CC: {cc_list}, BCC: {bcc_list}")

    try:
        result = execute(
            to=to_list,
            subject=subject,
            html_body=content,
            cc=cc_list,
            bcc=bcc_list,
            from_email=from_email
        )
        print(f"Execute result: {result}")
        return result
    except Exception as e:
        error_msg = f"Error in send_email: {str(e)}"
        print(error_msg)
        return error_msg


# Update Tool metadata for LLM integration
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
