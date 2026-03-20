# Easy Bulk Email Workflow (CSV + Templates)

This is the **non-technical** workflow for running personalized bulk emails safely.

## 1) Prepare your leads CSV

Use a normal spreadsheet export with headers. Required column: `email`

Recommended columns for personalization:
- `name`
- `company`
- `role`
- `city`

Example file: `workflows/examples/leads.sample.csv`

## 2) Edit sequence templates

Sequence config: `workflows/examples/sequence.sample.json`

It points to text/HTML template files:
- `workflows/examples/templates/01_intro.txt`
- `workflows/examples/templates/02_followup.txt`
- `workflows/examples/templates/03_last_call.txt`

Supported personalization tokens:
- `{name}`
- `{company}`
- `{role}`
- `{city}`
- `{brief_link}` and `{call_link}` (tracked links when `--enable-tracked-links` is used)
- `[name]` and `{{name}}` are also supported

## 3) Dry-run first (safe preview)

```bash
cd LapsliEmail
./workflows/run_bulk_sequence_starter.sh
```

This prints previews and writes reports into `out/`.

## 4) Send for real

Set SMTP environment variables and send mode.

> Safety default: send mode is **tracked-link enforced**. If you forget `--enable-tracked-links` (or omit `{brief_link}` / `{call_link}` in templates), the run fails closed.


```bash
cd LapsliEmail
export SMTP_HOST="smtp-relay.brevo.com"
export SMTP_PORT="587"
export SMTP_USER="your_smtp_user"
export SMTP_PASS="your_smtp_password"
export FROM_EMAIL="you@yourdomain.com"

python3 workflows/bulk_email_sequence.py \
  --leads-csv workflows/examples/leads.sample.csv \
  --sequence-json workflows/examples/sequence.sample.json \
  --send \
  --rate-per-minute 20 \
  --retries 3 \
  --backoff-seconds 2 \
  --enable-tracked-links \
  --utm-campaign "mar-2026-founders"
```

## Post-Deploy Lead Funnel Smoke Test (recommended)

Before sending new outbound batches, run a quick end-to-end smoke test:

```bash
cd LapsliEmail
python3 workflows/smoke_test_lead_funnel.py \
  --dashboard-token "$LEAD_DASHBOARD_TOKEN" \
  --base-url "https://lapsliemail-api.onrender.com"
```

What it validates:
- brief creation (`POST /api/project-brief`)
- inbox visibility (`GET /api/project-briefs`)
- first-response draft generation (`GET /api/project-briefs/<briefId>/first-response-draft`)
- attribution capture in summary (`GET /api/project-briefs/summary`)

Tip: run this after each deploy and before high-volume campaigns.

## Daily stalled-lead recovery block (recommended)

Use this to recover warm opportunities that are stuck in `contacted`, `qualified`, or `proposal_sent` for too long.

```bash
cd LapsliEmail
python3 workflows/run_recovery_block.py \
  --dashboard-token "$LEAD_DASHBOARD_TOKEN" \
  --base-url "https://lapsliemail-api.onrender.com" \
  --stale-hours 48
```

Default mode is **dry-run**. It prints exactly which leads would be actioned.

Execute for real:

```bash
python3 workflows/run_recovery_block.py \
  --dashboard-token "$LEAD_DASHBOARD_TOKEN" \
  --send
```

By default, qualified leads get `proposal-send`; contacted/proposal_sent leads get `follow-up-send`.

## What this workflow includes

- CSV lead import + dedupe by email
- Personalization token rendering per lead
- Multi-step sequence template support
- **Dry-run mode by default**
- Send mode with rate limiting (`--rate-per-minute`)
- Retry/backoff (`--retries`, `--backoff-seconds`, exponential)
- Run logs exported to JSON + CSV

## Quick CLI reference

```bash
python3 workflows/bulk_email_sequence.py --help
```

Main options:
- `--leads-csv` (required)
- `--sequence-json` (required)
- `--send` (omit for dry-run)
- `--rate-per-minute 20`
- `--retries 3`
- `--backoff-seconds 2`
- `--smtp-host/--smtp-port/--smtp-user/--smtp-pass` (or env vars)
- `--from-email` (or `FROM_EMAIL` env var)
- `--enable-tracked-links` (build per-lead `{brief_link}` and `{call_link}`)
- `--allow-untracked-send` (escape hatch; bypasses tracked-link enforcement)
- `--utm-source/--utm-medium/--utm-campaign/--utm-content-prefix`
- `--base-brief-url/--base-call-url`
