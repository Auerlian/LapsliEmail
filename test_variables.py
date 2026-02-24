#!/usr/bin/env python
"""Test variable extraction"""

from services.template_engine import TemplateEngine

# Test templates
test_cases = [
    "<h1>Hello [name]!</h1><p>Your email is [email]</p>",
    "<h1>Hello {{name}}!</h1><p>Your email is {{email}}</p>",
    "<h1>Hello [name]!</h1><p>Company: [company]</p><p>Email: {{email}}</p>",
]

for i, template in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Template: {template}")
    variables = TemplateEngine.extract_variables(template)
    print(f"Variables: {variables}")
    
    # Test rendering
    test_vars = {'name': 'John', 'email': 'john@example.com', 'company': 'Acme Corp'}
    rendered = TemplateEngine.render(template, test_vars)
    print(f"Rendered: {rendered}")
