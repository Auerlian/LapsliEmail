from models import db
from datetime import datetime

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider_connections.id'), nullable=False)
    list_id = db.Column(db.Integer, db.ForeignKey('recipient_lists.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    html_body = db.Column(db.Text)
    text_body = db.Column(db.Text)
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id'))
    status = db.Column(db.String(50), default='draft')
    total_recipients = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    scheduled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    user = db.relationship('User', back_populates='campaigns')
    logs = db.relationship('CampaignLog', back_populates='campaign', cascade='all, delete-orphan')

class CampaignLog(db.Model):
    __tablename__ = 'campaign_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    campaign = db.relationship('Campaign', back_populates='logs')
    
    __table_args__ = (
        db.Index('idx_campaign_status', 'campaign_id', 'status'),
    )
