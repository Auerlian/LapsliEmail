#!/usr/bin/env python3
"""End-to-end smoke test for Lapslie lead funnel API.

Checks:
1) POST /api/project-brief creates a brief.
2) GET /api/project-briefs can read the created brief (auth required).
3) GET /api/project-briefs/<briefId>/first-response-draft returns a draft.
4) GET /api/project-briefs/summary returns source counts including test source.

Designed for post-deploy validation before outbound traffic is scaled.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


DEFAULT_BASE_URL = "https://lapsliemail-api.onrender.com"


def request_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 15) -> dict:
    data = None
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method.upper(), headers=merged_headers)

    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {method} {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {method} {url}: {exc}") from exc


def find_brief(briefs: list[dict], brief_id: str) -> dict | None:
    for brief in briefs:
        if brief.get("briefId") == brief_id:
            return brief
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end smoke tests against the lead funnel API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Lead API base URL")
    parser.add_argument("--dashboard-token", required=True, help="LEAD_DASHBOARD_TOKEN for authenticated endpoints")
    parser.add_argument("--timeout-seconds", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--summary-limit", type=int, default=200, help="Limit used for summary read")
    parser.add_argument("--source", default="smoke_test", help="utm_source value for test brief")
    parser.add_argument("--medium", default="qa", help="utm_medium value for test brief")
    parser.add_argument("--campaign", default="lead_funnel_smoke", help="utm_campaign value for test brief")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    marker = f"SMOKE-{int(time.time())}"

    base_url = args.base_url.rstrip("/")
    auth_headers = {"Authorization": f"Bearer {args.dashboard_token}"}

    print(f"[1/4] POST project brief @ {base_url}")
    payload = {
        "name": "Smoke Test",
        "email": "smoke-test@lapslie.com",
        "budget": "£1,200-£2,500",
        "timeline": "ASAP",
        "summary": f"{marker} submitted at {now}",
        "briefIntent": "conversion",
        "utm_source": args.source,
        "utm_medium": args.medium,
        "utm_campaign": args.campaign,
        "utm_content": marker.lower(),
        "referrer": "https://lapslie.com/",
        "landingPath": "/#projectBriefForm",
    }
    created = request_json("POST", f"{base_url}/api/project-brief", payload=payload, timeout=args.timeout_seconds)

    brief_id = created.get("briefId")
    if not created.get("success") or not brief_id:
        raise RuntimeError(f"Create brief failed: {created}")
    print(f"  ✓ created briefId={brief_id}")

    print("[2/4] GET lead inbox and verify created brief appears")
    inbox = request_json(
        "GET",
        f"{base_url}/api/project-briefs?limit=50",
        headers=auth_headers,
        timeout=args.timeout_seconds,
    )
    briefs = inbox.get("briefs", [])
    if not isinstance(briefs, list):
        raise RuntimeError(f"Unexpected inbox schema: {inbox}")

    matched = find_brief(briefs, brief_id)
    if not matched:
        raise RuntimeError(f"Created brief {brief_id} not found in inbox")
    print(f"  ✓ inbox contains briefId={brief_id} (priority={matched.get('priority')})")

    print("[3/4] GET first-response draft")
    draft = request_json(
        "GET",
        f"{base_url}/api/project-briefs/{urllib.parse.quote(brief_id)}/first-response-draft",
        headers=auth_headers,
        timeout=args.timeout_seconds,
    )
    draft_subject = ((draft.get("draft") or {}).get("subject"))
    if not draft_subject:
        raise RuntimeError(f"Draft endpoint returned no subject: {draft}")
    print(f"  ✓ draft generated: {draft_subject}")

    print("[4/4] GET summary and verify test source captured")
    summary = request_json(
        "GET",
        f"{base_url}/api/project-briefs/summary?limit={args.summary_limit}",
        headers=auth_headers,
        timeout=args.timeout_seconds,
    )

    by_source = summary.get("bySource", {}) if isinstance(summary, dict) else {}
    source_value = by_source.get(args.source, 0)
    if not source_value:
        raise RuntimeError(f"Summary missing source '{args.source}': {summary}")
    print(f"  ✓ summary bySource['{args.source}']={source_value}")

    print("\nPASS: Lead funnel smoke test completed successfully.")
    print(f"Marker: {marker}")
    print("Note: if this was run against production, mark this test lead as lost/no-op in lead ops.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - cli guard
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
