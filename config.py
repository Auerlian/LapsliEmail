import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///platform.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Disable SQL logging for performance
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    
    # OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback')
    
    # Encryption
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', os.urandom(32).hex())
    
    # Rate limits
    DEFAULT_SEND_RATE = int(os.getenv('DEFAULT_SEND_RATE', 100))
    MAX_RECIPIENTS_PER_CAMPAIGN = int(os.getenv('MAX_RECIPIENTS_PER_CAMPAIGN', 10000))
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # AI Providers
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
