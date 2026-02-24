# Bulk Email Platform - Complete Setup Guide

## ✓ Migration Fixed

The schema mismatch error has been resolved. All database columns are now in place.

## Quick Commands

### Start the Application
```bash
python app_production.py
```

### If You Get Schema Errors
```bash
python manual_migration.py
```

### Future Schema Changes
```bash
export FLASK_APP=app_production.py
flask db migrate -m "Description"
flask db upgrade
```

## What's New

### Production Features
- ✓ Multi-provider support (Gmail, SendGrid, Mailgun, SES, Brevo, SMTP)
- ✓ Campaign wizard with 5-step validation
- ✓ Template management (save/edit/delete)
- ✓ Suppression list enforcement
- ✓ AI-assisted email generation (with privacy controls)
- ✓ Rate limiting and security controls
- ✓ Daily send caps per user
- ✓ Provider health monitoring

### Database Improvements
- ✓ Flask-Migrate integration
- ✓ Proper schema versioning
- ✓ Safe migrations without data loss
- ✓ Rollback capability

## File Structure

```
.
├── app_production.py          # Main application with Flask-Migrate
├── manual_migration.py        # Quick fix for schema issues
├── setup.py                   # Automated setup script
├── requirements.txt           # Dependencies (includes Flask-Migrate)
│
├── models/                    # Database models
│   ├── user.py               # User with send limits
│   ├── provider.py           # Provider with health status
│   ├── campaign.py           # Campaign with scheduling
│   ├── template.py           # Email templates (NEW)
│   ├── suppression.py        # Suppression list (NEW)
│   └── recipient_list.py     # Recipient lists
│
├── routes/                    # API endpoints
│   ├── providers.py          # Provider management
│   ├── lists.py              # List management
│   ├── templates.py          # Template management
│   ├── campaigns.py          # Campaign wizard
│   └── suppression.py        # Suppression management (NEW)
│
├── services/                  # Business logic
│   ├── provider_factory.py   # Provider creation (NEW)
│   ├── template_engine.py    # Template rendering
│   ├── csv_import.py         # CSV parsing
│   ├── sending_queue.py      # Email sending (NEW)
│   └── ai_assistant.py       # AI generation (UPDATED)
│
├── providers/                 # Email provider implementations
│   ├── base.py               # Base provider interface
│   ├── gmail.py              # Gmail OAuth (NEW)
│   ├── brevo.py              # Brevo API
│   ├── sendgrid.py           # SendGrid API
│   ├── mailgun.py            # Mailgun API
│   ├── ses.py                # AWS SES
│   └── smtp.py               # Generic SMTP
│
├── templates/                 # HTML templates
│   ├── campaign_wizard.html  # Campaign wizard UI (NEW)
│   └── ...
│
├── static/
│   └── js/
│       └── campaign_wizard.js # Wizard logic (NEW)
│
└── Documentation
    ├── QUICKSTART.md          # Quick start guide
    ├── MIGRATION_GUIDE.md     # Detailed migration docs
    ├── MIGRATION_SUCCESS.md   # Migration completion status
    ├── PRODUCTION_UPGRADE.md  # Feature documentation
    └── README_MIGRATION.md    # Migration quick fix
```

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Option A: Automated (recommended)
python setup.py

# Option B: Manual migration
python manual_migration.py

# Option C: Flask-Migrate
export FLASK_APP=app_production.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Start Application
```bash
python app_production.py
```

## Configuration

Edit `.env`:

```env
# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# Database
DATABASE_URL=sqlite:///platform.db

# OAuth (Gmail)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# AI Providers (optional)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-claude-key
GOOGLE_AI_API_KEY=your-gemini-key

# Limits
DEFAULT_SEND_RATE=100
MAX_RECIPIENTS_PER_CAMPAIGN=10000
```

## Usage

### 1. Add Email Provider
Navigate to `/providers` and configure:
- Gmail (OAuth flow)
- SendGrid (API key)
- Mailgun (API key + domain)
- AWS SES (access key + secret + region)
- Brevo (API key)
- SMTP (host + port + credentials)

### 2. Upload Recipients
Navigate to `/lists`:
- Upload CSV file
- Map columns
- Review validation summary
- Save list

### 3. Create Template
Navigate to `/templates`:
- Create new template
- Use `{{variable}}` syntax
- Add plain text fallback
- Check spam score
- Save template

### 4. Launch Campaign
Navigate to `/campaigns/wizard`:
1. Select verified provider
2. Select recipient list
3. Select or create template
4. Review validation results
5. Send immediately or schedule

## API Endpoints

### Providers
- `GET /providers/schemas` - Get credential schemas
- `GET /providers/list` - List providers
- `POST /providers/add` - Add provider
- `POST /providers/<id>/verify` - Verify provider
- `DELETE /providers/<id>` - Delete provider

### Lists
- `GET /lists/list` - List recipient lists
- `POST /lists/parse` - Parse CSV
- `POST /lists/create` - Create list
- `GET /lists/<id>` - Get list
- `DELETE /lists/<id>` - Delete list

### Templates
- `GET /templates/list` - List templates
- `POST /templates/save` - Save template
- `GET /templates/<id>` - Get template
- `DELETE /templates/<id>` - Delete template
- `POST /templates/validate` - Validate template
- `POST /templates/preview` - Preview with variables
- `POST /templates/spam-check` - Check spam score
- `POST /templates/ai/generate` - AI generation

### Campaigns
- `GET /campaigns/wizard` - Campaign wizard
- `POST /campaigns/wizard/validate` - Validate campaign
- `POST /campaigns/create` - Create campaign
- `POST /campaigns/<id>/send` - Send campaign
- `GET /campaigns/<id>/logs` - Get logs

### Suppression
- `GET /suppression/list` - List suppressions
- `POST /suppression/add` - Add email
- `POST /suppression/bulk` - Bulk add
- `DELETE /suppression/<id>` - Remove

## Security Features

1. **Credential Encryption** - All API keys encrypted at rest
2. **Provider Verification** - Must verify before sending
3. **Daily Send Limits** - Per-user send caps
4. **Suppression Lists** - Automatic enforcement
5. **Spam Detection** - Pre-send content analysis
6. **AI Privacy** - Only variable schema sent, never recipient data
7. **Rate Limiting** - Per-provider and per-user limits

## Troubleshooting

### Schema Error
```bash
python manual_migration.py
```

### Database Locked
Stop all app instances, then restart.

### Provider Verification Fails
Check API keys and credentials in `.env`.

### Emails Not Sending
1. Verify provider is connected
2. Check daily send limit
3. Review campaign logs

### Reset Database
```bash
rm instance/platform.db
python manual_migration.py
```

## Development

### Run Tests
```bash
pytest
```

### Make Schema Changes
1. Edit model files
2. Generate migration:
   ```bash
   export FLASK_APP=app_production.py
   flask db migrate -m "Description"
   ```
3. Review migration file
4. Apply migration:
   ```bash
   flask db upgrade
   ```

### Debug Mode
```bash
export FLASK_ENV=development
python app_production.py
```

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app_production:app
```

### Using Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manual_migration.py
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app_production:app"]
```

### Environment
- Set `FLASK_ENV=production`
- Use PostgreSQL instead of SQLite
- Set up Redis for Celery
- Configure proper logging
- Use HTTPS
- Set up monitoring

## Documentation

- `QUICKSTART.md` - Quick start guide
- `MIGRATION_GUIDE.md` - Detailed migration documentation
- `MIGRATION_SUCCESS.md` - Migration completion status
- `PRODUCTION_UPGRADE.md` - Feature documentation
- `README_MIGRATION.md` - Migration quick fix guide

## Support

For issues:
1. Check documentation files
2. Review `app.log`
3. Run `python manual_migration.py`
4. Check database schema with `sqlite3 instance/platform.db ".schema"`

## License

[Your License Here]

## Contributors

[Your Team Here]
