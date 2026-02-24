import re

template = '<h1>Hello [name]!</h1><p>Your email is [email]</p><p>Company: [company]</p>'

print("Template:", template)
print()

# Current regex
square_vars = re.findall(r'\[(\w+)\]', template)
print('Square bracket variables (\\w+):', square_vars)

# Alternative regex
alt_vars = re.findall(r'\[([^\]]+)\]', template)
print('Square bracket variables ([^\\]]+):', alt_vars)

# Test the actual function
from services.template_engine import TemplateEngine

variables = TemplateEngine.extract_variables(template)
print()
print('TemplateEngine.extract_variables():', variables)
