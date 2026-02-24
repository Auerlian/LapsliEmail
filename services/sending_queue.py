from models import db
from models.campaign import Campaign, CampaignLog
from models.recipient_list import Recipient
from models.provider import ProviderConnection
from models.user import User
from services.provider_factory import ProviderFactory
from services.template_engine import TemplateEngine
from utils.crypto import CredentialEncryption
from flask import current_app
import json
import time
from datetime import datetime, date

class SendingQueue:
    @staticmethod
    def enqueue(campaign_id: int):
        from threading import Thread
        thread = Thread(target=SendingQueue._process_campaign, args=(campaign_id,))
        thread.daemon = True
        thread.start()
    
    @staticmethod
    def _process_campaign(campaign_id: int):
        from app_production import app
        
        with app.app_context():
            campaign = Campaign.query.get(campaign_id)
            if not campaign:
                return
            
            try:
                campaign.status = 'sending'
                db.session.commit()
                
                provider = ProviderConnection.query.get(campaign.provider_id)
                user = User.query.get(campaign.user_id)
                
                crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
                credentials = json.loads(crypto.decrypt(provider.encrypted_credentials))
                
                provider_instance = ProviderFactory.create(provider.provider_type, credentials)
                
                recipients = Recipient.query.filter_by(list_id=campaign.list_id).all()
                
                sent = 0
                failed = 0
                
                for recipient in recipients:
                    variables = recipient.data or {}
                    variables['email'] = recipient.email
                    
                    subject = TemplateEngine.render(campaign.subject, variables)
                    html_body = TemplateEngine.render(campaign.html_body, variables) if campaign.html_body else None
                    text_body = TemplateEngine.render(campaign.text_body, variables) if campaign.text_body else None
                    
                    if not text_body and html_body:
                        text_body = TemplateEngine.html_to_text(html_body)
                    
                    result = provider_instance.send(
                        from_email=provider.sender_email,
                        to_email=recipient.email,
                        subject=subject,
                        html_body=html_body or text_body,
                        text_body=text_body
                    )
                    
                    log = CampaignLog(
                        campaign_id=campaign.id,
                        recipient_email=recipient.email,
                        status='sent' if result['success'] else 'failed',
                        error_message=result.get('error')
                    )
                    db.session.add(log)
                    
                    if result['success']:
                        sent += 1
                    else:
                        failed += 1
                    
                    time.sleep(1.0 / provider.rate_limit * 60)
                
                campaign.sent_count = sent
                campaign.failed_count = failed
                campaign.status = 'completed'
                campaign.completed_at = datetime.utcnow()
                
                if user.last_send_date != date.today():
                    user.daily_send_count = 0
                    user.last_send_date = date.today()
                
                user.daily_send_count += sent
                
                db.session.commit()
                
            except Exception as e:
                campaign.status = 'failed'
                db.session.commit()
