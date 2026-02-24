from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Import all models before initializing migrate
with app.app_context():
    from models.user import User
    from models.provider import ProviderConnection
    from models.campaign import Campaign, CampaignLog
    from models.recipient_list import RecipientList, Recipient
    from models.template import EmailTemplate
    from models.suppression import SuppressionList

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))

@app.route('/')
def index():
    from flask import render_template
    from flask_login import current_user
    if current_user.is_authenticated:
        from flask import redirect, url_for
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')

from routes import register_routes
register_routes(app)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  BULK EMAIL PLATFORM - Production Mode")
    print("="*60)
    print("\n  Open your browser: http://localhost:5001")
    print("\n  Features:")
    print("  - Multi-provider support (Gmail, SendGrid, Mailgun, SES, Brevo)")
    print("  - Campaign wizard with validation")
    print("  - Template management")
    print("  - Suppression list enforcement")
    print("  - AI-assisted email generation")
    print("  - Rate limiting and security controls")
    print("\n  Database migrations: flask db upgrade")
    print("="*60 + "\n")
    app.run(debug=False, port=5001, host='127.0.0.1', threaded=True)
