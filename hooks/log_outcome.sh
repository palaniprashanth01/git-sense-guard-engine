#!/usr/bin/env sh
# Capture the tool output JSON and persist outcome metrics.
LOG_DIR="$(dirname "$0")/../memory"
mkdir -p "$LOG_DIR"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
payload="$(cat -)"
outcome="$(printf '%s' "$payload" | grep -o '"outcome":[[:space:]]*"[^"]*"' | head -n1)"
printf '%s\t%s\n' "$ts" "$outcome" >> "$LOG_DIR/outcomes.log"
printf '%s' "$payload"
