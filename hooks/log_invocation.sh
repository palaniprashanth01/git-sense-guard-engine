#!/usr/bin/env sh
# Append a one-line audit invocation record to memory/invocations.log.
# Receives the tool input JSON on stdin.
LOG_DIR="$(dirname "$0")/../memory"
mkdir -p "$LOG_DIR"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
payload="$(cat -)"
printf '%s\trun-audit\t%s\n' "$ts" "$payload" >> "$LOG_DIR/invocations.log"
# Re-emit stdin so downstream hooks / tool still see it.
printf '%s' "$payload"
