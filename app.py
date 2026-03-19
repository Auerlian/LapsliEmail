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
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
CORS(app)

# Single source of truth for email template
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'email.html')
PROJECT_BRIEF_LOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'project_briefs.jsonl')

LEAD_SMTP_SERVER = os.environ.get('LEAD_SMTP_SERVER')
LEAD_SMTP_PORT = int(os.environ.get('LEAD_SMTP_PORT', '587'))
LEAD_SMTP_USER = os.environ.get('LEAD_SMTP_USER')
LEAD_SMTP_PASS = os.environ.get('LEAD_SMTP_PASS')
LEAD_FROM_EMAIL = os.environ.get('LEAD_FROM_EMAIL', LEAD_SMTP_USER or '')
LEAD_TO_EMAIL = os.environ.get('LEAD_TO_EMAIL', 'james@lapslie.com')
LEAD_ACK_ENABLED = os.environ.get('LEAD_ACK_ENABLED', 'true').lower() in ('1', 'true', 'yes', 'on')
LEAD_CALENDLY_URL = os.environ.get('LEAD_CALENDLY_URL', 'https://calendly.com/lapslie/30min')
LEAD_DASHBOARD_TOKEN = os.environ.get('LEAD_DASHBOARD_TOKEN', '')
LEAD_ALERT_WEBHOOK_URL = os.environ.get('LEAD_ALERT_WEBHOOK_URL', '').strip()
LEAD_ALERT_MIN_PRIORITY = os.environ.get('LEAD_ALERT_MIN_PRIORITY', 'high').strip().lower()
LEAD_STAGES = {'new', 'contacted', 'qualified', 'proposal_sent', 'won', 'lost'}
FOLLOW_UP_STAGES = {'new', 'contacted', 'qualified', 'proposal_sent'}

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
        <p style="margin: 0;">Sent with ❤️ using <a href="https://glowbal.co.uk" style="color: #667eea; text-decoration: none; font-weight: 600;">GlowBal Mailer</a></p>
    </div>
    '''
    
    # Try to insert before closing body tag
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', branding_footer + '</body>')
    else:
        html_content += branding_footer
    
    return html_content


def append_project_brief_log(payload):
    """Persist project brief submissions as JSON lines for lead visibility."""
    os.makedirs(os.path.dirname(PROJECT_BRIEF_LOG_PATH), exist_ok=True)
    with open(PROJECT_BRIEF_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def load_all_project_briefs():
    """Load all stored project briefs from JSONL storage."""
    if not os.path.exists(PROJECT_BRIEF_LOG_PATH):
        return []

    briefs = []
    with open(PROJECT_BRIEF_LOG_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                briefs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return briefs


def save_all_project_briefs(briefs):
    """Rewrite JSONL storage with updated brief records."""
    os.makedirs(os.path.dirname(PROJECT_BRIEF_LOG_PATH), exist_ok=True)
    with open(PROJECT_BRIEF_LOG_PATH, 'w', encoding='utf-8') as f:
        for brief in briefs:
            f.write(json.dumps(brief, ensure_ascii=False) + '\n')


def is_valid_lead_stage(stage):
    return stage in LEAD_STAGES


def send_email_via_lead_smtp(recipient, subject, body):
    """Shared SMTP sender for lead notifications and acknowledgements."""
    if not all([LEAD_SMTP_SERVER, LEAD_SMTP_PORT, LEAD_SMTP_USER, LEAD_SMTP_PASS, LEAD_FROM_EMAIL]):
        return {'sent': False, 'reason': 'lead_smtp_not_configured'}

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = LEAD_FROM_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject

    context = ssl.create_default_context()
    with smtplib.SMTP(LEAD_SMTP_SERVER, LEAD_SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(LEAD_SMTP_USER, LEAD_SMTP_PASS)
        server.sendmail(LEAD_FROM_EMAIL, recipient, msg.as_string())

    return {'sent': True}


def should_send_lead_alert(priority):
    thresholds = {'low': 1, 'medium': 2, 'high': 3}
    candidate = thresholds.get((priority or 'low').lower(), 1)
    minimum = thresholds.get((LEAD_ALERT_MIN_PRIORITY or 'high').lower(), 3)
    return candidate >= minimum


def send_lead_alert(event_type, payload):
    """Push lead alerts to webhook destinations for fast speed-to-lead response."""
    if not LEAD_ALERT_WEBHOOK_URL:
        return {'sent': False, 'reason': 'lead_alert_webhook_not_configured'}

    if event_type == 'lead.created' and not should_send_lead_alert(payload.get('priority')):
        return {'sent': False, 'reason': 'priority_below_alert_threshold'}

    source = payload.get('utmSource') or payload.get('source') or 'unknown'
    summary = str(payload.get('summary', '')).strip()
    compact_summary = summary[:220] + ('…' if len(summary) > 220 else '')

    message = {
        'eventType': event_type,
        'briefId': payload.get('briefId'),
        'name': payload.get('name'),
        'email': payload.get('email'),
        'priority': payload.get('priority'),
        'stage': payload.get('stage'),
        'source': source,
        'budget': payload.get('budget'),
        'timeline': payload.get('timeline'),
        'leadScore': payload.get('leadScore'),
        'stageUpdatedAt': payload.get('stageUpdatedAt') or payload.get('submittedAt'),
        'submittedAt': payload.get('submittedAt'),
        'summary': compact_summary
    }

    try:
        req = Request(
            LEAD_ALERT_WEBHOOK_URL,
            data=json.dumps(message).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urlopen(req, timeout=8) as response:
            status = getattr(response, 'status', None) or response.getcode()
        return {'sent': True, 'status': status}
    except Exception as exc:
        return {'sent': False, 'reason': str(exc)}


def score_project_brief(payload):
    """Simple fit score to prioritize follow-up response queue."""
    score = 0

    budget_weights = {
        '£10,000+': 5,
        '£5,000–£10,000': 4,
        '£2,500–£5,000': 3,
        '£1,000–£2,500': 2,
        'Under £1,000': 1,
        'Not sure yet': 1
    }
    timeline_weights = {
        'ASAP (this week)': 5,
        'Within 2 weeks': 4,
        'Within 1 month': 3,
        'Within 2–3 months': 2,
        'Exploring options': 1,
        'Not sure yet': 1
    }

    score += budget_weights.get(payload.get('budget', ''), 1)
    score += timeline_weights.get(payload.get('timeline', ''), 1)

    summary = payload.get('summary', '')
    if len(summary) >= 180:
        score += 2
    elif len(summary) >= 80:
        score += 1

    if score >= 10:
        priority = 'high'
    elif score >= 7:
        priority = 'medium'
    else:
        priority = 'low'

    return {'score': score, 'priority': priority}


def notify_project_brief_via_email(payload):
    """Send internal project brief notification if LEAD SMTP env vars are configured."""
    if not LEAD_TO_EMAIL:
        return {'sent': False, 'reason': 'lead_to_email_not_configured'}

    subject = f"[Lapslie.com Lead] ({payload['priority'].upper()}) {payload['name']} — {payload['budget']}"
    body = f"""New project brief submitted via Lapslie.com

Name: {payload['name']}
Email: {payload['email']}
Budget: {payload['budget']}
Timeline: {payload['timeline']}
Lead Score: {payload['leadScore']} ({payload['priority']})
Submitted At: {payload['submittedAt']}
Source: {payload['source']}

Summary:
{payload['summary']}
"""

    return send_email_via_lead_smtp(LEAD_TO_EMAIL, subject, body)


def send_project_brief_acknowledgement(payload):
    """Send immediate acknowledgement to the lead to improve conversion and trust."""
    if not LEAD_ACK_ENABLED:
        return {'sent': False, 'reason': 'lead_ack_disabled'}

    subject = "Got it — your project brief is in"
    body = f"""Hi {payload['name']},

Thanks for sending your project brief — I received it.

What happens next:
1) I review your goals, constraints, and timeline.
2) You get a direct reply with recommended next steps within 24 hours.
3) If a call would accelerate things, you can book here: {LEAD_CALENDLY_URL}

Quick recap from your brief:
- Budget: {payload['budget']}
- Timeline: {payload['timeline']}

Speak soon,
James
"""

    return send_email_via_lead_smtp(payload['email'], subject, body)


def load_recent_project_briefs(limit=25):
    """Load most recent project briefs from JSONL log."""
    briefs = load_all_project_briefs()
    recent = list(reversed(briefs[-limit:]))

    for brief in recent:
        if not brief.get('briefId'):
            identity_seed = f"{brief.get('email', 'unknown')}|{brief.get('submittedAt', '')}|{brief.get('name', '')}"
            brief['briefId'] = compute_hash(identity_seed)
        if not brief.get('stage'):
            brief['stage'] = 'new'

    return recent



def summarize_project_briefs(briefs):
    """Create lightweight attribution + priority + pipeline summary from brief list."""
    by_priority = {'high': 0, 'medium': 0, 'low': 0}
    by_source = {}
    by_stage = {stage: 0 for stage in sorted(LEAD_STAGES)}

    contacted_count = 0
    responded_within_24h = 0
    first_response_hours_values = []

    for brief in briefs:
        priority = brief.get('priority', 'low')
        if priority not in by_priority:
            by_priority[priority] = 0
        by_priority[priority] += 1

        source = brief.get('utmSource') or brief.get('source') or 'unknown'
        by_source[source] = by_source.get(source, 0) + 1

        stage = brief.get('stage', 'new')
        if stage not in by_stage:
            by_stage[stage] = 0
        by_stage[stage] += 1

        first_response_hours = brief.get('firstResponseHours')
        if first_response_hours is not None:
            try:
                hours = float(first_response_hours)
                first_response_hours_values.append(hours)
                contacted_count += 1
                if hours <= 24:
                    responded_within_24h += 1
            except (TypeError, ValueError):
                continue

    avg_first_response = round(sum(first_response_hours_values) / len(first_response_hours_values), 2) if first_response_hours_values else None
    response_sla = {
        'contactedLeads': contacted_count,
        'respondedWithin24h': responded_within_24h,
        'respondedWithin24hRate': round((responded_within_24h / contacted_count) * 100, 2) if contacted_count else None,
        'avgFirstResponseHours': avg_first_response
    }

    return {
        'total': len(briefs),
        'byPriority': by_priority,
        'bySource': by_source,
        'byStage': by_stage,
        'responseSLA': response_sla
    }


def build_source_performance(briefs):
    """Aggregate funnel + speed-to-lead metrics by acquisition source."""
    source_stats = {}

    for brief in briefs:
        source = brief.get('utmSource') or brief.get('source') or 'unknown'
        stage = brief.get('stage', 'new')
        priority = brief.get('priority', 'low')

        if source not in source_stats:
            source_stats[source] = {
                'source': source,
                'total': 0,
                'highPriority': 0,
                'contacted': 0,
                'qualified': 0,
                'proposalSent': 0,
                'won': 0,
                'lost': 0,
                'respondedWithin24h': 0,
                'firstResponseHoursValues': []
            }

        stats = source_stats[source]
        stats['total'] += 1

        if priority == 'high':
            stats['highPriority'] += 1

        if stage in {'contacted', 'qualified', 'proposal_sent', 'won', 'lost'}:
            stats['contacted'] += 1
        if stage in {'qualified', 'proposal_sent', 'won', 'lost'}:
            stats['qualified'] += 1
        if stage in {'proposal_sent', 'won', 'lost'}:
            stats['proposalSent'] += 1
        if stage == 'won':
            stats['won'] += 1
        if stage == 'lost':
            stats['lost'] += 1

        first_response_hours = brief.get('firstResponseHours')
        if first_response_hours is not None:
            try:
                hours = float(first_response_hours)
                stats['firstResponseHoursValues'].append(hours)
                if hours <= 24:
                    stats['respondedWithin24h'] += 1
            except (TypeError, ValueError):
                pass

    performance = []
    for stats in source_stats.values():
        contacted = stats['contacted']
        proposal_sent = stats['proposalSent']
        total = stats['total']

        avg_first_response_hours = None
        if stats['firstResponseHoursValues']:
            avg_first_response_hours = round(sum(stats['firstResponseHoursValues']) / len(stats['firstResponseHoursValues']), 2)

        performance.append({
            'source': stats['source'],
            'total': total,
            'highPriority': stats['highPriority'],
            'contacted': contacted,
            'qualified': stats['qualified'],
            'proposalSent': proposal_sent,
            'won': stats['won'],
            'lost': stats['lost'],
            'winRateFromTotal': round((stats['won'] / total) * 100, 2) if total else 0.0,
            'proposalRateFromTotal': round((proposal_sent / total) * 100, 2) if total else 0.0,
            'closeRateFromProposal': round((stats['won'] / proposal_sent) * 100, 2) if proposal_sent else 0.0,
            'respondedWithin24h': stats['respondedWithin24h'],
            'responseWithin24hRate': round((stats['respondedWithin24h'] / contacted) * 100, 2) if contacted else None,
            'avgFirstResponseHours': avg_first_response_hours
        })

    performance.sort(
        key=lambda item: (
            item['won'],
            item['proposalSent'],
            item['highPriority'],
            item['total']
        ),
        reverse=True
    )

    return performance


def authorize_dashboard_request():
    """Shared bearer token guard for lead dashboard endpoints."""
    if not LEAD_DASHBOARD_TOKEN:
        return jsonify({'success': False, 'error': 'Dashboard token not configured'}), 403

    auth_header = request.headers.get('Authorization', '')
    expected_auth = f"Bearer {LEAD_DASHBOARD_TOKEN}"
    if auth_header != expected_auth:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    return None


def parse_iso_datetime(value):
    """Best-effort ISO parser that returns timezone-aware UTC datetimes."""
    if not value:
        return None

    try:
        normalized = str(value).strip().replace('Z', '+00:00')
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def build_follow_up_queue(briefs, sla_hours=24):
    """Return open leads sorted by urgency against a follow-up SLA."""
    now = datetime.now(timezone.utc)
    priority_weight = {'high': 3, 'medium': 2, 'low': 1}

    queue = []
    overdue_count = 0

    for brief in briefs:
        stage = brief.get('stage', 'new')
        if stage not in FOLLOW_UP_STAGES:
            continue

        anchor = parse_iso_datetime(brief.get('stageUpdatedAt')) or parse_iso_datetime(brief.get('submittedAt'))
        if not anchor:
            continue

        hours_since = max(0.0, (now - anchor).total_seconds() / 3600.0)
        overdue = hours_since >= sla_hours
        if overdue:
            overdue_count += 1

        priority = brief.get('priority', 'low')
        stage_actions = {
            'new': 'Send first response and qualify scope',
            'contacted': 'Nudge for missing scope details or call slot',
            'qualified': 'Send scoped proposal and confirm decision timeline',
            'proposal_sent': 'Follow up on proposal with clear next step'
        }

        urgency_score = (
            (2 if overdue else 0)
            + priority_weight.get(priority, 1)
            + min(3, int(hours_since // max(1, sla_hours)))
        )

        queue.append({
            'briefId': brief.get('briefId'),
            'name': brief.get('name', ''),
            'email': brief.get('email', ''),
            'priority': priority,
            'stage': stage,
            'source': brief.get('utmSource') or brief.get('source') or 'unknown',
            'submittedAt': brief.get('submittedAt'),
            'stageUpdatedAt': brief.get('stageUpdatedAt') or brief.get('submittedAt'),
            'hoursSinceStageUpdate': round(hours_since, 2),
            'overdue': overdue,
            'recommendedAction': stage_actions.get(stage, 'Follow up with next concrete step'),
            'urgencyScore': urgency_score
        })

    queue.sort(
        key=lambda item: (
            1 if item['overdue'] else 0,
            item['urgencyScore'],
            item['hoursSinceStageUpdate']
        ),
        reverse=True
    )

    return {
        'slaHours': sla_hours,
        'openLeads': len(queue),
        'overdueLeads': overdue_count,
        'queue': queue
    }

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

@app.route('/api/project-brief', methods=['POST'])
def project_brief():
    """Capture inbound website project briefs for freelance lead qualification."""
    data = request.json or {}

    # Honeypot field should stay empty; basic spam filter
    if data.get('website'):
        return jsonify({'success': False, 'error': 'Spam detected'}), 400

    required_fields = ['name', 'email', 'budget', 'timeline', 'summary']
    missing = [field for field in required_fields if not str(data.get(field, '')).strip()]
    if missing:
        return jsonify({'success': False, 'error': f"Missing required fields: {', '.join(missing)}"}), 400

    email = str(data.get('email', '')).strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'success': False, 'error': 'Invalid email format'}), 400

    submitted_at = datetime.now(timezone.utc).isoformat()
    payload = {
        'name': str(data.get('name', '')).strip(),
        'email': email,
        'budget': str(data.get('budget', '')).strip(),
        'timeline': str(data.get('timeline', '')).strip(),
        'summary': str(data.get('summary', '')).strip(),
        'source': str(data.get('source', 'lapslie.com')).strip(),
        'utmSource': str(data.get('utmSource', '')).strip()[:120],
        'utmMedium': str(data.get('utmMedium', '')).strip()[:120],
        'utmCampaign': str(data.get('utmCampaign', '')).strip()[:180],
        'utmContent': str(data.get('utmContent', '')).strip()[:180],
        'utmTerm': str(data.get('utmTerm', '')).strip()[:180],
        'referrer': str(data.get('referrer', '')).strip()[:500],
        'landingPath': str(data.get('landingPath', '')).strip()[:250],
        'submittedAt': submitted_at,
        'stage': 'new',
        'stageUpdatedAt': submitted_at,
        'statusNotes': '',
        'userAgent': request.headers.get('User-Agent', ''),
        'ipHash': compute_hash(request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown'))
    }

    payload['briefId'] = compute_hash(f"{payload['email']}|{payload['submittedAt']}|{payload['name']}")

    lead_priority = score_project_brief(payload)
    payload['leadScore'] = lead_priority['score']
    payload['priority'] = lead_priority['priority']

    try:
        append_project_brief_log(payload)
        notify_result = notify_project_brief_via_email(payload)
        acknowledgement_result = send_project_brief_acknowledgement(payload)
        alert_result = send_lead_alert('lead.created', payload)
        return jsonify({
            'success': True,
            'message': 'Project brief received',
            'briefId': payload['briefId'],
            'priority': payload['priority'],
            'leadScore': payload['leadScore'],
            'stage': payload['stage'],
            'notification': notify_result,
            'acknowledgement': acknowledgement_result,
            'alert': alert_result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/project-briefs', methods=['GET'])
def get_project_briefs():
    """Lightweight lead inbox endpoint for quick qualification and follow-up."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    limit = request.args.get('limit', default=25, type=int)
    limit = max(1, min(limit, 100))

    briefs = load_recent_project_briefs(limit=limit)

    return jsonify({
        'success': True,
        'count': len(briefs),
        'briefs': briefs
    })


@app.route('/api/project-briefs/<brief_id>', methods=['PATCH'])
def update_project_brief(brief_id):
    """Update lead stage/notes for lightweight pipeline tracking."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    data = request.json or {}
    requested_stage = str(data.get('stage', '')).strip().lower()
    status_notes = str(data.get('statusNotes', '')).strip()[:800]

    if not requested_stage or not is_valid_lead_stage(requested_stage):
        return jsonify({
            'success': False,
            'error': f"Invalid stage. Allowed values: {', '.join(sorted(LEAD_STAGES))}"
        }), 400

    briefs = load_all_project_briefs()
    updated_brief = None

    for brief in briefs:
        candidate_id = brief.get('briefId')
        if not candidate_id:
            identity_seed = f"{brief.get('email', 'unknown')}|{brief.get('submittedAt', '')}|{brief.get('name', '')}"
            candidate_id = compute_hash(identity_seed)
            brief['briefId'] = candidate_id

        if candidate_id == brief_id:
            previous_stage = brief.get('stage', 'new')
            brief['stage'] = requested_stage
            now_iso = datetime.now(timezone.utc).isoformat()
            brief['stageUpdatedAt'] = now_iso
            if status_notes:
                brief['statusNotes'] = status_notes

            if requested_stage in {'contacted', 'qualified', 'proposal_sent', 'won', 'lost'} and not brief.get('contactedAt'):
                brief['contactedAt'] = now_iso
                submitted_at = parse_iso_datetime(brief.get('submittedAt'))
                contacted_at = parse_iso_datetime(now_iso)
                if submitted_at and contacted_at:
                    first_response_hours = max(0.0, (contacted_at - submitted_at).total_seconds() / 3600.0)
                    brief['firstResponseHours'] = round(first_response_hours, 2)

            updated_brief = brief
            break

    if not updated_brief:
        return jsonify({'success': False, 'error': 'Brief not found'}), 404

    save_all_project_briefs(briefs)

    alert_result = {'sent': False, 'reason': 'stage_unchanged'}
    if previous_stage != requested_stage and requested_stage in {'proposal_sent', 'won', 'lost'}:
        alert_result = send_lead_alert('lead.stage_updated', updated_brief)

    return jsonify({
        'success': True,
        'message': 'Project brief updated',
        'brief': updated_brief,
        'alert': alert_result
    })


@app.route('/api/project-briefs/summary', methods=['GET'])
def get_project_briefs_summary():
    """Attribution summary endpoint to identify channels generating quality leads."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    limit = request.args.get('limit', default=100, type=int)
    limit = max(1, min(limit, 1000))

    briefs = load_recent_project_briefs(limit=limit)
    summary = summarize_project_briefs(briefs)

    return jsonify({
        'success': True,
        'limit': limit,
        'summary': summary
    })


@app.route('/api/project-briefs/follow-up-queue', methods=['GET'])
def get_project_briefs_follow_up_queue():
    """Return open leads ranked by urgency against a response SLA."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    limit = request.args.get('limit', default=100, type=int)
    limit = max(1, min(limit, 500))

    sla_hours = request.args.get('slaHours', default=24, type=int)
    sla_hours = max(1, min(sla_hours, 168))

    briefs = load_recent_project_briefs(limit=limit)
    queue_data = build_follow_up_queue(briefs, sla_hours=sla_hours)

    return jsonify({
        'success': True,
        'limit': limit,
        'followUp': queue_data
    })


@app.route('/api/project-briefs/source-performance', methods=['GET'])
def get_project_briefs_source_performance():
    """Return per-source funnel and speed metrics for outreach allocation decisions."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    limit = request.args.get('limit', default=200, type=int)
    limit = max(1, min(limit, 1000))

    briefs = load_recent_project_briefs(limit=limit)
    performance = build_source_performance(briefs)

    return jsonify({
        'success': True,
        'limit': limit,
        'performance': performance
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
