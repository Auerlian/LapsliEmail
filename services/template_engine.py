import re
from html.parser import HTMLParser

class HTMLToText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_text(self):
        return ' '.join(self.text).strip()

class TemplateEngine:
    @staticmethod
    def render(template: str, variables: dict) -> str:
        """Render template with variables. Supports both [variable] and {{variable}} syntax."""
        result = template
        for key, value in variables.items():
            # Support both [variable] and {{variable}} syntax
            result = result.replace(f'[{key}]', str(value))
            result = result.replace(f'{{{{{key}}}}}', str(value))
        return result
    
    @staticmethod
    def extract_variables(template: str) -> list:
        """Extract variables from template. Supports both [variable] and {{variable}} syntax."""
        # Find [variable] patterns
        square_vars = re.findall(r'\[(\w+)\]', template)
        # Find {{variable}} patterns
        curly_vars = re.findall(r'\{\{(\w+)\}\}', template)
        # Combine and deduplicate
        return list(set(square_vars + curly_vars))
    
    @staticmethod
    def html_to_text(html: str) -> str:
        parser = HTMLToText()
        parser.feed(html)
        return parser.get_text()
    
    @staticmethod
    def validate_template(template: str, required_vars: list) -> dict:
        found_vars = set(TemplateEngine.extract_variables(template))
        missing = [v for v in required_vars if v not in found_vars]
        
        return {'valid': len(missing) == 0, 'missing': missing, 'found': list(found_vars)}
