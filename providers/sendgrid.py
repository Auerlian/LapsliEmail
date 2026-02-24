from providers.base import BaseProvider
import requests

class SendGridProvider(BaseProvider):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials['api_key']
        self.base_url = 'https://api.sendgrid.com/v3'
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            payload = {
                'personalizations': [{'to': [{'email': to_email}]}],
                'from': {'email': from_email},
                'subject': subject,
                'content': [
                    {'type': 'text/plain', 'value': text_body or ''},
                    {'type': 'text/html', 'value': html_body}
                ]
            }
            
            response = requests.post(
                f'{self.base_url}/mail/send',
                json=payload,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30
            )
            
            if response.status_code == 202:
                return {'success': True, 'message_id': response.headers.get('X-Message-Id')}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            response = requests.get(
                f'{self.base_url}/user/profile',
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=10
            )
            if response.status_code == 200:
                return {'success': True}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 100
