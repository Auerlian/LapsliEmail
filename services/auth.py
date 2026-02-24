from google.oauth2 import id_token
from google.auth.transport import requests
from models import db
from models.user import User
from flask import current_app

class AuthService:
    @staticmethod
    def verify_google_token(token: str) -> dict:
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                current_app.config['GOOGLE_CLIENT_ID']
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')
            
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', '')
            }
        except Exception as e:
            return None
    
    @staticmethod
    def get_or_create_user(google_id: str, email: str, name: str) -> User:
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            user = User(google_id=google_id, email=email, name=name)
            db.session.add(user)
            db.session.commit()
        
        return user
