# gmail_client.py

import os
import pickle
import base64

from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import quopri

from config.logging_config import setup_logger
from config.services_config import GOOGLE_SCOPES

logger = setup_logger(__name__)

# Top level fields to keep
ESSENTIAL_EMAIL_FIELDS = {
    'id',
    'threadId',
    'labelIds',
    'snippet',
    'simplified_content'
}

# Essential headers to keep
ESSENTIAL_HEADERS = {
    'From',
    'To',
    'Subject',
    'Date',
    'Reply-to'
}

def process_gmail_message(message):
    """
    Process a Gmail API message by:
    1. Extracting and decoding the content into simplified_content
    2. Removing base64 data to clean up the structure
    """
    def decode_content(part):
        """Helper function to decode message content"""
        if 'data' not in part.get('body', {}):
            return ''
        
        data = part['body']['data']
        decoded_bytes = base64.urlsafe_b64decode(data)
        
        # Handle different content transfer encodings
        if 'headers' in part:
            for header in part['headers']:
                if header['name'].lower() == 'content-transfer-encoding':
                    if header['value'].lower() == 'quoted-printable':
                        decoded_bytes = quopri.decodestring(decoded_bytes)
                    break
        
        try:
            return decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return decoded_bytes.decode('iso-8859-1')

    def extract_plain_text(payload):
        """Extract plain text content from payload"""
        if payload.get('mimeType') == 'text/plain':
            return decode_content(payload)
        
        if payload.get('mimeType') == 'multipart/alternative':
            parts = payload.get('parts', [])
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    return decode_content(part)
            if parts:
                return decode_content(parts[0])
        return ''

    def clean_part(part):
        """Clean a message part by removing body data"""
        cleaned_part = part.copy()
        if 'body' in cleaned_part:
            body = cleaned_part['body'].copy()
            if 'data' in body:
                del body['data']
            cleaned_part['body'] = body
        return cleaned_part

    # Create a copy of the original message
    processed_message = message.copy()
    
    # Add simplified content
    if 'payload' in message:
        processed_message['simplified_content'] = extract_plain_text(message['payload'])
    
    # Clean the payload
    if 'payload' in processed_message:
        payload = processed_message['payload']
        
        # Clean main body
        if 'body' in payload:
            body = payload['body'].copy()
            if 'data' in body:
                del body['data']
            payload['body'] = body
            
        # Clean parts
        if 'parts' in payload:
            payload['parts'] = [clean_part(part) for part in payload['parts']]
        
        processed_message['payload'] = payload

    return processed_message

def filter_email_data(raw_email):
    # Initialize filtered result
    filtered = {}
    
    # First level filtering
    for field in ESSENTIAL_EMAIL_FIELDS:
        if field in raw_email:
            filtered[field] = raw_email[field]
    
    # Handle payload and headers specially
    if 'payload' in raw_email:
        filtered['headers'] = {}
        headers = raw_email['payload'].get('headers', [])
        
        # Filter only essential headers
        filtered['headers'] = {
            header['name']: header['value']
            for header in headers
            if header['name'] in ESSENTIAL_HEADERS
        }
    
    return filtered

def simplify_gmail_message(message):
    """
    Process a Gmail API message to simplify its content structure.
    Keeps all original fields but adds a 'simplified_content' field with plain text content.
    """
    def decode_content(part):
        """Helper function to decode message content"""
        if 'data' not in part.get('body', {}):
            return ''
        
        # Get the content data
        data = part['body']['data']
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(data)
        
        # Handle different content transfer encodings
        if 'headers' in part:
            for header in part['headers']:
                if header['name'].lower() == 'content-transfer-encoding':
                    if header['value'].lower() == 'quoted-printable':
                        decoded_bytes = quopri.decodestring(decoded_bytes)
                    break
        
        # Try to decode as UTF-8, fallback to ISO-8859-1 if needed
        try:
            return decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return decoded_bytes.decode('iso-8859-1')

    def extract_plain_text(payload):
        """Extract plain text content from payload"""
        if payload.get('mimeType') == 'text/plain':
            return decode_content(payload)
        
        if payload.get('mimeType') == 'multipart/alternative':
            parts = payload.get('parts', [])
            # Look for text/plain part first
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    return decode_content(part)
            # Fallback to first part if no text/plain
            if parts:
                return decode_content(parts[0])
        
        return ''

    # Create a copy of the original message
    processed_message = message.copy()
    
    # Add simplified content while keeping original payload
    if 'payload' in message:
        processed_message['simplified_content'] = extract_plain_text(message['payload'])
    
    return processed_message

class GmailClient:
    def __init__(self,
                 credentials_path='credentials.json',
                 token_path='token.pickle',
                 scopes=None):
        """
        :param credentials_path: Path to your downloaded OAuth credentials JSON file.
        :param token_path: Path to store the OAuth token (pickle).
        :param scopes: List of Gmail API scopes you need.
        """
        # Add groups scope alongside mail scope
        self.scopes = scopes or GOOGLE_SCOPES
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None

        # Try loading existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token_file:
                creds = pickle.load(token_file)

        # If no valid credentials, prompt user login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )
                creds = flow.run_local_server(port=0)

            # Save new token for future runs
            with open(self.token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)

        return build('gmail', 'v1', credentials=creds)

    def send_email(self, to, subject, body, cc=None, from_name=None, from_email=None):
        """
        Send a plain-text email.
        :param to: List of recipient email addresses or single address
        :param subject: Email subject
        :param body: Plain-text message content
        :param cc: List of CC recipient email addresses or single address (optional)
        :param from_name: Display name for the sender (optional)
        :param from_email: Sender email address (optional, must have permission)
        :return: API response dict containing message ID, etc.
        """
        # Create a simple message without any policy
        message = MIMEText(body, 'html')
        
        # Handle to recipients (convert to comma-separated string if list)
        if isinstance(to, list):
            message['to'] = ', '.join(to)
        else:
            message['to'] = to

        # Handle CC recipients if provided
        if cc:
            if isinstance(cc, list):
                message['cc'] = ', '.join(cc)
            else:
                message['cc'] = cc

        # Set the subject
        message['subject'] = subject
        
        # Use provided from_email if available, otherwise get user's email
        if from_email:
            sender_email = from_email
        else:
            sender_info = self.service.users().getProfile(userId='me').execute()
            sender_email = sender_info['emailAddress']
        
        # Set the From header with display name if provided
        if from_name:
            message['from'] = f"{from_name} <{sender_email}>"
        else:
            message['from'] = sender_email

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body = {'raw': raw_message}

        sent_message = self.service.users().messages().send(
            userId='me', 
            body=send_body
        ).execute()
        return sent_message

    def list_emails(self, query='', label_ids=None, max_results=10):
        """
        List emails in your mailbox.
        :param query: Search query (e.g. 'is:unread', 'subject:Hello')
        :param label_ids: List of label IDs (e.g. ['INBOX'])
        :param max_results: How many messages to return
        :return: List of messages (each is a dict with at least an 'id')
        """
        if label_ids is None:
            label_ids = []

        response = self.service.users().messages().list(
            userId='me',
            q=query,
            labelIds=label_ids,
            maxResults=max_results,
        ).execute()

        messages = response.get('messages', [])
        results = []

        # 2) For each message, call messages().get with format='metadata' to grab its Subject.
        for msg in messages:
            msg_id = msg['id']
            detail = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Cc']
            ).execute()

            # Extract the relevant headers
            subject, from_addr, to_addr, cc_addr = None, None, None, None
            headers = detail.get('payload', {}).get('headers', [])
            for h in headers:
                name_lower = h['name'].lower()
                value = h['value']
                if name_lower == 'subject':
                    subject = h['value']
                elif name_lower == 'from':
                    from_addr = value
                elif name_lower == 'to':
                    to_addr = value
                elif name_lower == 'cc':
                    cc_addr = value

            results.append({
                'id': msg_id,
                'threadId': msg.get('threadId'),
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'cc': cc_addr,
            })

        return results

    def get_email(self, message_id):
        """
        Retrieve a full email by ID (with headers, body, etc.).
        :param message_id: The ID of the message to retrieve
        :return: A dict with detailed message data
        """
        message = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        return message
    
    def search_emails(
    self,
    sender=None,
    subject=None,
    is_unread=False,
    has_attachment=False,
    from_date=None,
    to_date=None,
    label_ids=None,
    max_results=10
    ):
        """
        Search emails based on multiple optional parameters.

        :param sender: Filter by sender email address (e.g. 'someone@example.com')
        :param subject: Filter by subject keyword/phrase (e.g. 'Meeting')
        :param is_unread: If True, only show unread messages (adds 'is:unread')
        :param has_attachment: If True, only show messages that have attachments
        :param from_date: Limit results to messages after this date (format: 'YYYY/MM/DD')
        :param to_date: Limit results to messages before this date (format: 'YYYY/MM/DD')
        :param label_ids: List of label IDs to filter by (e.g. ['INBOX', 'Label_123'])
        :param max_results: Maximum number of messages to retrieve
        :return: A list of message dicts, each containing 'id' and 'threadId'
        """
        # Build query string from the provided parameters
        conditions = []

        if sender:
            conditions.append(f"from:{sender}")
        if subject:
            conditions.append(f"subject:{subject}")
        if is_unread:
            conditions.append("is:unread")
        if has_attachment:
            conditions.append("has:attachment")
        if from_date:
            # Gmail uses after:YYYY/MM/DD (messages after this date)
            conditions.append(f"after:{from_date}")
        if to_date:
            # Gmail uses before:YYYY/MM/DD (messages before this date)
            conditions.append(f"before:{to_date}")

        query_str = " ".join(conditions)

        if label_ids is None:
            label_ids = []

        return self.list_emails(query=query_str, label_ids=label_ids, max_results=max_results)

    def list_attachments(self, message_id):
        """
        List all attachments in an email without downloading them.
        
        :param message_id: The ID of the message to check for attachments
        :return: A list of dicts with attachment info (id, filename, mimeType, size)
        """
        message = self.get_email(message_id)
        attachments = []
        
        def find_attachments(parts):
            """Recursively find attachments in message parts"""
            for part in parts:
                filename = part.get('filename', '')
                if filename:
                    attachment_info = {
                        'id': part['body'].get('attachmentId'),
                        'filename': filename,
                        'mimeType': part.get('mimeType', 'application/octet-stream'),
                        'size': part['body'].get('size', 0)
                    }
                    attachments.append(attachment_info)
                # Check nested parts
                if 'parts' in part:
                    find_attachments(part['parts'])
        
        payload = message.get('payload', {})
        if 'parts' in payload:
            find_attachments(payload['parts'])
        
        return attachments

    def download_attachment(self, message_id, attachment_id, filename, download_path):
        """
        Download a single attachment from an email.
        
        :param message_id: The ID of the message containing the attachment
        :param attachment_id: The ID of the attachment to download
        :param filename: The filename to save the attachment as
        :param download_path: The directory path to save the attachment to
        :return: The full path to the downloaded file
        """
        # Get the attachment data
        attachment = self.service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        # Decode the attachment data
        data = attachment.get('data', '')
        file_data = base64.urlsafe_b64decode(data)
        
        # Ensure download directory exists
        os.makedirs(download_path, exist_ok=True)
        
        # Create the full file path
        file_path = os.path.join(download_path, filename)
        
        # Handle filename conflicts by adding a number suffix
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(download_path, f"{base_name}_{counter}{ext}")
            counter += 1
        
        # Write the file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Downloaded attachment: {file_path}")
        return file_path

    def download_attachments(self, message_id, download_path, filenames):
        """
        Download specific attachments from an email by filename.
        
        :param message_id: The ID of the message to download attachments from
        :param download_path: The directory path to save attachments to
        :param filenames: List of filenames to download
        :return: A list of dicts with download results (filename, path, size, success)
        """
        attachments = self.list_attachments(message_id)
        results = []
        
        # Create a lookup dict for quick access
        attachment_lookup = {att['filename']: att for att in attachments}
        
        for filename in filenames:
            if filename not in attachment_lookup:
                results.append({
                    'filename': filename,
                    'path': None,
                    'size': 0,
                    'success': False,
                    'error': f'Attachment not found in email'
                })
                continue
            
            attachment = attachment_lookup[filename]
            try:
                if attachment['id']:
                    file_path = self.download_attachment(
                        message_id=message_id,
                        attachment_id=attachment['id'],
                        filename=attachment['filename'],
                        download_path=download_path
                    )
                    results.append({
                        'filename': attachment['filename'],
                        'path': file_path,
                        'size': attachment['size'],
                        'success': True
                    })
                else:
                    # Inline attachments without an attachmentId (embedded in body)
                    results.append({
                        'filename': attachment['filename'],
                        'path': None,
                        'size': attachment['size'],
                        'success': False,
                        'error': 'Inline attachment cannot be downloaded separately'
                    })
            except Exception as e:
                logger.error(f"Failed to download attachment {attachment['filename']}: {e}")
                results.append({
                    'filename': attachment['filename'],
                    'path': None,
                    'size': attachment['size'],
                    'success': False,
                    'error': str(e)
                })
        
        return results


if __name__ == '__main__':
    # Example usage
    client = GmailClient()

    # Send an email
    response = client.send_email(
        to='fournes.maxime@gmail.com',
        subject='Hello from Python!',
        body='This is a test email.',
        cc=['cc_recipient@example.com']
    )
    print("Email sent:", response)

    # List some emails
    emails = client.list_emails(query='is:unread', max_results=5)
    print("Emails found:", emails)

    # Fetch first email if there is one
    if emails:
        msg_id = emails[0]['id']
        full_msg = client.get_email(msg_id)
        print("Fetched email details:", full_msg)
