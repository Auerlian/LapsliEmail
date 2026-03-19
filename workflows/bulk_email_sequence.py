#!/usr/bin/env python3
"""Simple CSV-driven bulk email sequence workflow.

Uses existing LapsliEmail components where possible:
- services.template_engine.TemplateEngine for token rendering
- providers.smtp.SMTPProvider for SMTP delivery

Default mode is dry-run (safe preview). Use --send to actually deliver.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is importable when running from workflows/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Reuse existing app modules
from services.template_engine import TemplateEngine


@dataclass
class SequenceStep:
    id: str
    subject: str
    text_body: str
    html_body: str | None = None


def load_csv_leads(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")

        normalized = [h.strip() for h in reader.fieldnames if h]
        if "email" not in [h.lower() for h in normalized]:
            raise ValueError("CSV must include an 'email' column")

        rows: List[Dict[str, str]] = []
        for i, row in enumerate(reader, start=2):
            clean: Dict[str, str] = {}
            for k, v in row.items():
                key = (k or "").strip()
                if not key:
                    continue
                clean[key] = (v or "").strip()

            email_key = next((k for k in clean.keys() if k.lower() == "email"), None)
            if not email_key or not clean.get(email_key):
                continue

            clean["email"] = clean[email_key].strip().lower()
            clean["row_number"] = str(i)
            rows.append(clean)

    # de-dupe by email, keep first
    seen = set()
    unique_rows = []
    for row in rows:
        email = row["email"]
        if email in seen:
            continue
        seen.add(email)
        unique_rows.append(row)

    return unique_rows


def load_sequence(sequence_path: Path) -> List[SequenceStep]:
    data = json.loads(sequence_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Sequence file must be a non-empty JSON array")

    steps: List[SequenceStep] = []
    base_dir = sequence_path.parent

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Step {idx} must be an object")

        step_id = str(item.get("id") or f"step-{idx}")
        subject = str(item.get("subject") or "").strip()
        text_body = ""

        if item.get("text_body"):
            text_body = str(item["text_body"])
        elif item.get("text_body_file"):
            text_file = (base_dir / str(item["text_body_file"])).resolve()
            text_body = text_file.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Step '{step_id}' needs text_body or text_body_file")

        html_body = None
        if item.get("html_body"):
            html_body = str(item["html_body"])
        elif item.get("html_body_file"):
            html_file = (base_dir / str(item["html_body_file"])).resolve()
            html_body = html_file.read_text(encoding="utf-8")

        if not subject:
            raise ValueError(f"Step '{step_id}' is missing subject")

        steps.append(SequenceStep(id=step_id, subject=subject, text_body=text_body, html_body=html_body))

    return steps


def render_with_tokens(template: str, variables: Dict[str, Any]) -> str:
    """Support {token} plus existing [token] and {{token}} syntaxes."""
    rendered = TemplateEngine.render(template, variables)
    for key, value in variables.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def build_smtp_config(args: argparse.Namespace) -> Dict[str, Any]:
    host = args.smtp_host or os.getenv("SMTP_HOST") or ""
    port = int(args.smtp_port or os.getenv("SMTP_PORT") or 587)
    username = args.smtp_user or os.getenv("SMTP_USER") or ""
    password = args.smtp_pass or os.getenv("SMTP_PASS") or ""

    missing = []
    if not host:
        missing.append("smtp-host / SMTP_HOST")
    if not username:
        missing.append("smtp-user / SMTP_USER")
    if not password:
        missing.append("smtp-pass / SMTP_PASS")

    if missing:
        raise ValueError("Missing SMTP settings: " + ", ".join(missing))

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
    }


def send_via_smtp(
    smtp_config: Dict[str, Any],
    from_email: str,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None,
) -> Dict[str, Any]:
    try:
        message = MIMEMultipart("alternative")
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject

        if text_body:
            message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body or text_body, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_config["host"], int(smtp_config["port"]), timeout=60) as server:
            server.starttls(context=context)
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(from_email, to_email, message.as_string())

        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def send_with_backoff(
    smtp_config: Dict[str, Any],
    from_email: str,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None,
    retries: int,
    base_backoff: float,
) -> Dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        result = send_via_smtp(
            smtp_config=smtp_config,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        if result.get("success"):
            result["attempt"] = attempt
            return result

        if attempt > retries:
            result["attempt"] = attempt
            return result

        sleep_for = base_backoff * (2 ** (attempt - 1))
        time.sleep(sleep_for)


def run(args: argparse.Namespace) -> int:
    leads = load_csv_leads(Path(args.leads_csv))
    steps = load_sequence(Path(args.sequence_json))

    mode = "SEND" if args.send else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"Leads: {len(leads)} | Sequence steps: {len(steps)}")

    if not leads:
        print("No leads found after validation/dedup. Nothing to do.")
        return 0

    smtp_config = None
    if args.send:
        smtp_config = build_smtp_config(args)

    interval_seconds = 60.0 / max(1, args.rate_per_minute)
    from_email = args.from_email or os.getenv("FROM_EMAIL")
    if args.send and not from_email:
        raise ValueError("Missing from email: pass --from-email or set FROM_EMAIL")

    results: List[Dict[str, Any]] = []
    total_messages = len(leads) * len(steps)
    sent_counter = 0

    for lead in leads:
        tokens = dict(lead)
        tokens.setdefault("name", tokens.get("first_name") or "there")

        for step in steps:
            rendered_subject = render_with_tokens(step.subject, tokens)
            rendered_text = render_with_tokens(step.text_body, tokens)
            rendered_html = render_with_tokens(step.html_body, tokens) if step.html_body else None

            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "lead_email": lead.get("email"),
                "step_id": step.id,
                "subject": rendered_subject,
                "status": "dry_run",
                "attempt": 0,
                "error": None,
            }

            if args.send and smtp_config:
                result = send_with_backoff(
                    smtp_config=smtp_config,
                    from_email=from_email,
                    to_email=lead["email"],
                    subject=rendered_subject,
                    text_body=rendered_text,
                    html_body=rendered_html,
                    retries=args.retries,
                    base_backoff=args.backoff_seconds,
                )
                entry["attempt"] = result.get("attempt", 1)
                if result.get("success"):
                    entry["status"] = "sent"
                else:
                    entry["status"] = "failed"
                    entry["error"] = result.get("error")

                sent_counter += 1
                if sent_counter < total_messages:
                    time.sleep(interval_seconds)
            else:
                preview = rendered_text[:160].replace("\n", " ")
                print(f"[DRY-RUN] {lead['email']} | {step.id} | {rendered_subject} | {preview}...")

            results.append(entry)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_json = output_dir / f"bulk-sequence-results-{stamp}.json"
    out_csv = output_dir / f"bulk-sequence-results-{stamp}.csv"

    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "lead_email", "step_id", "subject", "status", "attempt", "error"])
        writer.writeheader()
        writer.writerows(results)

    sent = sum(1 for r in results if r["status"] == "sent")
    failed = sum(1 for r in results if r["status"] == "failed")
    dry = sum(1 for r in results if r["status"] == "dry_run")

    print("\nDone.")
    print(f"Sent: {sent} | Failed: {failed} | Dry-run: {dry}")
    print(f"Results JSON: {out_json}")
    print(f"Results CSV:  {out_csv}")

    return 0 if failed == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a CSV-driven bulk email sequence (default: dry-run)."
    )
    parser.add_argument("--leads-csv", required=True, help="Path to leads CSV (must include email column)")
    parser.add_argument("--sequence-json", required=True, help="Path to sequence JSON definition")
    parser.add_argument("--from-email", help="From address (or env FROM_EMAIL)")

    parser.add_argument("--send", action="store_true", help="Actually send emails (otherwise dry-run preview)")
    parser.add_argument("--rate-per-minute", type=int, default=20, help="Rate limit in emails/minute (default: 20)")
    parser.add_argument("--retries", type=int, default=3, help="Retries for failed sends (default: 3)")
    parser.add_argument("--backoff-seconds", type=float, default=2.0, help="Base backoff seconds (default: 2.0)")

    parser.add_argument("--smtp-host", help="SMTP host (or env SMTP_HOST)")
    parser.add_argument("--smtp-port", type=int, help="SMTP port (or env SMTP_PORT, default 587)")
    parser.add_argument("--smtp-user", help="SMTP username (or env SMTP_USER)")
    parser.add_argument("--smtp-pass", help="SMTP password (or env SMTP_PASS)")

    parser.add_argument("--output-dir", default="out", help="Output directory for run results (default: out)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
