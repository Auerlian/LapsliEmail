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
        'projectUrl': payload.get('projectUrl'),
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

    project_url = str(payload.get('projectUrl', '')).strip()
    if project_url.startswith('http://') or project_url.startswith('https://'):
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
Project URL: {payload.get('projectUrl') or 'Not provided'}
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
- Project URL: {payload.get('projectUrl') or 'Not provided'}

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


def apply_stage_update(brief, requested_stage, status_notes=''):
    """Apply stage transition metadata consistently across endpoints."""
    previous_stage = brief.get('stage', 'new')
    brief['stage'] = requested_stage
    now_iso = datetime.now(timezone.utc).isoformat()
    brief['stageUpdatedAt'] = now_iso

    if status_notes:
        brief['statusNotes'] = status_notes[:800]

    if requested_stage in {'contacted', 'qualified', 'proposal_sent', 'won', 'lost'} and not brief.get('contactedAt'):
        brief['contactedAt'] = now_iso
        submitted_at = parse_iso_datetime(brief.get('submittedAt'))
        contacted_at = parse_iso_datetime(now_iso)
        if submitted_at and contacted_at:
            first_response_hours = max(0.0, (contacted_at - submitted_at).total_seconds() / 3600.0)
            brief['firstResponseHours'] = round(first_response_hours, 2)

    return previous_stage, now_iso


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


def build_source_recommendations(performance, min_sample=3):
    """Create sample-aware channel allocation guidance from source performance metrics."""
    recommendations = []
    items = [item for item in performance if item.get('total', 0) > 0]
    if not items:
        return recommendations

    reliable = [
        item for item in items
        if item.get('total', 0) >= min_sample and item.get('proposalSent', 0) >= 1
    ]

    reliable.sort(
        key=lambda item: (
            item.get('closeRateFromProposal', 0),
            item.get('proposalRateFromTotal', 0),
            item.get('won', 0)
        ),
        reverse=True
    )

    if reliable:
        winner = reliable[0]
        recommendations.append({
            'action': 'scale',
            'source': winner.get('source', 'unknown'),
            'reason': (
                f"Highest reliable conversion: closeRateFromProposal={winner.get('closeRateFromProposal', 0)}%, "
                f"proposalRateFromTotal={winner.get('proposalRateFromTotal', 0)}% "
                f"across {winner.get('total', 0)} leads."
            )
        })

    weak_reliable = [
        item for item in reliable
        if item.get('won', 0) == 0 and item.get('proposalRateFromTotal', 0) < 20
    ]
    if weak_reliable:
        weakest = sorted(weak_reliable, key=lambda item: item.get('total', 0), reverse=True)[0]
        recommendations.append({
            'action': 'deprioritize',
            'source': weakest.get('source', 'unknown'),
            'reason': (
                f"Sustained low yield: 0 wins and proposalRateFromTotal={weakest.get('proposalRateFromTotal', 0)}% "
                f"over {weakest.get('total', 0)} leads."
            )
        })

    low_data = [item for item in items if item.get('total', 0) < min_sample]
    if low_data:
        test_candidate = sorted(
            low_data,
            key=lambda item: (item.get('proposalRateFromTotal', 0), item.get('total', 0)),
            reverse=True
        )[0]
        recommendations.append({
            'action': 'test',
            'source': test_candidate.get('source', 'unknown'),
            'reason': (
                f"Insufficient sample ({test_candidate.get('total', 0)} leads). "
                "Run a controlled test before scaling or cutting."
            )
        })

    return recommendations


def build_daily_plan(briefs, sla_hours=24):
    """Combine queue urgency + source performance into a focused daily execution plan."""
    follow_up = build_follow_up_queue(briefs, sla_hours=sla_hours)
    performance = build_source_performance(briefs)

    queue = follow_up.get('queue', [])
    top_actions = []
    for item in queue[:5]:
        top_actions.append({
            'briefId': item.get('briefId'),
            'name': item.get('name', ''),
            'priority': item.get('priority', 'low'),
            'stage': item.get('stage', 'new'),
            'source': item.get('source', 'unknown'),
            'hoursSinceStageUpdate': item.get('hoursSinceStageUpdate', 0),
            'recommendedAction': item.get('recommendedAction', 'Follow up with next concrete step')
        })

    source_recommendation_objects = build_source_recommendations(performance)
    source_recommendations = [
        f"{entry.get('action', 'review').upper()}: {entry.get('source', 'unknown')} — {entry.get('reason', '')}"
        for entry in source_recommendation_objects
    ]

    execution_notes = []
    if follow_up.get('overdueLeads', 0) > 0:
        execution_notes.append(
            f"Clear overdue queue first: {follow_up.get('overdueLeads', 0)} leads beyond {sla_hours}h SLA."
        )
    if not execution_notes:
        execution_notes.append("No overdue leads. Prioritize top urgency leads and proposal follow-through.")

    return {
        'slaHours': sla_hours,
        'openLeads': follow_up.get('openLeads', 0),
        'overdueLeads': follow_up.get('overdueLeads', 0),
        'topActions': top_actions,
        'sourceRecommendations': source_recommendations,
        'sourceRecommendationDetails': source_recommendation_objects,
        'executionNotes': execution_notes
    }


def extract_project_url_signals(project_url, timeout=6):
    """Fetch lightweight public-page signals to personalize first response drafts."""
    if not project_url:
        return {'available': False, 'reason': 'project_url_missing'}

    try:
        req = Request(
            project_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; LapsliEmailLeadOps/1.0; +https://lapslie.com)'
            }
        )
        with urlopen(req, timeout=timeout) as response:
            content_type = (response.headers.get('Content-Type') or '').lower()
            if 'text/html' not in content_type:
                return {'available': False, 'reason': f'unsupported_content_type:{content_type or "unknown"}'}
            html = response.read(150000).decode('utf-8', errors='ignore')

        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
        description_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html,
            flags=re.IGNORECASE | re.DOTALL
        )

        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.IGNORECASE | re.DOTALL)

        def clean(value):
            if not value:
                return ''
            without_tags = re.sub(r'<[^>]+>', ' ', value)
            normalized = re.sub(r'\s+', ' ', without_tags).strip()
            return normalized[:220]

        signals = {
            'available': True,
            'title': clean(title_match.group(1) if title_match else ''),
            'metaDescription': clean(description_match.group(1) if description_match else ''),
            'h1': clean(h1_match.group(1) if h1_match else ''),
            'url': project_url
        }

        if not any([signals['title'], signals['metaDescription'], signals['h1']]):
            return {'available': False, 'reason': 'no_extractable_signals', 'url': project_url}

        return signals
    except Exception as exc:
        return {'available': False, 'reason': str(exc), 'url': project_url}


def build_first_response_draft(brief):
    """Generate a structured first-response email draft using brief + project URL signals."""
    name = brief.get('name') or 'there'
    budget = brief.get('budget') or 'Not specified'
    timeline = brief.get('timeline') or 'Not specified'
    priority = brief.get('priority') or 'low'
    summary = (brief.get('summary') or '').strip()
    project_url = (brief.get('projectUrl') or '').strip()

    project_signals = extract_project_url_signals(project_url) if project_url else {'available': False, 'reason': 'project_url_missing'}

    observations = []
    if project_signals.get('available'):
        if project_signals.get('title'):
            observations.append(f"Homepage title is currently: \"{project_signals['title']}\".")
        if project_signals.get('h1'):
            observations.append(f"Primary page headline appears to be: \"{project_signals['h1']}\".")
        if project_signals.get('metaDescription'):
            observations.append("Meta description is present — we can tighten this against your conversion goal so paid/organic clicks land cleaner.")
        if len(observations) < 3:
            observations.append("I can run a focused pass on speed, clarity, and CTA path to remove drop-off between first visit and enquiry.")
    else:
        observations.append("I can start with a fast conversion + technical audit and map the top 3 fixes with highest expected ROI.")

    while len(observations) < 3:
        observations.append("I’ll keep changes implementation-first so you get shipped improvements, not just recommendations.")

    recommended_next_step = "Reply with your top KPI + access constraints, and I’ll send a concrete sprint plan within 24 hours."
    if priority == 'high':
        recommended_next_step = "Given urgency/fit, I recommend a 20-minute scope call today/tomorrow to lock sprint scope and start this week."

    subject = f"Re: your project brief — suggested first sprint"
    body_lines = [
        f"Hi {name},",
        "",
        "Thanks for the brief — useful context.",
        "",
        "Based on what you shared, here are the first 3 high-leverage opportunities:",
        f"1) {observations[0]}",
        f"2) {observations[1]}",
        f"3) {observations[2]}",
        "",
        f"Your stated constraints: budget {budget} · timeline {timeline}.",
        "",
        "If useful, I can send a one-page sprint scope with deliverables, timeline, and fixed price range.",
        recommended_next_step,
        "",
        "Best,",
        "James"
    ]

    return {
        'subject': subject,
        'body': "\n".join(body_lines),
        'recommendedNextStep': recommended_next_step,
        'projectSignals': project_signals,
        'summaryPreview': summary[:320] + ('…' if len(summary) > 320 else '')
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

    project_url = str(data.get('projectUrl', '')).strip()
    if project_url and not re.match(r'^https?://[^\s]+$', project_url, re.IGNORECASE):
        return jsonify({'success': False, 'error': 'Invalid projectUrl format. Use full URL including http(s)://'}), 400

    submitted_at = datetime.now(timezone.utc).isoformat()
    payload = {
        'name': str(data.get('name', '')).strip(),
        'email': email,
        'budget': str(data.get('budget', '')).strip(),
        'timeline': str(data.get('timeline', '')).strip(),
        'projectUrl': project_url[:300],
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
            previous_stage, _ = apply_stage_update(brief, requested_stage, status_notes=status_notes)
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


@app.route('/api/project-briefs/daily-plan', methods=['GET'])
def get_project_briefs_daily_plan():
    """Return a compact daily operator plan for lead follow-up and channel allocation."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    limit = request.args.get('limit', default=200, type=int)
    limit = max(1, min(limit, 1000))

    sla_hours = request.args.get('slaHours', default=24, type=int)
    sla_hours = max(1, min(sla_hours, 168))

    briefs = load_recent_project_briefs(limit=limit)
    plan = build_daily_plan(briefs, sla_hours=sla_hours)

    return jsonify({
        'success': True,
        'limit': limit,
        'plan': plan
    })


@app.route('/api/project-briefs/<brief_id>/first-response-draft', methods=['GET'])
def get_project_brief_first_response_draft(brief_id):
    """Return a URL-aware first response draft to accelerate same-day qualification replies."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    briefs = load_all_project_briefs()
    target_brief = None

    for brief in briefs:
        candidate_id = brief.get('briefId')
        if not candidate_id:
            identity_seed = f"{brief.get('email', 'unknown')}|{brief.get('submittedAt', '')}|{brief.get('name', '')}"
            candidate_id = compute_hash(identity_seed)
            brief['briefId'] = candidate_id

        if candidate_id == brief_id:
            target_brief = brief
            break

    if not target_brief:
        return jsonify({'success': False, 'error': 'Brief not found'}), 404

    draft = build_first_response_draft(target_brief)

    return jsonify({
        'success': True,
        'briefId': brief_id,
        'stage': target_brief.get('stage', 'new'),
        'priority': target_brief.get('priority', 'low'),
        'draft': draft
    })


@app.route('/api/project-briefs/<brief_id>/first-response-send', methods=['POST'])
def send_project_brief_first_response(brief_id):
    """Send first response via lead SMTP and optionally mark lead as contacted."""
    auth_error = authorize_dashboard_request()
    if auth_error:
        return auth_error

    briefs = load_all_project_briefs()
    target_brief = None

    for brief in briefs:
        candidate_id = brief.get('briefId')
        if not candidate_id:
            identity_seed = f"{brief.get('email', 'unknown')}|{brief.get('submittedAt', '')}|{brief.get('name', '')}"
            candidate_id = compute_hash(identity_seed)
            brief['briefId'] = candidate_id

        if candidate_id == brief_id:
            target_brief = brief
            break

    if not target_brief:
        return jsonify({'success': False, 'error': 'Brief not found'}), 404

    recipient = (target_brief.get('email') or '').strip()
    if not recipient:
        return jsonify({'success': False, 'error': 'Brief has no recipient email'}), 400

    data = request.json or {}
    draft = build_first_response_draft(target_brief)
    subject = str(data.get('subject') or draft.get('subject') or '').strip()
    body = str(data.get('body') or draft.get('body') or '').strip()

    if not subject or not body:
        return jsonify({'success': False, 'error': 'Unable to send: missing subject or body'}), 400

    send_result = send_email_via_lead_smtp(recipient, subject, body)
    if not send_result.get('sent'):
        return jsonify({
            'success': False,
            'error': 'Failed to send first response',
            'email': send_result
        }), 503

    mark_contacted = data.get('markContacted', True)
    stage_updated = False
    previous_stage = target_brief.get('stage', 'new')

    if mark_contacted and previous_stage == 'new':
        status_notes = str(data.get('statusNotes', '')).strip()
        default_note = f"First response sent via API at {datetime.now(timezone.utc).isoformat()}"
        combined_notes = f"{default_note}. {status_notes}".strip() if status_notes else default_note
        apply_stage_update(target_brief, 'contacted', status_notes=combined_notes)
        stage_updated = True

    if stage_updated:
        save_all_project_briefs(briefs)

    return jsonify({
        'success': True,
        'briefId': brief_id,
        'email': send_result,
        'stage': target_brief.get('stage', 'new'),
        'stageUpdated': stage_updated,
        'previousStage': previous_stage,
        'draftUsed': {
            'subject': subject,
            'recommendedNextStep': draft.get('recommendedNextStep', '')
        }
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
