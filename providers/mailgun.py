from providers.base import BaseProvider
import requests

class MailgunProvider(BaseProvider):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.api_key = credentials['api_key']
        self.domain = credentials['domain']
        self.base_url = f'https://api.mailgun.net/v3/{self.domain}'
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            response = requests.post(
                f'{self.base_url}/messages',
                auth=('api', self.api_key),
                data={
                    'from': from_email,
                    'to': to_email,
                    'subject': subject,
                    'text': text_body or '',
                    'html': html_body
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {'success': True, 'message_id': response.json().get('id')}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            response = requests.get(
                f'{self.base_url}/domains/{self.domain}',
                auth=('api', self.api_key),
                timeout=10
            )
            if response.status_code == 200:
                return {'success': True}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 1000
