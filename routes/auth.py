from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth_login_new.html')
    
    data = request.json or request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not check_password_hash(user.google_id, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    login_user(user, remember=True)
    
    if request.is_json:
        return jsonify({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name}})
    else:
        return redirect(url_for('dashboard.index'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('auth_signup_new.html')
    
    data = request.json or request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        email=email,
        name=email.split('@')[0],
        google_id=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    
    login_user(user, remember=True)
    
    if request.is_json:
        return jsonify({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name}})
    else:
        return redirect(url_for('dashboard.index'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        return render_template('auth_reset.html')
    
    data = request.json or request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'No account found with that email'}), 404
    
    user.google_id = generate_password_hash(password)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Password reset successfully'})
    else:
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    from flask_login import current_user
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'send_limit': current_user.send_limit
    })
