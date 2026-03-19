#!/usr/bin/env bash
set -euo pipefail

# Starter command script for non-technical operation.
# Default = DRY-RUN (safe). Add --send for live mode.

python3 workflows/bulk_email_sequence.py \
  --leads-csv workflows/examples/leads.sample.csv \
  --sequence-json workflows/examples/sequence.sample.json \
  --rate-per-minute 20 \
  --retries 3 \
  --backoff-seconds 2
