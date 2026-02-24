from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from models import db
from models.campaign import Campaign, CampaignLog
from utils.validators import check_spam_score

campaigns_bp = Blueprint('campaigns', __name__)

@campaigns_bp.route('/')
@login_required
def index():
    return render_template('campaigns_manage.html')

@campaigns_bp.route('/old')
@login_required
def old_index():
    return render_template('campaigns.html')

@campaigns_bp.route('/send')
@login_required
def send_page():
    return render_template('send_campaign.html')

@campaigns_bp.route('/wizard')
@login_required
def wizard():
    return render_template('campaign_wizard.html')

@campaigns_bp.route('/wizard/validate', methods=['POST'])
@login_required
def validate_wizard():
    from models.provider import ProviderConnection
    from models.recipient_list import RecipientList
    from models.template import EmailTemplate
    from models.suppression import SuppressionList
    from utils.validators import check_spam_score
    from datetime import date
    
    data = request.json
    provider_id = data.get('provider_id')
    list_id = data.get('list_id')
    template_id = data.get('template_id')
    subject = data.get('subject')
    html_body = data.get('html_body')
    text_body = data.get('text_body')
    
    errors = []
    warnings = []
    
    provider = ProviderConnection.query.filter_by(id=provider_id, user_id=current_user.id).first()
    if not provider:
        errors.append('Provider not found')
    elif not provider.is_verified:
        errors.append('Provider not verified')
    elif provider.health_status != 'healthy':
        warnings.append(f'Provider health: {provider.health_status}')
    
    recipient_list = RecipientList.query.filter_by(id=list_id, user_id=current_user.id).first()
    if not recipient_list:
        errors.append('Recipient list not found')
    elif recipient_list.recipient_count == 0:
        errors.append('Recipient list is empty')
    
    if template_id:
        template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if not template:
            errors.append('Template not found')
    
    if current_user.last_send_date == date.today():
        if current_user.daily_send_count >= current_user.send_limit:
            errors.append(f'Daily send limit reached ({current_user.send_limit})')
    
    if recipient_list and provider:
        if recipient_list.recipient_count > provider.rate_limit:
            warnings.append(f'Recipient count exceeds provider rate limit ({provider.rate_limit})')
    
    spam_result = check_spam_score(subject or '', text_body or html_body or '')
    if spam_result.get('is_spam'):
        warnings.append(f"Spam flags: {', '.join(spam_result.get('flags', []))}")
    
    return jsonify({
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    })

@campaigns_bp.route('/list')
@login_required
def list_campaigns():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).order_by(Campaign.created_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'subject': c.subject,
        'status': c.status,
        'total_recipients': c.total_recipients,
        'sent_count': c.sent_count,
        'failed_count': c.failed_count,
        'created_at': c.created_at.isoformat()
    } for c in campaigns])

@campaigns_bp.route('/create', methods=['POST'])
@login_required
def create_campaign():
    from models.recipient_list import RecipientList
    from datetime import date
    
    data = request.json
    
    recipient_list = RecipientList.query.filter_by(id=data['list_id'], user_id=current_user.id).first()
    if not recipient_list:
        return jsonify({'error': 'List not found'}), 404
    
    campaign = Campaign(
        user_id=current_user.id,
        provider_id=data['provider_id'],
        list_id=data['list_id'],
        template_id=data.get('template_id'),
        name=data['name'],
        subject=data['subject'],
        html_body=data.get('html_body'),
        text_body=data.get('text_body'),
        total_recipients=recipient_list.recipient_count,
        scheduled_at=data.get('scheduled_at')
    )
    
    db.session.add(campaign)
    
    if current_user.last_send_date != date.today():
        current_user.daily_send_count = 0
        current_user.last_send_date = date.today()
    
    db.session.commit()
    
    return jsonify({'success': True, 'id': campaign.id})

@campaigns_bp.route('/send-now', methods=['POST'])
@login_required
def send_now():
    """Send campaign immediately without queuing"""
    from models.provider import ProviderConnection
    from models.recipient_list import RecipientList, Recipient
    from models.template import EmailTemplate
    from services.provider_factory import ProviderFactory
    from services.template_engine import TemplateEngine
    from utils.crypto import CredentialEncryption
    from datetime import datetime, date
    import json
    
    data = request.json
    variable_mapping = data.get('variable_mapping', {})
    
    # Get resources
    provider = ProviderConnection.query.filter_by(id=data['provider_id'], user_id=current_user.id).first()
    if not provider or not provider.is_verified:
        return jsonify({'error': 'Provider not found or not verified'}), 404
    
    recipient_list = RecipientList.query.filter_by(id=data['list_id'], user_id=current_user.id).first()
    if not recipient_list:
        return jsonify({'error': 'List not found'}), 404
    
    template = EmailTemplate.query.filter_by(id=data['template_id'], user_id=current_user.id).first()
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Create campaign record
    campaign = Campaign(
        user_id=current_user.id,
        provider_id=provider.id,
        list_id=recipient_list.id,
        template_id=template.id,
        name=data['name'],
        subject=data['subject'],
        html_body=template.html_body,
        text_body=template.text_body,
        total_recipients=recipient_list.recipient_count,
        status='sending',
        started_at=datetime.utcnow()
    )
    db.session.add(campaign)
    db.session.commit()
    
    # Get provider instance
    crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
    credentials = json.loads(crypto.decrypt(provider.encrypted_credentials))
    provider_instance = ProviderFactory.create(provider.provider_type, credentials)
    
    # Send emails
    recipients = Recipient.query.filter_by(list_id=recipient_list.id).all()
    sent = 0
    failed = 0
    
    for recipient in recipients:
        try:
            # Build variables dict based on mapping
            variables = {}
            
            # Always include email
            variables['email'] = recipient.email
            
            # Map variables based on configuration
            for var_name, mapping in variable_mapping.items():
                if mapping['type'] == 'field':
                    # Get value from recipient data
                    field_name = mapping['value']
                    if field_name == 'email':
                        variables[var_name] = recipient.email
                    elif field_name == 'name':
                        variables[var_name] = recipient.data.get('name', '') if recipient.data else ''
                    elif recipient.data and field_name in recipient.data:
                        variables[var_name] = recipient.data[field_name]
                    else:
                        variables[var_name] = ''
                elif mapping['type'] == 'custom':
                    # Use custom value
                    variables[var_name] = mapping['value']
            
            subject = TemplateEngine.render(data['subject'], variables)
            html_body = TemplateEngine.render(template.html_body, variables)
            text_body = TemplateEngine.render(template.text_body, variables) if template.text_body else TemplateEngine.html_to_text(html_body)
            
            result = provider_instance.send(
                from_email=provider.sender_email,
                to_email=recipient.email,
                subject=subject,
                html_body=html_body,
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
                
        except Exception as e:
            failed += 1
            log = CampaignLog(
                campaign_id=campaign.id,
                recipient_email=recipient.email,
                status='failed',
                error_message=str(e)
            )
            db.session.add(log)
    
    # Update campaign
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.status = 'completed'
    campaign.completed_at = datetime.utcnow()
    
    # Update user send count
    if current_user.last_send_date != date.today():
        current_user.daily_send_count = 0
        current_user.last_send_date = date.today()
    current_user.daily_send_count += sent
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'campaign_id': campaign.id,
        'sent': sent,
        'failed': failed
    })

@campaigns_bp.route('/<int:campaign_id>/send', methods=['POST'])
@login_required
def send(campaign_id):
    from services.sending_queue import SendingQueue
    from datetime import datetime, date
    
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first()
    if not campaign:
        return jsonify({'error': 'Not found'}), 404
    
    if campaign.status not in ['draft', 'failed']:
        return jsonify({'error': 'Campaign already sent or in progress'}), 400
    
    if current_user.last_send_date == date.today():
        if current_user.daily_send_count + campaign.total_recipients > current_user.send_limit:
            return jsonify({'error': 'Daily send limit exceeded'}), 400
    
    campaign.status = 'queued'
    campaign.started_at = datetime.utcnow()
    db.session.commit()
    
    try:
        SendingQueue.enqueue(campaign.id)
        return jsonify({'success': True, 'message': 'Campaign queued for sending'})
    except Exception as e:
        campaign.status = 'failed'
        db.session.commit()
        return jsonify({'error': str(e)}), 500

@campaigns_bp.route('/<int:campaign_id>')
@login_required
def get_campaign(campaign_id):
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first()
    if not campaign:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': campaign.id,
        'name': campaign.name,
        'subject': campaign.subject,
        'status': campaign.status,
        'total_recipients': campaign.total_recipients,
        'sent_count': campaign.sent_count,
        'failed_count': campaign.failed_count,
        'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
        'started_at': campaign.started_at.isoformat() if campaign.started_at else None,
        'completed_at': campaign.completed_at.isoformat() if campaign.completed_at else None
    })

@campaigns_bp.route('/<int:campaign_id>/logs')
@login_required
def get_logs(campaign_id):
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first()
    if not campaign:
        return jsonify({'error': 'Not found'}), 404
    
    logs = CampaignLog.query.filter_by(campaign_id=campaign_id).order_by(CampaignLog.sent_at.desc()).limit(100).all()
    
    return jsonify([{
        'recipient_email': l.recipient_email,
        'status': l.status,
        'error_message': l.error_message,
        'sent_at': l.sent_at.isoformat()
    } for l in logs])
