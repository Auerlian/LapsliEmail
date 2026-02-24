from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import db
from models.provider import ProviderConnection
from utils.crypto import CredentialEncryption
from flask import current_app
import json

providers_bp = Blueprint('providers', __name__)

@providers_bp.route('/')
@login_required
def index():
    providers = ProviderConnection.query.filter_by(user_id=current_user.id).all()
    return render_template('providers_manage.html', providers=providers)

@providers_bp.route('/old')
@login_required
def old_index():
    providers = ProviderConnection.query.filter_by(user_id=current_user.id).all()
    return render_template('providers_new.html', providers=providers)

@providers_bp.route('/schemas')
@login_required
def get_schemas():
    from services.provider_factory import ProviderFactory
    
    providers = ['gmail', 'brevo', 'sendgrid', 'mailgun', 'ses', 'smtp']
    schemas = {p: ProviderFactory.get_credential_schema(p) for p in providers}
    
    return jsonify(schemas)

@providers_bp.route('/list')
@login_required
def list_providers():
    providers = ProviderConnection.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': p.id,
        'type': p.provider_type,
        'sender_email': p.sender_email,
        'sender_name': p.sender_name,
        'is_verified': p.is_verified,
        'created_at': p.created_at.isoformat()
    } for p in providers])

@providers_bp.route('/add', methods=['POST'])
@login_required
def add_provider():
    data = request.json
    provider_type = data.get('provider_type')
    sender_email = data.get('sender_email')
    sender_name = data.get('sender_name')
    credentials = data.get('credentials')
    
    if not all([provider_type, sender_email, credentials]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
    encrypted = crypto.encrypt(json.dumps(credentials))
    
    provider = ProviderConnection(
        user_id=current_user.id,
        provider_type=provider_type,
        sender_email=sender_email,
        sender_name=sender_name,
        encrypted_credentials=encrypted,
        verification_status='pending'
    )
    
    db.session.add(provider)
    db.session.commit()
    
    return jsonify({'success': True, 'id': provider.id})

@providers_bp.route('/<int:provider_id>/verify', methods=['POST'])
@login_required
def verify_provider(provider_id):
    from services.provider_factory import ProviderFactory
    from datetime import datetime
    
    provider = ProviderConnection.query.filter_by(id=provider_id, user_id=current_user.id).first()
    if not provider:
        return jsonify({'error': 'Not found'}), 404
    
    crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
    credentials = json.loads(crypto.decrypt(provider.encrypted_credentials))
    
    try:
        provider_instance = ProviderFactory.create(provider.provider_type, credentials)
        result = provider_instance.verify()
        
        if result['success']:
            provider.is_verified = True
            provider.verification_status = 'verified'
            provider.health_status = 'healthy'
            provider.last_verified_at = datetime.utcnow()
        else:
            provider.verification_status = 'invalid_credentials'
            provider.health_status = 'error'
        
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        provider.verification_status = 'error'
        provider.health_status = 'error'
        db.session.commit()
        return jsonify({'success': False, 'error': str(e)})

@providers_bp.route('/<int:provider_id>')
@login_required
def get_provider(provider_id):
    """Get provider details for editing"""
    provider = ProviderConnection.query.filter_by(id=provider_id, user_id=current_user.id).first()
    if not provider:
        return jsonify({'error': 'Not found'}), 404
    
    crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
    credentials = json.loads(crypto.decrypt(provider.encrypted_credentials))
    
    return jsonify({
        'id': provider.id,
        'provider_type': provider.provider_type,
        'sender_email': provider.sender_email,
        'sender_name': provider.sender_name,
        'credentials': credentials,
        'rate_limit': provider.rate_limit
    })

@providers_bp.route('/<int:provider_id>/update', methods=['POST'])
@login_required
def update_provider(provider_id):
    """Update an existing provider"""
    provider = ProviderConnection.query.filter_by(id=provider_id, user_id=current_user.id).first()
    if not provider:
        return jsonify({'error': 'Not found'}), 404
    
    data = request.json
    
    # Update basic info
    if 'sender_email' in data:
        provider.sender_email = data['sender_email']
    if 'sender_name' in data:
        provider.sender_name = data['sender_name']
    if 'rate_limit' in data:
        provider.rate_limit = data['rate_limit']
    
    # Update credentials if provided
    if 'credentials' in data:
        crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
        encrypted = crypto.encrypt(json.dumps(data['credentials']))
        provider.encrypted_credentials = encrypted
        # Reset verification status when credentials change
        provider.is_verified = False
        provider.verification_status = 'pending'
    
    db.session.commit()
    
    return jsonify({'success': True, 'id': provider.id})

@providers_bp.route('/<int:provider_id>', methods=['DELETE'])
@login_required
def delete_provider(provider_id):
    provider = ProviderConnection.query.filter_by(id=provider_id, user_id=current_user.id).first()
    if not provider:
        return jsonify({'error': 'Not found'}), 404
    
    db.session.delete(provider)
    db.session.commit()
    
    return jsonify({'success': True})
