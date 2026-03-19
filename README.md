# Bulk Email Sender with HTML Support

A Flask-based web application for sending personalized bulk emails via Brevo SMTP with HTML template support.

## Features

✅ **HTML Email Support** - Send beautiful HTML emails with inline CSS
✅ **Personalization** - Use `{name}` and `[University Name]` tokens
✅ **Brevo SMTP Integration** - Pre-configured for Brevo (smtp-relay.brevo.com)
✅ **Test Mode** - Preview emails without sending (dry-run)
✅ **Custom From Address** - Set sender email separate from SMTP login
✅ **Recipient Management** - Support for email, name, and university fields
✅ **Template Loading** - Load HTML templates from file
✅ **Real-time Logging** - Track send status per recipient
✅ **Error Handling** - Detailed error messages per recipient
✅ **Security** - Password masking, no hardcoded credentials

## Quick Start

```bash
# Install dependencies
pip3 install flask

# Run the app
python3 app.py

# Open browser
http://127.0.0.1:5000
```

## Configuration

### SMTP Settings (Brevo)
- Server: `smtp-relay.brevo.com`
- Port: `587`
- Login: Your Brevo SMTP login (e.g., `9c36a5001@smtp-brevo.com`)
- Password: Your Brevo SMTP password
- From: `hello@morningbuddy.co.uk` (or your verified sender)

### Recipient Format
```
email@domain.com, Name, University
```

Examples:
```
James@Lapslie.com, James, Lapslie University
admissions@mit.edu, MIT Admissions, MIT
contact@stanford.edu, Stanford Team, Stanford University
```

## Usage

### 1. Configure SMTP (Settings Tab)
Enter your Brevo SMTP credentials and sender email.

### 2. Add Recipients (Recipients Tab)
Paste your recipient list (one per line) and click "Validate & Clean List".

### 3. Compose Email (Compose & Send Tab)
- Toggle "Send as HTML" for HTML emails
- Use personalization tokens: `{name}` and `[University Name]`
- Load template from file or write your own
- Click "Test Mode" to preview without sending
- Click "Send All Emails" to send

## Personalization

### Available Tokens
- `{name}` - Replaced with recipient's name
- `[University Name]` - Replaced with recipient's university

### Example Subject
```
Hello {name} from Morning Buddy
```

### Example HTML Body
```html
<h1>Dear {name},</h1>
<p>We're excited to connect with [University Name]!</p>
```

## Test Mode

Test mode (dry-run) allows you to:
- Preview personalized content without sending
- Verify token replacement
- Check HTML rendering
- View rendered HTML in browser console

## Files Structure

```
.
├── app.py                          # Flask backend
├── templates/
│   ├── index.html                  # Web UI
│   └── email_template.html         # HTML email template
├── static/
│   └── email.html                  # Loadable template
├── CHANGELOG.md                    # Detailed changes
├── TEST_INSTRUCTIONS.md            # Complete test guide
├── QUICK_START.md                  # Quick reference
└── README.md                       # This file
```

## Testing

### Send Test Email
1. Add recipient: `James@Lapslie.com, James, Lapslie University`
2. Enable "Send as HTML"
3. Click "Load from email.html"
4. Subject: `Hello {name} from Morning Buddy`
5. Click "Test Mode (Preview Only)" first
6. Check browser console for rendered HTML
7. Click "Send All Emails" to send

### Verify Email
Check that:
- Email arrives at James@Lapslie.com
- HTML renders (banner, button, styles)
- "James" appears in greeting
- "Lapslie University" appears in body
- Links are clickable
- From address is correct

## Security

- ✅ No hardcoded credentials
- ✅ Password masking in UI
- ✅ Passwords not logged
- ✅ UTF-8 encoding
- ✅ Test mode for safe testing

### Production Recommendations
- Use environment variables for credentials
- Add rate limiting
- Add unsubscribe footer
- Add open/click tracking
- Use production WSGI server
- Store send logs
- Handle bounces

## API Endpoints

### POST /validate_recipients
Validates and cleans recipient list.

**Request:**
```json
{
  "recipients": "email, name, university\n..."
}
```

**Response:**
```json
{
  "count": 3,
  "recipients": [
    {"email": "...", "name": "...", "university": "..."}
  ]
}
```

### POST /api/project-brief
Captures freelance leads from Lapslie.com, scores priority, logs them to `data/project_briefs.jsonl`, and can send instant emails.

**Request:**
```json
{
  "name": "Jane Founder",
  "email": "jane@startup.com",
  "budget": "£2,500–£5,000",
  "timeline": "Within 1 month",
  "summary": "Need conversion-focused rebuild + analytics",
  "website": "",
  "source": "lapslie.com",
  "utmSource": "linkedin",
  "utmMedium": "dm",
  "utmCampaign": "march-outbound",
  "utmContent": "founder-offer-v1",
  "utmTerm": "freelance developer",
  "referrer": "https://www.linkedin.com/",
  "landingPath": "/"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project brief received",
  "briefId": "7f1ad2c4e92a31b8",
  "priority": "high",
  "leadScore": 11,
  "stage": "new",
  "notification": {
    "sent": true
  },
  "acknowledgement": {
    "sent": true
  }
}
```

Optional lead-system env vars:
- `LEAD_SMTP_SERVER`
- `LEAD_SMTP_PORT` (default `587`)
- `LEAD_SMTP_USER`
- `LEAD_SMTP_PASS`
- `LEAD_FROM_EMAIL`
- `LEAD_TO_EMAIL` (default `james@lapslie.com`)
- `LEAD_ACK_ENABLED` (default `true`)
- `LEAD_CALENDLY_URL` (default `https://calendly.com/lapslie/30min`)
- `LEAD_DASHBOARD_TOKEN` (required for secure lead inbox + summary endpoints)

### GET /api/project-briefs
Returns recent project briefs for lightweight CRM/inbox use.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Query params:**
- `limit` (1-100, default 25)

**Response:**
```json
{
  "success": true,
  "count": 2,
  "briefs": [
    {
      "briefId": "7f1ad2c4e92a31b8",
      "name": "Jane Founder",
      "email": "jane@startup.com",
      "budget": "£5,000–£10,000",
      "timeline": "Within 2 weeks",
      "summary": "Need landing page + analytics sprint",
      "priority": "high",
      "leadScore": 10,
      "stage": "new",
      "stageUpdatedAt": "2026-03-19T00:00:00+00:00",
      "statusNotes": "",
      "submittedAt": "2026-03-19T00:00:00+00:00"
    }
  ]
}
```

### PATCH /api/project-briefs/<briefId>
Update a lead's pipeline status after outreach/follow-up.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Request:**
```json
{
  "stage": "proposal_sent",
  "statusNotes": "Sent scoped 2-week sprint proposal. Follow up Friday."
}
```

Allowed `stage` values:
- `new`
- `contacted`
- `qualified`
- `proposal_sent`
- `won`
- `lost`

### GET /api/project-briefs/summary
Returns a quick attribution + quality + pipeline summary so you can see which channels are generating high-priority leads and whether they are converting.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Query params:**
- `limit` (1-1000, default 100)

**Response:**
```json
{
  "success": true,
  "limit": 100,
  "summary": {
    "total": 12,
    "byPriority": {"high": 5, "medium": 4, "low": 3},
    "bySource": {"linkedin": 6, "lapslie.com": 4, "x": 2},
    "byStage": {
      "new": 4,
      "contacted": 3,
      "qualified": 2,
      "proposal_sent": 2,
      "won": 1,
      "lost": 0
    }
  }
}
```

### GET /api/project-briefs/follow-up-queue
Returns open leads ranked by urgency so you can enforce a response SLA and focus on the highest-leverage follow-ups first.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Query params:**
- `limit` (1-500, default 100)
- `slaHours` (1-168, default 24)

**Response:**
```json
{
  "success": true,
  "limit": 100,
  "followUp": {
    "slaHours": 24,
    "openLeads": 5,
    "overdueLeads": 2,
    "queue": [
      {
        "briefId": "7f1ad2c4e92a31b8",
        "name": "Jane Founder",
        "email": "jane@startup.com",
        "priority": "high",
        "stage": "qualified",
        "source": "linkedin",
        "hoursSinceStageUpdate": 31.6,
        "overdue": true,
        "recommendedAction": "Send scoped proposal and confirm decision timeline",
        "urgencyScore": 8
      }
    ]
  }
}
```

### POST /send_emails
Sends emails to recipients.

**Request:**
```json
{
  "smtp_server": "smtp-relay.brevo.com",
  "smtp_port": 587,
  "email_user": "9c36a5001@smtp-brevo.com",
  "email_pass": "password",
  "from_email": "hello@morningbuddy.co.uk",
  "subject": "Hello {name}",
  "body": "Plain text body",
  "html_body": "<html>...</html>",
  "send_as_html": true,
  "delay": 3,
  "dry_run": false,
  "recipients": "email, name, university\n..."
}
```

**Response:**
```json
{
  "success": true,
  "sent": 3,
  "total": 3,
  "dry_run": false,
  "results": [
    {
      "email": "...",
      "name": "...",
      "university": "...",
      "status": "success",
      "message": "Sent successfully"
    }
  ]
}
```

## Troubleshooting

### Email not arriving
- Check spam folder
- Verify Brevo credentials
- Check Brevo dashboard
- Verify sender email is authorized

### HTML not rendering
- Check email client compatibility
- View email source
- Test in different clients

### Personalization not working
- Verify exact token format
- Check recipient format
- Use test mode to preview

## Next Steps

Want to add:
- Open/click tracking
- Unsubscribe footer
- Bounce handling
- Send logs
- Analytics

Let me know and I'll provide the next prompt!

## License

MIT License - Use freely for your projects.

## Support

For issues or questions, check:
- TEST_INSTRUCTIONS.md for detailed testing
- CHANGELOG.md for recent changes
- QUICK_START.md for quick reference
