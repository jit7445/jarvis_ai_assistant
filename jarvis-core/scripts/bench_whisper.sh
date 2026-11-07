#!/bin/sh
# Phase 2 offline benchmark. Run with Wi-Fi off; results go to docs/phase2_offline.log.
set -u
CORE="$(cd "$(dirname "$0")/.." && pwd)"
WHISPER="$CORE/whisper.cpp"
LOG="$CORE/docs/phase2_offline.log"
WAV="${1:-$CORE/workspace/mic_test.wav}"

if curl -s -m 3 -o /dev/null https://github.com; then
  echo "Network is reachable. Turn Wi-Fi off and run again."
  exit 1
fi

{
  echo "date: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "network: unreachable"
  echo "pressure before: $(memory_pressure | grep 'free percentage')"
  for i in 1 2 3 4 5; do
    out=$(/usr/bin/time -l "$WHISPER/build/bin/whisper-cli" -m "$WHISPER/models/ggml-base.en.bin" \
          -f "$WAV" -t 4 -nt 2>&1)
    text=$(printf '%s\n' "$out" | grep -E '^ [A-Za-z]' | head -1)
    real=$(printf '%s\n' "$out" | awk '/ real /{print $1}')
    rss=$(printf '%s\n' "$out" | awk '/maximum resident/{printf "%.0f", $1/1048576}')
    echo "run $i: ${real}s ${rss}MB |${text}"
  done
  echo "pressure after: $(memory_pressure | grep 'free percentage')"
} | tee "$LOG"
