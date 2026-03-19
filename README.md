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

## Lead Ops Console

Open `/lead-ops` in the browser for a lightweight daily operator console that connects directly to lead APIs.

What it supports:
- Pulls `GET /api/project-briefs/follow-up-queue` with configurable SLA window.
- One-click first-response execution via `POST /api/project-briefs/<briefId>/first-response-send`.
- One-click stage-aware follow-up via `POST /api/project-briefs/<briefId>/follow-up-send`.
- Stage updates via `PATCH /api/project-briefs/<briefId>`.
- On-demand draft preview via `GET /api/project-briefs/<briefId>/first-response-draft`.

The page asks for `LEAD_DASHBOARD_TOKEN` client-side and sends Bearer auth on each API call.

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
  "projectUrl": "https://startup.com",
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
  },
  "alert": {
    "sent": true,
    "status": 200
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
- `LEAD_ALERT_WEBHOOK_URL` (optional webhook for instant lead/stage alerts)
- `LEAD_ALERT_MIN_PRIORITY` (`low|medium|high`, default `high`)

`projectUrl` is optional but recommended for faster qualification.

When `LEAD_ALERT_WEBHOOK_URL` is set, new leads above the configured threshold trigger a webhook POST with:
`eventType`, `briefId`, `name`, `email`, `priority`, `stage`, `source`, `budget`, `timeline`, `projectUrl`, `leadScore`, timestamps, and a summary preview.

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
      "projectUrl": "https://startup.com",
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

When a lead is first moved into any follow-up stage (`contacted`, `qualified`, `proposal_sent`, `won`, `lost`), the API also stores:
- `contactedAt`
- `firstResponseHours` (hours between `submittedAt` and first contact)

If `LEAD_ALERT_WEBHOOK_URL` is set, stage changes into `proposal_sent`, `won`, or `lost` also emit a webhook event (`eventType: lead.stage_updated`) so pipeline movement is visible immediately.

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
    },
    "responseSLA": {
      "contactedLeads": 7,
      "respondedWithin24h": 5,
      "respondedWithin24hRate": 71.43,
      "avgFirstResponseHours": 18.6
    }
  }
}
```

### GET /api/project-briefs/source-performance
Returns per-channel performance so outreach can be reallocated toward sources that produce proposals and wins (not just raw lead volume).

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Query params:**
- `limit` (1-1000, default 200)

**Response:**
```json
{
  "success": true,
  "limit": 200,
  "performance": [
    {
      "source": "linkedin",
      "total": 12,
      "highPriority": 5,
      "contacted": 8,
      "qualified": 6,
      "proposalSent": 4,
      "won": 2,
      "lost": 1,
      "winRateFromTotal": 16.67,
      "proposalRateFromTotal": 33.33,
      "closeRateFromProposal": 50.0,
      "respondedWithin24h": 6,
      "responseWithin24hRate": 75.0,
      "avgFirstResponseHours": 14.2
    }
  ]
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

### GET /api/project-briefs/daily-plan
Returns a single operator-focused plan that combines follow-up urgency with source allocation guidance.

Allocation guidance is sample-aware:
- `scale`: reliable channels with enough volume + proposal history
- `deprioritize`: reliable channels with sustained low conversion
- `test`: low-sample channels that need controlled experiments before budget/time shifts

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Query params:**
- `limit` (1-1000, default 200)
- `slaHours` (1-168, default 24)

**Response:**
```json
{
  "success": true,
  "limit": 200,
  "plan": {
    "slaHours": 24,
    "openLeads": 8,
    "overdueLeads": 3,
    "topActions": [
      {
        "briefId": "7f1ad2c4e92a31b8",
        "name": "Jane Founder",
        "priority": "high",
        "stage": "qualified",
        "source": "linkedin",
        "hoursSinceStageUpdate": 31.6,
        "recommendedAction": "Send scoped proposal and confirm decision timeline"
      }
    ],
    "sourceRecommendations": [
      "SCALE: linkedin — Highest reliable conversion: closeRateFromProposal=50.0%, proposalRateFromTotal=33.33% across 12 leads.",
      "DEPRIORITIZE: x — Sustained low yield: 0 wins and proposalRateFromTotal=12.5% over 8 leads.",
      "TEST: referral — Insufficient sample (2 leads). Run a controlled test before scaling or cutting."
    ],
    "sourceRecommendationDetails": [
      {
        "action": "scale",
        "source": "linkedin",
        "reason": "Highest reliable conversion: closeRateFromProposal=50.0%, proposalRateFromTotal=33.33% across 12 leads."
      }
    ],
    "executionNotes": [
      "Clear overdue queue first: 3 leads beyond 24h SLA."
    ]
  }
}
```

### GET /api/project-briefs/<briefId>/first-response-draft
Returns a ready-to-send, URL-aware first response draft for a specific lead so high-intent briefs can be answered in minutes (not hours).

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Behavior:**
- Pulls the stored brief (`budget`, `timeline`, `summary`, `projectUrl`, `priority`).
- If `projectUrl` exists, attempts lightweight page signal extraction (`title`, first `h1`, meta description).
- Generates a structured response draft with 3 observations + recommended next step.

**Response:**
```json
{
  "success": true,
  "briefId": "7f1ad2c4e92a31b8",
  "stage": "new",
  "priority": "high",
  "draft": {
    "subject": "Re: your project brief — suggested first sprint",
    "body": "Hi Jane...",
    "recommendedNextStep": "Given urgency/fit, I recommend a 20-minute scope call today/tomorrow to lock sprint scope and start this week.",
    "projectSignals": {
      "available": true,
      "title": "Startup — Revenue Ops Platform",
      "metaDescription": "...",
      "h1": "Stop leaking pipeline",
      "url": "https://startup.com"
    },
    "summaryPreview": "Need conversion-focused rebuild + analytics..."
  }
}
```

### POST /api/project-briefs/<briefId>/first-response-send
Sends a first-response email directly to the lead using configured `LEAD_SMTP_*` settings, with optional overrides to the generated subject/body.

This lets the operator go from queue -> draft -> sent reply in one API flow.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Request (optional fields):**
```json
{
  "subject": "Optional override subject",
  "body": "Optional override body",
  "markContacted": true,
  "statusNotes": "Sent first response + asked for analytics access"
}
```

**Behavior:**
- Uses generated draft if `subject` and/or `body` are not provided.
- Sends to the brief's stored `email` via lead SMTP.
- If `markContacted=true` (default) and current stage is `new`, automatically moves lead to `contacted` and writes a timestamped status note.

**Response:**
```json
{
  "success": true,
  "briefId": "7f1ad2c4e92a31b8",
  "email": {"sent": true},
  "stage": "contacted",
  "stageUpdated": true,
  "previousStage": "new",
  "draftUsed": {
    "subject": "Re: your project brief — suggested first sprint",
    "recommendedNextStep": "Given urgency/fit, I recommend a 20-minute scope call today/tomorrow to lock sprint scope and start this week."
  }
}
```

### POST /api/project-briefs/<briefId>/follow-up-send
Sends a stage-aware follow-up email for stalled opportunities in `contacted`, `qualified`, or `proposal_sent`.

Use this to recover warm leads that have gone quiet without manually drafting each nudge.

**Auth:**
`Authorization: Bearer <LEAD_DASHBOARD_TOKEN>`

**Request (optional fields):**
```json
{
  "subject": "Optional override subject",
  "body": "Optional override body",
  "statusNotes": "Asked for decision by Friday"
}
```

**Behavior:**
- Builds a follow-up draft from the lead's current stage if no override is provided.
- Sends via configured lead SMTP settings.
- Appends a timestamped note and updates `lastFollowUpSentAt` + `stageUpdatedAt`.
- Keeps stage unchanged (this endpoint is for progression nudges, not stage transitions).

**Response:**
```json
{
  "success": true,
  "briefId": "7f1ad2c4e92a31b8",
  "email": {"sent": true},
  "stage": "qualified",
  "followUpSentAt": "2026-03-19T05:38:00.000000+00:00",
  "draftUsed": {
    "subject": "Shall I send the scoped proposal?",
    "stage": "qualified"
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
