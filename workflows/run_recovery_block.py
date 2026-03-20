#!/usr/bin/env python3
"""Run a daily stalled-lead recovery block against the LapsliEmail API.

Default behavior is safe dry-run:
- reads follow-up queue
- filters stale leads (>=48h by default) in contacted/qualified/proposal_sent
- prints planned actions

Send mode (`--send`) executes:
- contacted/proposal_sent -> POST /follow-up-send
- qualified -> POST /proposal-send (can be changed via --qualified-action)
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

DEFAULT_BASE_URL = "https://lapsliemail-api.onrender.com"
DEFAULT_STAGES = ("contacted", "qualified", "proposal_sent")


def request_json(method: str, url: str, headers: dict, payload: dict | None = None, timeout: int = 20) -> dict:
    body = None
    req_headers = {"Accept": "application/json"}
    req_headers.update(headers or {})

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=body, method=method.upper(), headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error {method} {url}: {exc}") from exc


def action_for_stage(stage: str, qualified_action: str) -> tuple[str, str]:
    if stage == "qualified":
        return ("proposal-send", "Send scoped proposal to push decision") if qualified_action == "proposal" else ("follow-up-send", "Send qualification follow-up nudge")
    return "follow-up-send", "Send stage-aware follow-up nudge"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run stalled-lead recovery block")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--dashboard-token", required=True, help="LEAD_DASHBOARD_TOKEN")
    parser.add_argument("--limit", type=int, default=300, help="Queue read limit (1-500)")
    parser.add_argument("--sla-hours", type=int, default=24, help="SLA hours used by queue API")
    parser.add_argument("--stale-hours", type=float, default=48.0, help="Minimum stage age to recover")
    parser.add_argument("--stages", nargs="+", default=list(DEFAULT_STAGES), help="Stages to include")
    parser.add_argument("--qualified-action", choices=["proposal", "followup"], default="proposal", help="Action for qualified leads")
    parser.add_argument("--send", action="store_true", help="Execute actions (default is dry-run)")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="HTTP timeout")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {args.dashboard_token}"}

    limit = max(1, min(args.limit, 500))
    sla_hours = max(1, min(args.sla_hours, 168))

    queue_url = f"{base}/api/project-briefs/follow-up-queue?limit={limit}&slaHours={sla_hours}"
    queue_resp = request_json("GET", queue_url, headers=headers, timeout=args.timeout_seconds)
    queue = ((queue_resp.get("followUp") or {}).get("queue") or [])

    include_stages = {str(s).strip().lower() for s in args.stages if str(s).strip()}
    candidates = []
    for lead in queue:
        stage = str(lead.get("stage") or "").lower()
        if stage not in include_stages:
            continue
        age = float(lead.get("hoursSinceStageUpdate") or 0)
        if age < args.stale_hours:
            continue
        endpoint, rationale = action_for_stage(stage, args.qualified_action)
        candidates.append({
            "briefId": lead.get("briefId"),
            "name": lead.get("name") or "Unknown",
            "email": lead.get("email") or "",
            "source": lead.get("source") or "unknown",
            "stage": stage,
            "hoursSinceStageUpdate": round(age, 1),
            "recommendedAction": endpoint,
            "rationale": rationale,
        })

    print(f"Recovery block mode: {'SEND' if args.send else 'DRY-RUN'}")
    print(f"Queue items read: {len(queue)} | stale threshold: {args.stale_hours}h | candidates: {len(candidates)}")

    if not candidates:
        print("No stale leads matched filters. Nothing to do.")
        return 0

    by_stage = Counter(item["stage"] for item in candidates)
    by_source = Counter(item["source"] for item in candidates)
    print("Candidates by stage:", dict(by_stage))
    print("Candidates by source:", dict(by_source))

    for idx, item in enumerate(candidates, start=1):
        print(
            f"{idx}. {item['briefId']} | {item['stage']} | {item['hoursSinceStageUpdate']}h | "
            f"{item['source']} | {item['name']} <{item['email']}> -> {item['recommendedAction']}"
        )

    if not args.send:
        print("\nDry-run complete. Re-run with --send to execute.")
        return 0

    success = 0
    failed = 0
    for item in candidates:
        brief_id = urllib.parse.quote(str(item["briefId"]))
        endpoint = item["recommendedAction"]
        url = f"{base}/api/project-briefs/{brief_id}/{endpoint}"
        note = (
            f"Recovery block auto-action ({endpoint}) after {item['hoursSinceStageUpdate']}h in {item['stage']} stage"
        )
        payload = {"statusNotes": note}
        try:
            resp = request_json("POST", url, headers=headers, payload=payload, timeout=args.timeout_seconds)
            if resp.get("success"):
                success += 1
            else:
                failed += 1
                print(f"FAIL {item['briefId']}: {resp}")
        except Exception as exc:  # pragma: no cover - CLI guard
            failed += 1
            print(f"FAIL {item['briefId']}: {exc}")

    print(f"\nExecution complete. Success={success} Failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
