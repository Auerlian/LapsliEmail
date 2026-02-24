from providers.gmail import GmailProvider
from providers.brevo import BrevoProvider
from providers.sendgrid import SendGridProvider
from providers.mailgun import MailgunProvider
from providers.ses import SESProvider
from providers.smtp import SMTPProvider

class ProviderFactory:
    @staticmethod
    def create(provider_type: str, credentials: dict):
        providers = {
            'gmail': GmailProvider,
            'brevo': BrevoProvider,
            'sendgrid': SendGridProvider,
            'mailgun': MailgunProvider,
            'ses': SESProvider,
            'smtp': SMTPProvider
        }
        
        provider_class = providers.get(provider_type)
        if not provider_class:
            raise ValueError(f'Unknown provider: {provider_type}')
        
        return provider_class(credentials)
    
    @staticmethod
    def get_credential_schema(provider_type: str) -> dict:
        schemas = {
            'gmail': {
                'fields': [
                    {'name': 'access_token', 'type': 'hidden'},
                    {'name': 'refresh_token', 'type': 'hidden'},
                    {'name': 'client_id', 'type': 'hidden'},
                    {'name': 'client_secret', 'type': 'hidden'}
                ],
                'oauth': True
            },
            'brevo': {
                'fields': [
                    {'name': 'api_key', 'type': 'password', 'label': 'API Key', 'required': True}
                ]
            },
            'sendgrid': {
                'fields': [
                    {'name': 'api_key', 'type': 'password', 'label': 'API Key', 'required': True}
                ]
            },
            'mailgun': {
                'fields': [
                    {'name': 'api_key', 'type': 'password', 'label': 'API Key', 'required': True},
                    {'name': 'domain', 'type': 'text', 'label': 'Domain', 'required': True}
                ]
            },
            'ses': {
                'fields': [
                    {'name': 'access_key', 'type': 'password', 'label': 'Access Key', 'required': True},
                    {'name': 'secret_key', 'type': 'password', 'label': 'Secret Key', 'required': True},
                    {'name': 'region', 'type': 'text', 'label': 'Region', 'required': True, 'default': 'us-east-1'}
                ]
            },
            'smtp': {
                'fields': [
                    {'name': 'host', 'type': 'text', 'label': 'SMTP Host', 'required': True},
                    {'name': 'port', 'type': 'number', 'label': 'Port', 'required': True, 'default': 587},
                    {'name': 'username', 'type': 'text', 'label': 'Username', 'required': True},
                    {'name': 'password', 'type': 'password', 'label': 'Password', 'required': True}
                ]
            }
        }
        
        return schemas.get(provider_type, {'fields': []})
