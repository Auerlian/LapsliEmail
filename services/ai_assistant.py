import requests
from flask import current_app
from utils.crypto import CredentialEncryption
from datetime import datetime, timedelta

class AIAssistant:
    MAX_REQUESTS_PER_HOUR = 10
    
    @staticmethod
    def check_rate_limit(user_id: int) -> bool:
        from models import db
        from models.user import User
        
        # Simple in-memory rate limiting (production should use Redis)
        cache_key = f'ai_rate_limit_{user_id}'
        # This is a placeholder - implement proper rate limiting
        return True
    
    @staticmethod
    def generate_email(provider: str, prompt: str, variables: list, user_id: int) -> dict:
        if not AIAssistant.check_rate_limit(user_id):
            return {'error': 'AI rate limit exceeded. Please try again later.'}
        
        # SECURITY: Only send variable schema, never actual recipient data
        variable_schema = [{'name': v, 'type': 'string'} for v in variables]
        
        if provider == 'openai':
            return AIAssistant._openai_generate(prompt, variable_schema)
        elif provider == 'claude':
            return AIAssistant._claude_generate(prompt, variable_schema)
        elif provider == 'gemini':
            return AIAssistant._gemini_generate(prompt, variable_schema)
        else:
            return {'error': 'Unknown provider'}
    
    @staticmethod
    def _get_encrypted_key(key_name: str) -> str:
        """Retrieve encrypted API key from config"""
        encrypted_key = current_app.config.get(key_name)
        if not encrypted_key:
            return None
        
        # If key is already plain text (for backward compatibility)
        if not encrypted_key.startswith('gAAAAAB'):
            return encrypted_key
        
        crypto = CredentialEncryption(current_app.config['ENCRYPTION_KEY'])
        return crypto.decrypt(encrypted_key)
    
    @staticmethod
    def _openai_generate(prompt: str, variable_schema: list) -> dict:
        api_key = AIAssistant._get_encrypted_key('OPENAI_API_KEY')
        if not api_key:
            return {'error': 'OpenAI API key not configured'}
        
        variable_names = [v['name'] for v in variable_schema]
        system_prompt = f"""Generate an email template using these variables: {', '.join(variable_names)}. 
Use {{{{variable}}}} format. 
IMPORTANT: You are only provided with variable names, not actual recipient data.
Generate a professional email template that uses these variables appropriately."""
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}'},
                json={
                    'model': 'gpt-4',
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return {
                    'success': True, 
                    'content': content,
                    'data_sent_to_ai': f'Variable schema: {variable_names}'
                }
            else:
                return {'error': response.text}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def _claude_generate(prompt: str, variable_schema: list) -> dict:
        api_key = AIAssistant._get_encrypted_key('ANTHROPIC_API_KEY')
        if not api_key:
            return {'error': 'Claude API key not configured'}
        
        variable_names = [v['name'] for v in variable_schema]
        system_prompt = f"""Generate an email template using these variables: {', '.join(variable_names)}. 
Use {{{{variable}}}} format.
IMPORTANT: You are only provided with variable names, not actual recipient data.
Generate a professional email template that uses these variables appropriately."""
        
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-sonnet-20240229',
                    'max_tokens': 1024,
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['content'][0]['text']
                return {
                    'success': True, 
                    'content': content,
                    'data_sent_to_ai': f'Variable schema: {variable_names}'
                }
            else:
                return {'error': response.text}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def _gemini_generate(prompt: str, variable_schema: list) -> dict:
        api_key = AIAssistant._get_encrypted_key('GOOGLE_AI_API_KEY')
        if not api_key:
            return {'error': 'Gemini API key not configured'}
        
        variable_names = [v['name'] for v in variable_schema]
        system_prompt = f"""Generate an email template using these variables: {', '.join(variable_names)}. 
Use {{{{variable}}}} format.
IMPORTANT: You are only provided with variable names, not actual recipient data.
Generate a professional email template that uses these variables appropriately."""
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}',
                json={'contents': [{'parts': [{'text': full_prompt}]}]},
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['candidates'][0]['content']['parts'][0]['text']
                return {
                    'success': True, 
                    'content': content,
                    'data_sent_to_ai': f'Variable schema: {variable_names}'
                }
            else:
                return {'error': response.text}
        except Exception as e:
            return {'error': str(e)}
