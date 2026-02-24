#!/usr/bin/env python
"""Update all templates to extract variables"""

from app_production import app, db
from models.template import EmailTemplate
from services.template_engine import TemplateEngine

with app.app_context():
    templates = EmailTemplate.query.all()
    
    print(f"Found {len(templates)} templates")
    
    for template in templates:
        if template.html_body:
            variables = TemplateEngine.extract_variables(template.html_body)
            template.variables = variables
            print(f"Template '{template.name}': {variables}")
    
    db.session.commit()
    print("\n✅ All templates updated!")
