from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from services.template_engine import TemplateEngine
from services.ai_assistant import AIAssistant
from models import db

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('/')
@login_required
def index():
    from models.template import EmailTemplate
    templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template('templates_new.html', templates=templates)

@templates_bp.route('/list')
@login_required
def list_templates():
    from models.template import EmailTemplate
    
    templates = EmailTemplate.query.filter_by(user_id=current_user.id).order_by(EmailTemplate.updated_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'subject': t.subject,
        'variables': t.variables,
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat()
    } for t in templates])

@templates_bp.route('/save', methods=['POST'])
@login_required
def save_template():
    from models.template import EmailTemplate
    from models import db
    
    data = request.json
    template_id = data.get('id')
    
    variables = TemplateEngine.extract_variables(data.get('html_body', ''))
    
    if template_id:
        template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if not template:
            return jsonify({'error': 'Not found'}), 404
        
        template.name = data.get('name')
        template.subject = data.get('subject')
        template.html_body = data.get('html_body')
        template.text_body = data.get('text_body')
        template.variables = variables
    else:
        template = EmailTemplate(
            user_id=current_user.id,
            name=data.get('name'),
            subject=data.get('subject'),
            html_body=data.get('html_body'),
            text_body=data.get('text_body'),
            variables=variables
        )
        db.session.add(template)
    
    db.session.commit()
    return jsonify({'success': True, 'id': template.id})

@templates_bp.route('/<int:template_id>')
@login_required
def get_template(template_id):
    from models.template import EmailTemplate
    
    template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
    if not template:
        return jsonify({'error': 'Not found'}), 404
    
    # Re-extract variables if not set
    if not template.variables and template.html_body:
        template.variables = TemplateEngine.extract_variables(template.html_body)
        db.session.commit()
    
    return jsonify({
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'html_body': template.html_body,
        'text_body': template.text_body,
        'variables': template.variables or []
    })

@templates_bp.route('/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    from models.template import EmailTemplate
    from models import db
    
    template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
    if not template:
        return jsonify({'error': 'Not found'}), 404
    
    db.session.delete(template)
    db.session.commit()
    return jsonify({'success': True})

@templates_bp.route('/validate', methods=['POST'])
@login_required
def validate():
    data = request.json
    template = data.get('template')
    required_vars = data.get('required_vars', [])
    
    result = TemplateEngine.validate_template(template, required_vars)
    return jsonify(result)

@templates_bp.route('/preview', methods=['POST'])
@login_required
def preview():
    data = request.json
    template = data.get('template')
    variables = data.get('variables', {})
    
    rendered = TemplateEngine.render(template, variables)
    text_fallback = TemplateEngine.html_to_text(rendered)
    
    return jsonify({'rendered': rendered, 'text_fallback': text_fallback})

@templates_bp.route('/spam-check', methods=['POST'])
@login_required
def spam_check():
    from utils.validators import check_spam_score
    
    data = request.json
    subject = data.get('subject', '')
    body = data.get('body', '')
    
    result = check_spam_score(subject, body)
    return jsonify(result)

@templates_bp.route('/ai/generate', methods=['POST'])
@login_required
def ai_generate():
    data = request.json
    provider = data.get('provider')
    prompt = data.get('prompt')
    variables = data.get('variables', [])
    
    result = AIAssistant.generate_email(provider, prompt, variables, current_user.id)
    return jsonify(result)
