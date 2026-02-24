from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user
from models.campaign import Campaign
from models.recipient_list import RecipientList
from models.provider import ProviderConnection
from datetime import date

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    providers = ProviderConnection.query.filter_by(user_id=current_user.id).all()
    campaigns = Campaign.query.filter_by(user_id=current_user.id).order_by(Campaign.created_at.desc()).limit(5).all()
    lists = RecipientList.query.filter_by(user_id=current_user.id).all()
    
    verified_count = sum(1 for p in providers if p.is_verified)
    total_recipients = sum(l.recipient_count for l in lists)
    active_campaigns = sum(1 for c in campaigns if c.status in ['sending', 'queued'])
    
    remaining_sends = current_user.send_limit - (current_user.daily_send_count or 0)
    if current_user.last_send_date != date.today():
        remaining_sends = current_user.send_limit
    
    alerts = []
    if verified_count == 0 and len(providers) > 0:
        alerts.append({'type': 'warning', 'message': 'You have unverified providers. Verify them to start sending.'})
    if len(providers) == 0:
        alerts.append({'type': 'info', 'message': 'Connect your first email provider to get started.'})
    
    return render_template('dashboard_new.html',
        provider_count=len(providers),
        verified_count=verified_count,
        list_count=len(lists),
        total_recipients=total_recipients,
        campaign_count=len(campaigns),
        active_campaigns=active_campaigns,
        remaining_sends=remaining_sends,
        send_limit=current_user.send_limit,
        providers=providers[:5],
        campaigns=campaigns,
        alerts=alerts
    )

@dashboard_bp.route('/stats')
@login_required
def stats():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    lists = RecipientList.query.filter_by(user_id=current_user.id).all()
    providers = ProviderConnection.query.filter_by(user_id=current_user.id).all()
    
    total_sent = sum(c.sent_count for c in campaigns)
    total_failed = sum(c.failed_count for c in campaigns)
    
    return jsonify({
        'campaigns': len(campaigns),
        'lists': len(lists),
        'providers': len(providers),
        'total_sent': total_sent,
        'total_failed': total_failed
    })
