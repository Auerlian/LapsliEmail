from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re
import secrets
import os
import hashlib
import csv
import io
from html.parser import HTMLParser

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
CORS(app)

# Single source of truth for email template
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'email.html')

class HTMLToText(HTMLParser):
    """Simple HTML to text converter for fallback"""
    def __init__(self):
        super().__init__()
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_text(self):
        return ' '.join(self.text).strip()

def html_to_text(html):
    """Convert HTML to plain text for fallback"""
    parser = HTMLToText()
    parser.feed(html)
    return parser.get_text()

def compute_hash(content):
    """Compute SHA256 hash of content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

def get_template_metadata(content):
    """Get metadata about template content"""
    return {
        'length': len(content),
        'hash': compute_hash(content),
        'preview': content[:120] if len(content) > 120 else content
    }

def parse_recipients(raw_data):
    """Parse recipients from plain text format"""
    results = []
    seen = set()
    for line in raw_data.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(',')]
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', parts[0])
        if not email_match:
            continue
        email = email_match.group()
        name = parts[1] if len(parts) > 1 else email
        university = parts[2] if len(parts) > 2 else name
        if email not in seen:
            seen.add(email)
            results.append({'email': email, 'name': name, 'university': university})
    return results

def parse_csv_recipients(csv_content):
    """Parse recipients from CSV content with dynamic field mapping"""
    results = []
    seen = set()
    
    try:
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        # Get all field names from CSV
        fieldnames = reader.fieldnames
        if not fieldnames:
            return {'error': 'CSV has no headers', 'recipients': []}
        
        # Find email field (case-insensitive)
        email_field = None
        for field in fieldnames:
            if field.lower() in ['email', 'email address', 'e-mail', 'mail']:
                email_field = field
                break
        
        if not email_field:
            return {'error': 'CSV must have an "email" column', 'recipients': [], 'fields': fieldnames}
        
        # Parse all rows
        for row in reader:
            email = row.get(email_field, '').strip()
            if not email:
                continue
            
            # Validate email format
            if not re.match(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
                continue
            
            if email not in seen:
                seen.add(email)
                # Include all fields from CSV
                recipient = {'email': email}
                for field in fieldnames:
                    if field != email_field:
                        recipient[field] = row.get(field, '').strip()
                results.append(recipient)
        
        return {'recipients': results, 'fields': fieldnames, 'email_field': email_field}
    
    except Exception as e:
        return {'error': str(e), 'recipients': []}

def personalize_content_dynamic(content, recipient_data):
    """Replace all [FieldName] tokens with values from recipient data"""
    for field, value in recipient_data.items():
        if field != 'email':
            # Replace [FieldName] with actual value
            content = content.replace(f'[{field}]', str(value))
    
    # Legacy support for {name} and [University Name]
    if 'name' in recipient_data:
        content = content.replace('{name}', recipient_data['name'])
    if 'university' in recipient_data or 'University Name' in recipient_data:
        uni_value = recipient_data.get('university', recipient_data.get('University Name', ''))
        content = content.replace('[University Name]', uni_value)
    
    return content

def personalize_content(content, name, university):
    """Replace personalization tokens in content"""
    content = content.replace('{name}', name)
    content = content.replace('[University Name]', university)
    return content

def add_email_branding(html_content):
    """Add BulkMailer branding footer to HTML emails"""
    branding_footer = '''
    <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #e2e8f0; text-align: center; font-size: 12px; color: #718096;">
        <p style="margin: 0;">Sent with ❤️ using <a href="https://morningbuddy.co.uk" style="color: #667eea; text-decoration: none; font-weight: 600;">BulkMailer</a> - Free bulk email service</p>
    </div>
    '''
    
    # Try to insert before closing body tag
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', branding_footer + '</body>')
    else:
        html_content += branding_footer
    
    return html_content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_template', methods=['GET'])
def load_template():
    """Load the email template from static/email.html"""
    try:
        if not os.path.exists(TEMPLATE_PATH):
            return jsonify({
                'success': False,
                'error': f'Template not found at {TEMPLATE_PATH}'
            })
        
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        metadata = get_template_metadata(content)
        
        return jsonify({
            'success': True,
            'content': content,
            'metadata': {
                'path': TEMPLATE_PATH,
                'length': metadata['length'],
                'hash': metadata['hash'],
                'preview': metadata['preview']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/debug/template', methods=['GET'])
def debug_template():
    """Debug endpoint to inspect template file"""
    try:
        exists = os.path.exists(TEMPLATE_PATH)
        
        if not exists:
            return jsonify({
                'path': os.path.abspath(TEMPLATE_PATH),
                'exists': False,
                'error': 'Template file not found'
            })
        
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'path': os.path.abspath(TEMPLATE_PATH),
            'exists': True,
            'length': len(content),
            'hash': compute_hash(content),
            'first_200_chars': content[:200]
        })
    except Exception as e:
        return jsonify({
            'path': os.path.abspath(TEMPLATE_PATH),
            'exists': os.path.exists(TEMPLATE_PATH),
            'error': str(e)
        })

@app.route('/validate_recipients', methods=['POST'])
def validate_recipients():
    data = request.json
    recipients_data = parse_recipients(data.get('recipients', ''))
    return jsonify({'count': len(recipients_data), 'recipients': recipients_data})

@app.route('/parse_csv', methods=['POST'])
def parse_csv():
    """Parse CSV and return recipients with field mapping"""
    data = request.json
    csv_content = data.get('csv_content', '')
    
    result = parse_csv_recipients(csv_content)
    
    if 'error' in result:
        return jsonify({'success': False, 'error': result['error'], 'fields': result.get('fields', [])})
    
    return jsonify({
        'success': True,
        'count': len(result['recipients']),
        'recipients': result['recipients'],
        'fields': result['fields'],
        'email_field': result['email_field']
    })

@app.route('/send_emails', methods=['POST'])
def send_emails():
    data = request.json
    
    smtp_server = data.get('smtp_server')
    smtp_port = int(data.get('smtp_port'))
    email_user = data.get('email_user')
    email_pass = data.get('email_pass')
    from_email = data.get('from_email', email_user)
    subject = data.get('subject')
    body = data.get('body')
    html_body = data.get('html_body', '')
    send_as_html = data.get('send_as_html', False)
    delay = int(data.get('delay', 3))
    dry_run = data.get('dry_run', False)
    
    # Get recipients - could be from CSV or plain text
    recipients_list = data.get('recipients_list', [])
    if not recipients_list:
        # Fallback to plain text parsing
        recipients_list = parse_recipients(data.get('recipients', ''))
    
    # Validate required fields based on mode
    if not all([smtp_server, smtp_port, email_user, email_pass, subject, recipients_list]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    # Hard fail if HTML mode but template too short or empty
    if send_as_html:
        if not html_body or len(html_body) < 500:
            return jsonify({
                'success': False,
                'error': f'HTML body is required and must be at least 500 characters (got {len(html_body)}). Please load a valid template.'
            })
    
    if not send_as_html and not body:
        return jsonify({'success': False, 'error': 'Plain text body is required'})
    
    # Compute template metadata for verification
    template_metadata = None
    if send_as_html:
        template_metadata = {
            'hash': compute_hash(html_body),
            'length': len(html_body)
        }
    
    results = []
    context = ssl.create_default_context()
    
    try:
        if not dry_run:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls(context=context)
            server.login(email_user, email_pass)
        
        count = 0
        for recipient in recipients_list:
            email_to = recipient['email']
            
            # Get display name for logging
            display_name = recipient.get('name', recipient.get('Name', email_to))
            
            # Personalize content with dynamic fields
            personalized_subject = personalize_content_dynamic(subject, recipient)
            personalized_body = personalize_content_dynamic(body, recipient) if body else ''
            
            if send_as_html:
                msg = MIMEMultipart('alternative')
                msg['From'] = from_email
                msg['To'] = email_to
                msg['Subject'] = personalized_subject
                
                # Personalize HTML with dynamic fields
                personalized_html = personalize_content_dynamic(html_body, recipient)
                
                # Add branding footer
                personalized_html = add_email_branding(personalized_html)
                
                # Plain text fallback - use provided body or auto-generate from HTML
                if not personalized_body:
                    personalized_body = html_to_text(personalized_html)
                
                text_part = MIMEText(personalized_body, 'plain', 'utf-8')
                msg.attach(text_part)
                
                # HTML body
                html_part = MIMEText(personalized_html, 'html', 'utf-8')
                msg.attach(html_part)
            else:
                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = email_to
                msg['Subject'] = personalized_subject
                msg.attach(MIMEText(personalized_body, 'plain', 'utf-8'))
            
            if dry_run:
                # Return rendered content without sending
                result = {
                    'email': email_to,
                    'name': display_name,
                    'status': 'dry-run',
                    'message': 'Preview only',
                    'rendered_subject': personalized_subject,
                    'rendered_text': personalized_body
                }
                if send_as_html:
                    result['rendered_html_preview'] = personalized_html[:80]
                results.append(result)
                count += 1
            else:
                try:
                    server.sendmail(from_email, email_to, msg.as_string())
                    count += 1
                    results.append({
                        'email': email_to,
                        'name': display_name,
                        'status': 'success',
                        'message': 'Sent successfully'
                    })
                except Exception as e:
                    results.append({
                        'email': email_to,
                        'name': display_name,
                        'status': 'error',
                        'message': str(e)
                    })
            
            time.sleep(delay if not dry_run else 0)
        
        if not dry_run:
            server.quit()
        
        response = {
            'success': True,
            'sent': count,
            'total': len(recipients_list),
            'results': results,
            'dry_run': dry_run
        }
        
        # Add template metadata to response
        if template_metadata:
            response['template_metadata'] = template_metadata
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  BULK EMAIL SENDER - Web Interface")
    print("="*60)
    print("\n  Open your browser and go to: http://localhost:5000")
    print("\n  Press CTRL+C to stop the server")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)
