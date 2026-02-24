from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required
from config import Config
from models import db
from models.user import User
from routes import register_routes

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

register_routes(app)

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/login')
def login_page():
    return render_template('auth_login.html')

@app.route('/signup')
def signup_page():
    return render_template('auth_signup.html')

@app.route('/app')
@login_required
def app_home():
    return redirect(url_for('dashboard.index'))

@app.cli.command()
def init_db():
    db.create_all()
    print('Database initialized')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
