from ai_core.tools import tool
import json
import os

# Lazy initialization - client is created only when needed
_gmail_client = None
_gmail_error = None

def get_gmail_client():
    """Get or create the Gmail client. Returns (client, error_message)."""
    global _gmail_client, _gmail_error
    
    if _gmail_client is not None:
        return _gmail_client, None
    
    if _gmail_error is not None:
        return None, _gmail_error
    
    # Check if credentials exist
    if not os.path.exists('credentials.json') and not os.path.exists('token.pickle'):
        _gmail_error = (
            "Gmail integration not configured. To use Gmail tools:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project and enable the Gmail API\n"
            "3. Create OAuth 2.0 credentials and download as 'credentials.json'\n"
            "4. Place credentials.json in the obsidian_ai directory"
        )
        return None, _gmail_error
    
    try:
        from integrations.gmail_client import GmailClient
        _gmail_client = GmailClient()
        return _gmail_client, None
    except Exception as e:
        _gmail_error = f"Failed to initialize Gmail client: {str(e)}"
        return None, _gmail_error


@tool(
    description="Send an email through Gmail. This tool allows sending plain text emails to specified recipients. "
                "It handles the email composition and sending process through the authenticated Gmail account. "
                "The email can be sent from any authorized address including Google Groups. "
                "Multiple recipients and CC addresses can be specified using comma-separated values.",
    to="The recipient's email address(es), comma-separated for multiple recipients",
    cc="Optional CC recipient(s), comma-separated for multiple CC addresses",
    subject="The subject line of the email",
    body="The html content of the email message (make sure to use <br> for line breaks)",
    from_name="Optional display name for the sender",
    from_email="Optional sender email address (must have permission to send as this address)",
    safe=False
)
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = None,
    from_name: str = None,
    from_email: str = None
) -> str:
    """Sends an email through Gmail"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    # Split recipients by comma and strip whitespace
    to_list = [email.strip() for email in to.split(',') if email.strip()]
    cc_list = [email.strip() for email in cc.split(',')] if cc else None
    
    result = client.send_email(
        to=to_list,
        subject=subject,
        body=body,
        cc=cc_list,
        from_name=from_name,
        from_email=from_email
    )
    return json.dumps(result)

@tool(
    description="Search for emails in Gmail using various filters. This tool provides a powerful way to search through "
                "your Gmail inbox using multiple criteria. You can combine different search parameters to narrow down "
                "results. The search is performed on the authenticated Gmail account. Results are limited to prevent "
                "overwhelming responses.",
    sender="Optional email address to filter messages from a specific sender",
    subject="Optional keyword or phrase to filter messages by subject",
    is_unread="If True, only show unread messages",
    has_attachment="If True, only show messages with attachments",
    from_date="Optional date to filter messages after (format: YYYY/MM/DD)",
    to_date="Optional date to filter messages before (format: YYYY/MM/DD)",
    max_results="Maximum number of messages to return (default: 10)",
    safe=True
)
def search_emails(
    sender: str = None,
    subject: str = None,
    is_unread: bool = False,
    has_attachment: bool = False,
    from_date: str = None,
    to_date: str = None,
    max_results: int = 10
) -> str:
    """Searches for emails using various filters"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    from integrations.gmail_client import filter_email_data, process_gmail_message
    results = client.search_emails(
        sender=sender,
        subject=subject,
        is_unread=is_unread,
        has_attachment=has_attachment,
        from_date=from_date,
        to_date=to_date,
        max_results=max_results
    )
    return json.dumps(results)

@tool(
    description="Retrieve the full content and details of a specific email message. This tool fetches comprehensive "
                "information about an email including headers, body, and metadata. Use this after finding message IDs "
                "through the search_emails tool to get complete message details.",
    message_id="The unique ID of the email message to retrieve (obtained from search results)",
    simplified="If True, the email content will be decoded and simplified to a single string",
    safe=True
)
def get_email_content(message_id: str, simplified: bool = True) -> str:
    """Gets the full content of a specific email"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    from integrations.gmail_client import filter_email_data, process_gmail_message
    message = client.get_email(message_id)
    if simplified:
        message = process_gmail_message(message)
        message = filter_email_data(message)
    return json.dumps(message)

@tool(
    description="List recent emails from your Gmail inbox. This tool provides a simple way to fetch recent messages "
                "with optional filtering by labels and search query. It's useful for getting a quick overview of "
                "recent messages or finding specific messages using Gmail's search syntax.",
    query="Optional Gmail search query (e.g., 'is:unread', 'subject:Hello')",
    label_ids="Optional list of Gmail label IDs to filter by (e.g., ['INBOX'])",
    max_results="Maximum number of messages to return (default: 10)",
    safe=True
)
def list_recent_emails(
    query: str = '',
    label_ids: str = None,
    max_results: int = 10,
) -> str:
    """Lists recent emails with optional filtering"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    if label_ids:
        label_ids = json.loads(label_ids)
    messages = client.list_emails(
        query=query,
        label_ids=label_ids,
        max_results=max_results
    )
    return json.dumps(messages)

@tool(
    description="List all attachments in an email without downloading them. This is useful to see what attachments "
                "are available before deciding which ones to download. Returns information about each attachment "
                "including filename, size, and MIME type.",
    message_id="The unique ID of the email message to check for attachments (obtained from search results)",
    safe=True
)
def list_email_attachments(message_id: str) -> str:
    """Lists all attachments in a specific email"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    attachments = client.list_attachments(message_id)
    return json.dumps({
        "message_id": message_id,
        "attachment_count": len(attachments),
        "attachments": attachments
    })

@tool(
    description="Reply to an existing email, keeping the conversation in the same thread. This tool allows you to "
                "respond to an email while maintaining the email thread structure. The reply will automatically "
                "include proper threading headers (In-Reply-To, References) and will appear in the same conversation "
                "thread in Gmail. You MUST explicitly specify the recipient(s) in the 'to' parameter - check the "
                "original email's 'From' field to find the sender's address to reply to.",
    message_id="The unique ID of the email message to reply to (obtained from search results or get_email_content)",
    to="The recipient's email address(es) to send the reply to, comma-separated for multiple recipients. "
       "This must be explicitly specified - typically the original sender's email from the 'From' field.",
    body="The HTML content of the reply message (use <br> for line breaks)",
    cc="Optional CC recipient(s), comma-separated for multiple CC addresses",
    from_name="Optional display name for the sender",
    from_email="Optional sender email address (must have permission to send as this address)",
    safe=False
)
def reply_to_email(
    message_id: str,
    to: str,
    body: str,
    cc: str = None,
    from_name: str = None,
    from_email: str = None
) -> str:
    """Replies to an existing email in the same thread"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    # Split recipients by comma and strip whitespace
    to_list = [email.strip() for email in to.split(',') if email.strip()]
    
    # Split CC by comma and strip whitespace if provided
    cc_list = [email.strip() for email in cc.split(',')] if cc else None
    
    result = client.reply_to_email(
        message_id=message_id,
        to=to_list,
        body=body,
        cc=cc_list,
        from_name=from_name,
        from_email=from_email
    )
    return json.dumps(result)

@tool(
    description="Download specific attachments from an email to a specified folder. Use list_email_attachments first "
                "to see available attachments and their filenames. Creates the folder if it doesn't exist. "
                "If a file with the same name already exists, a number suffix will be added to avoid overwriting. "
                "Returns details about each downloaded file including the final path and any errors encountered.",
    message_id="The unique ID of the email message to download attachments from (obtained from search results)",
    download_path="The folder path where attachments should be saved (e.g., '/Users/me/Downloads/email_attachments')",
    filenames="JSON array of attachment filenames to download (e.g., '[\"report.pdf\", \"data.xlsx\"]'). Use list_email_attachments to see available filenames.",
    safe=False
)
def download_email_attachments(message_id: str, download_path: str, filenames: str) -> str:
    """Downloads specific attachments from an email to a folder"""
    client, error = get_gmail_client()
    if error:
        return json.dumps({"error": error})
    
    # Parse the filenames list
    try:
        filenames_list = json.loads(filenames)
        if not isinstance(filenames_list, list):
            return json.dumps({"error": "filenames must be a JSON array of strings"})
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON for filenames: {str(e)}"})
    
    # Expand user home directory if path starts with ~
    download_path = os.path.expanduser(download_path)
    
    results = client.download_attachments(message_id, download_path, filenames_list)
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    return json.dumps({
        "message_id": message_id,
        "download_path": download_path,
        "requested_files": filenames_list,
        "successful_downloads": successful,
        "failed_downloads": failed,
        "files": results
    })

# Export the tools
TOOLS = [
    send_email,
    reply_to_email,
    search_emails,
    get_email_content,
    list_recent_emails,
    list_email_attachments,
    download_email_attachments
]
