from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.suppression import SuppressionList
from utils.validators import is_valid_email

suppression_bp = Blueprint('suppression', __name__)

@suppression_bp.route('/list')
@login_required
def list_suppressions():
    suppressions = SuppressionList.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': s.id,
        'email': s.email,
        'reason': s.reason,
        'created_at': s.created_at.isoformat()
    } for s in suppressions])

@suppression_bp.route('/add', methods=['POST'])
@login_required
def add_suppression():
    data = request.json
    email = data.get('email', '').strip().lower()
    reason = data.get('reason', 'manual')
    
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    
    existing = SuppressionList.query.filter_by(user_id=current_user.id, email=email).first()
    if existing:
        return jsonify({'error': 'Email already suppressed'}), 400
    
    suppression = SuppressionList(user_id=current_user.id, email=email, reason=reason)
    db.session.add(suppression)
    db.session.commit()
    
    return jsonify({'success': True, 'id': suppression.id})

@suppression_bp.route('/bulk', methods=['POST'])
@login_required
def bulk_add():
    data = request.json
    emails = data.get('emails', [])
    reason = data.get('reason', 'bulk_import')
    
    added = 0
    for email in emails:
        email = email.strip().lower()
        if not is_valid_email(email):
            continue
        
        existing = SuppressionList.query.filter_by(user_id=current_user.id, email=email).first()
        if existing:
            continue
        
        suppression = SuppressionList(user_id=current_user.id, email=email, reason=reason)
        db.session.add(suppression)
        added += 1
    
    db.session.commit()
    return jsonify({'success': True, 'added': added})

@suppression_bp.route('/<int:suppression_id>', methods=['DELETE'])
@login_required
def delete_suppression(suppression_id):
    suppression = SuppressionList.query.filter_by(id=suppression_id, user_id=current_user.id).first()
    if not suppression:
        return jsonify({'error': 'Not found'}), 404
    
    db.session.delete(suppression)
    db.session.commit()
    
    return jsonify({'success': True})
