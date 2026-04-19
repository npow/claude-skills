#!/usr/bin/env bash
#
# Subagent staleness watchdog — Flavor A (push events via Monitor tail)
#
# See _shared/subagent-watchdog.md for the contract. This script is intended
# to be the `command` body of a Monitor tool invocation. Every line on stdout
# becomes one notification to the coordinator; the coordinator parses the
# line prefix (STALE / HUNG / ERROR) and reacts.
#
# Usage (from a coordination skill, after Agent(run_in_background=true)):
#
#   Monitor(
#     description="watchdog {skill}-{run_id}/{lane}",
#     timeout_ms=$((HUNG_SECONDS + 60)) * 1000,
#     persistent=false,
#     command="bash ~/.claude/skills/_shared/watchdog-monitor.sh \
#              {output_path} {stale_seconds} {hung_seconds} {lane_label}"
#   )
#
# Arguments:
#   $1  output_path     Path to the subagent's output file (mtime is tracked).
#   $2  stale_seconds   First-whisper threshold (e.g. 300 for 5 min).
#   $3  hung_seconds    Hard-kill threshold (e.g. 1200 for 20 min).
#   $4  lane_label      Short label identifying the lane (for parsable events).
#
# Emitted events (stdout, one per line, tight filter — see shared doc):
#   STALE <lane> age=<s>s file=<path>   — first time age crosses stale_seconds
#   HUNG  <lane> age=<s>s file=<path>   — first time age crosses hung_seconds;
#                                          script exits after emitting
#   ERROR <lane> <reason>                — stat failure, missing args, etc.
#
# Exit status:
#   0  — HUNG fired and was reported (caller should TaskStop the lane)
#   2  — missing / bad arguments
#   3  — hard timeout reached without HUNG (only possible if Monitor's
#         outer timeout_ms fires first; normally unreachable)
#
# Fail-safe: if the output file never appears, age is computed from Monitor
# start time (epoch at script entry) so STALE/HUNG still fire.

set -u

if [ "$#" -lt 4 ]; then
  echo "ERROR args missing: want <output_path> <stale_s> <hung_s> <lane_label>"
  exit 2
fi

OUTPUT_FILE="$1"
STALE_SECONDS="$2"
HUNG_SECONDS="$3"
LANE_LABEL="$4"
POLL_SECONDS="${POLL_SECONDS:-60}"

# Validate numeric thresholds — fail loudly rather than silently treat as 0.
case "$STALE_SECONDS" in ''|*[!0-9]*)
  echo "ERROR $LANE_LABEL stale_seconds not a positive integer: $STALE_SECONDS"
  exit 2
;; esac
case "$HUNG_SECONDS" in ''|*[!0-9]*)
  echo "ERROR $LANE_LABEL hung_seconds not a positive integer: $HUNG_SECONDS"
  exit 2
;; esac

if [ "$STALE_SECONDS" -ge "$HUNG_SECONDS" ]; then
  echo "ERROR $LANE_LABEL stale_seconds ($STALE_SECONDS) must be < hung_seconds ($HUNG_SECONDS)"
  exit 2
fi

# Portable mtime: stat -f %m on macOS, stat -c %Y on Linux.
mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null
}

SPAWN_EPOCH=$(date +%s)
last_alert=none

while true; do
  now=$(date +%s)

  if [ -f "$OUTPUT_FILE" ]; then
    file_mtime=$(mtime "$OUTPUT_FILE")
    if [ -z "$file_mtime" ]; then
      # File existed but stat failed — transient, fall back to spawn epoch.
      age=$(( now - SPAWN_EPOCH ))
    else
      age=$(( now - file_mtime ))
    fi
  else
    # File not yet created. Age is time since we started watching — don't
    # let a subagent that never writes anything look healthy.
    age=$(( now - SPAWN_EPOCH ))
  fi

  if [ "$age" -ge "$HUNG_SECONDS" ]; then
    echo "HUNG $LANE_LABEL age=${age}s file=$OUTPUT_FILE"
    exit 0
  fi

  if [ "$age" -ge "$STALE_SECONDS" ] && [ "$last_alert" = "none" ]; then
    echo "STALE $LANE_LABEL age=${age}s file=$OUTPUT_FILE"
    last_alert=stale
  fi

  sleep "$POLL_SECONDS"
done
