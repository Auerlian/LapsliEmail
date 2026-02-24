from providers.base import BaseProvider
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SMTPProvider(BaseProvider):
    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.host = credentials['host']
        self.port = credentials['port']
        self.username = credentials['username']
        self.password = credentials['password']
    
    def send(self, from_email: str, to_email: str, subject: str, html_body: str, text_body: str = None) -> dict:
        try:
            message = MIMEMultipart('alternative')
            message['From'] = from_email
            message['To'] = to_email
            message['Subject'] = subject
            
            if text_body:
                message.attach(MIMEText(text_body, 'plain'))
            message.attach(MIMEText(html_body, 'html'))
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=60) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(from_email, to_email, message.as_string())
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify(self) -> dict:
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_rate_limit(self) -> int:
        return 100
