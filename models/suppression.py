from models import db
from datetime import datetime

class SuppressionList(db.Model):
    __tablename__ = 'suppression_list'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    reason = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='suppressions')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'email', name='uq_user_suppression'),
    )
