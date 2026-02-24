from models import db
from datetime import datetime

class ProviderConnection(db.Model):
    __tablename__ = 'provider_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_type = db.Column(db.String(50), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255))
    encrypted_credentials = db.Column(db.Text, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(50), default='pending')
    health_status = db.Column(db.String(50), default='unknown')
    last_verified_at = db.Column(db.DateTime)
    rate_limit = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='providers')
    
    __table_args__ = (
        db.Index('idx_user_provider', 'user_id', 'provider_type'),
    )
