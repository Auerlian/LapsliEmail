from providers.base import BaseProvider
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

class GmailProvider(BaseProvider):
    def __init__(self, credentials: dict):
        self.credentials = Credentials(
            token=credentials.get('access_token'),
            refresh_token=credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=credentials.get('client_id'),
            client_secret=credentials.get('client_secret')
        )
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            
            message = MIMEText(html_body, 'html')
            message['to'] = to_email
            message['from'] = from_email
            message['subject'] = subject
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw}
            
            result = service.users().messages().send(userId='me', body=body).execute()
            return {'success': True, 'message_id': result['id']}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            profile = service.users().getProfile(userId='me').execute()
            return {'success': True, 'email': profile['emailAddress']}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 500
