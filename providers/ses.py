from providers.base import BaseProvider
import boto3
from botocore.exceptions import ClientError

class SESProvider(BaseProvider):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.client = boto3.client(
            'ses',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials.get('region', 'us-east-1')
        )
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            response = self.client.send_email(
                Source=from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Text': {'Data': text_body or ''},
                        'Html': {'Data': html_body}
                    }
                }
            )
            
            return {'success': True, 'message_id': response['MessageId']}
        except ClientError as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            response = self.client.get_send_quota()
            return {'success': True, 'quota': response}
        except ClientError as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 14
