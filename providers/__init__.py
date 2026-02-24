from providers.gmail import GmailProvider
from providers.sendgrid import SendGridProvider
from providers.brevo import BrevoProvider
from providers.mailgun import MailgunProvider
from providers.ses import SESProvider
from providers.smtp import SMTPProvider

PROVIDER_MAP = {
    'gmail': GmailProvider,
    'sendgrid': SendGridProvider,
    'brevo': BrevoProvider,
    'mailgun': MailgunProvider,
    'ses': SESProvider,
    'smtp': SMTPProvider
}

def get_provider(provider_type: str, credentials: dict):
    provider_class = PROVIDER_MAP.get(provider_type)
    if not provider_class:
        raise ValueError(f'Unknown provider: {provider_type}')
    return provider_class(credentials)
