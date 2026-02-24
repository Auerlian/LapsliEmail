from models import db
from datetime import datetime

class RecipientList(db.Model):
    __tablename__ = 'recipient_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    recipient_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='lists')
    recipients = db.relationship('Recipient', back_populates='list', cascade='all, delete-orphan')

class Recipient(db.Model):
    __tablename__ = 'recipients'
    
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('recipient_lists.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    data = db.Column(db.JSON)
    
    list = db.relationship('RecipientList', back_populates='recipients')
    
    __table_args__ = (
        db.Index('idx_list_email', 'list_id', 'email'),
    )
