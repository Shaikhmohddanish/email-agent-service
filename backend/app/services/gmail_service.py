import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_SCOPES, CC_EMAILS

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail API wrapper for sending and reading emails."""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        if os.path.exists(GMAIL_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                    logger.error(f"credentials.json not found at {GMAIL_CREDENTIALS_PATH}")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_PATH, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)

            with open(GMAIL_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        thread_id: Optional[str] = None,
        cc: Optional[list] = None,
    ) -> dict:
        """Send an HTML email, optionally as part of a thread."""
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['subject'] = subject

        if cc:
            message['cc'] = ', '.join(cc)

        # If replying to a thread, add In-Reply-To and References headers
        if thread_id:
            message['In-Reply-To'] = thread_id
            message['References'] = thread_id

        html_part = MIMEText(html_body, 'html')
        message.attach(html_part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw}

        if thread_id:
            body['threadId'] = thread_id

        try:
            sent = self.service.users().messages().send(userId='me', body=body).execute()
            logger.info(f"Email sent to {to}, message ID: {sent['id']}")
            return sent
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            raise

    def get_thread(self, thread_id: str) -> dict:
        """Get a Gmail thread by ID."""
        try:
            return self.service.users().threads().get(userId='me', id=thread_id).execute()
        except Exception as e:
            logger.error(f"Failed to get thread {thread_id}: {e}")
            raise

    def get_message(self, message_id: str) -> dict:
        """Get a Gmail message by ID."""
        try:
            return self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    def list_messages(self, query: str = "", max_results: int = 20) -> list:
        """List messages matching a query."""
        try:
            result = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            return result.get('messages', [])
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []

    def get_message_body(self, message: dict) -> str:
        """Extract plain text body from a message."""
        payload = message.get('payload', {})
        parts = payload.get('parts', [])

        if not parts:
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            return ''

        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        # Fallback to HTML
        for part in parts:
            if part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return ''

    def check_for_replies(self, gmail_thread_id: str, known_message_ids: list) -> list:
        """Check a thread for new messages not yet tracked."""
        try:
            thread = self.get_thread(gmail_thread_id)
            new_messages = []
            for msg in thread.get('messages', []):
                if msg['id'] not in known_message_ids:
                    full_msg = self.get_message(msg['id'])
                    body = self.get_message_body(full_msg)
                    headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                    new_messages.append({
                        'gmail_message_id': msg['id'],
                        'from': headers.get('From', ''),
                        'subject': headers.get('Subject', ''),
                        'body': body,
                        'date': headers.get('Date', ''),
                    })
            return new_messages
        except Exception as e:
            logger.error(f"Failed to check replies for thread {gmail_thread_id}: {e}")
            return []
