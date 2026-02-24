from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import db
from models.recipient_list import RecipientList, Recipient
from services.csv_import import CSVImportService

lists_bp = Blueprint('lists', __name__)

@lists_bp.route('/')
@login_required
def index():
    lists = RecipientList.query.filter_by(user_id=current_user.id).all()
    return render_template('lists_manage.html', lists=lists)

@lists_bp.route('/old')
@login_required
def old_index():
    lists = RecipientList.query.filter_by(user_id=current_user.id).all()
    return render_template('lists_new.html', lists=lists)

@lists_bp.route('/list')
@login_required
def list_all():
    lists = RecipientList.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': l.id,
        'name': l.name,
        'recipient_count': l.recipient_count,
        'created_at': l.created_at.isoformat()
    } for l in lists])

@lists_bp.route('/parse', methods=['POST'])
@login_required
def parse_csv():
    data = request.json
    content = data.get('content')
    
    result = CSVImportService.parse_csv(content)
    
    if 'error' in result:
        return jsonify({'success': False, 'error': result['error'], 'headers': result.get('headers', [])})
    
    from models.suppression import SuppressionList
    suppressed = SuppressionList.query.filter_by(user_id=current_user.id).all()
    suppressed_emails = {s.email for s in suppressed}
    
    valid_rows = []
    invalid_count = 0
    duplicate_count = 0
    suppressed_count = 0
    
    seen = set()
    for row in result['rows']:
        email = row['email']
        
        if email in suppressed_emails:
            suppressed_count += 1
            continue
        
        if email in seen:
            duplicate_count += 1
            continue
        
        seen.add(email)
        valid_rows.append(row)
    
    variables = set()
    for row in valid_rows:
        variables.update(row.get('data', {}).keys())
    
    return jsonify({
        'success': True,
        'count': len(valid_rows),
        'rows': valid_rows[:100],
        'headers': result['headers'],
        'email_field': result['email_field'],
        'validation': {
            'valid': len(valid_rows),
            'invalid': invalid_count,
            'duplicates': duplicate_count,
            'suppressed': suppressed_count
        },
        'variables': list(variables)
    })

@lists_bp.route('/create', methods=['POST'])
@login_required
def create_list():
    data = request.json
    name = data.get('name')
    rows = data.get('rows')
    
    if not name or not rows:
        return jsonify({'error': 'Missing required fields'}), 400
    
    recipient_list = CSVImportService.create_list(current_user.id, name, rows)
    return jsonify({'success': True, 'id': recipient_list.id})

@lists_bp.route('/<int:list_id>/update', methods=['POST'])
@login_required
def update_list(list_id):
    """Update an existing list with new recipients"""
    recipient_list = RecipientList.query.filter_by(id=list_id, user_id=current_user.id).first()
    if not recipient_list:
        return jsonify({'error': 'Not found'}), 404
    
    data = request.json
    name = data.get('name')
    rows = data.get('rows')
    
    if not name or not rows:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Update list name
    recipient_list.name = name
    
    # Delete existing recipients
    Recipient.query.filter_by(list_id=list_id).delete()
    
    # Add new recipients
    for row in rows:
        recipient = Recipient(
            list_id=list_id,
            email=row['email'],
            data=row.get('data', {})
        )
        db.session.add(recipient)
    
    recipient_list.recipient_count = len(rows)
    db.session.commit()
    
    return jsonify({'success': True, 'id': recipient_list.id})

@lists_bp.route('/<int:list_id>')
@login_required
def get_list(list_id):
    recipient_list = RecipientList.query.filter_by(id=list_id, user_id=current_user.id).first()
    if not recipient_list:
        return jsonify({'error': 'Not found'}), 404
    
    recipients = Recipient.query.filter_by(list_id=list_id).all()
    
    return jsonify({
        'id': recipient_list.id,
        'name': recipient_list.name,
        'recipient_count': recipient_list.recipient_count,
        'recipients': [{
            'email': r.email,
            'name': r.data.get('name', '') if r.data else ''
        } for r in recipients]
    })

@lists_bp.route('/<int:list_id>', methods=['DELETE'])
@login_required
def delete_list(list_id):
    recipient_list = RecipientList.query.filter_by(id=list_id, user_id=current_user.id).first()
    if not recipient_list:
        return jsonify({'error': 'Not found'}), 404
    
    db.session.delete(recipient_list)
    db.session.commit()
    
    return jsonify({'success': True})
