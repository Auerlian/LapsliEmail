from flask import Blueprint

def register_routes(app):
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.providers import providers_bp
    from routes.lists import lists_bp
    from routes.templates import templates_bp
    from routes.campaigns import campaigns_bp
    from routes.suppression import suppression_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(providers_bp, url_prefix='/providers')
    app.register_blueprint(lists_bp, url_prefix='/lists')
    app.register_blueprint(templates_bp, url_prefix='/templates')
    app.register_blueprint(campaigns_bp, url_prefix='/campaigns')
    app.register_blueprint(suppression_bp, url_prefix='/suppression')
