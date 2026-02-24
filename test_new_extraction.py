from services.template_engine import TemplateEngine

# Test cases
tests = [
    '<h1>Hello [name]!</h1>',
    '<h1>Hello [University Name]!</h1>',
    '<h1>Hello [first-name] and [last_name]!</h1>',
    '<!--[if !mso]>--><p>Test</p><!--<![endif]-->',
    '<h1>[University Name]</h1><p>[Student Name]</p><!--[if mso]><![endif]-->'
]

for i, template in enumerate(tests, 1):
    print(f'Test {i}: {template[:60]}...')
    variables = TemplateEngine.extract_variables(template)
    print(f'Variables: {variables}')
    print()

# Test with actual template
from app_production import app
from models.template import EmailTemplate

with app.app_context():
    t = EmailTemplate.query.first()
    if t:
        print('='*60)
        print(f'Actual Template: {t.name}')
        variables = TemplateEngine.extract_variables(t.html_body)
        print(f'Variables: {variables}')
