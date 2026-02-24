from models import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    google_id = db.Column(db.String(255), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    send_limit = db.Column(db.Integer, default=100)
    
    providers = db.relationship('ProviderConnection', back_populates='user', cascade='all, delete-orphan')
    lists = db.relationship('RecipientList', back_populates='user', cascade='all, delete-orphan')
    campaigns = db.relationship('Campaign', back_populates='user', cascade='all, delete-orphan')
    daily_send_count = db.Column(db.Integer, default=0)
    last_send_date = db.Column(db.Date)
