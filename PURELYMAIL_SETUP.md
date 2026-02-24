# Purelymail Setup Guide

## Quick Start

Your email platform is running at: **http://127.0.0.1:5001**

## Step 1: Login
- Go to http://127.0.0.1:5001/auth/login
- Email: `test@example.com`
- Password: `password123`

## Step 2: Add Purelymail Provider

1. Go to **Providers** page: http://127.0.0.1:5001/providers
2. Click "Add Provider"
3. Select **SMTP**
4. Fill in Purelymail SMTP settings:

```
Provider Type: SMTP
Sender Email: your@domain.com (your Purelymail email)
Sender Name: Your Name

SMTP Settings:
- Host: smtp.purelymail.com
- Port: 587
- Username: your@domain.com (your Purelymail email)
- Password: (your Purelymail password or app-specific password)
```

5. Click "Save" then "Verify"

## Step 3: Create Recipient List

1. Go to **Lists** page: http://127.0.0.1:5001/lists
2. Click "Create List"
3. Upload CSV with columns: `email,name` (or any custom fields)
4. Example CSV:
```csv
email,name
recipient1@example.com,John Doe
recipient2@example.com,Jane Smith
```

## Step 4: Create Campaign

1. Go to **Campaign Wizard**: http://127.0.0.1:5001/campaigns/wizard
2. Fill in:
   - Campaign Name
   - Select your Purelymail provider
   - Select your recipient list
   - Subject line (supports variables: `{{name}}`)
   - HTML Body (your custom HTML template)
3. Click "Validate" to check for issues
4. Click "Create & Send"

## HTML Template Variables

Use `{{variable_name}}` in your subject and body:
- `{{email}}` - recipient email
- `{{name}}` - recipient name
- Any custom CSV columns

Example:
```html
<h1>Hello {{name}}!</h1>
<p>This email was sent to {{email}}</p>
```

## Purelymail Notes

- Default rate limit: 100 emails/hour (configurable in provider settings)
- Supports HTML and plain text
- TLS encryption enabled by default
- No OAuth required - simple SMTP authentication

## Troubleshooting

If verification fails:
1. Check your Purelymail credentials
2. Ensure SMTP is enabled in your Purelymail account
3. Try using an app-specific password if available
4. Check port 587 is not blocked by firewall

## Test the System

Run this to check your setup:
```bash
python test_email_flow.py
```
