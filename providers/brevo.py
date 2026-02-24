from providers.base import BaseProvider
import requests

class BrevoProvider(BaseProvider):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials['api_key']
        self.base_url = 'https://api.brevo.com/v3'
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            payload = {
                'sender': {'email': from_email},
                'to': [{'email': to_email}],
                'subject': subject,
                'htmlContent': html_body,
                'textContent': text_body or ''
            }
            
            response = requests.post(
                f'{self.base_url}/smtp/email',
                json=payload,
                headers={'api-key': self.api_key},
                timeout=30
            )
            
            if response.status_code == 201:
                return {'success': True, 'message_id': response.json().get('messageId')}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            response = requests.get(
                f'{self.base_url}/account',
                headers={'api-key': self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                return {'success': True}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 300
