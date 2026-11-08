#!/usr/bin/env bash
# Start jarvis-gateway and jarvis-core together with a fresh shared secret.
#   scripts/dev.sh            any jarvis options pass through, e.g. scripts/dev.sh --verbose
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# New every run, never written to disk; both services read it from the environment.
JARVIS_CORE_TOKEN="$(openssl rand -hex 32)"
export JARVIS_CORE_TOKEN
export JARVIS_CORE_PORT="${JARVIS_CORE_PORT:-8765}"
export JARVIS_GATEWAY_PORT="${JARVIS_GATEWAY_PORT:-4300}"

# The gateway downloads YouTube audio with yt-dlp.
if [ -z "${YT_DLP:-}" ]; then
  if command -v yt-dlp >/dev/null 2>&1; then YT_DLP="$(command -v yt-dlp)"
  elif [ -x "$ROOT/jarvis-core/.venv/bin/yt-dlp" ]; then YT_DLP="$ROOT/jarvis-core/.venv/bin/yt-dlp"
  else echo "yt-dlp not found: YouTube notes will fail (brew install yt-dlp)." >&2; YT_DLP=yt-dlp; fi
fi
export YT_DLP

(cd "$ROOT/jarvis-gateway" && exec npm run --silent dev) &
GATEWAY=$!
trap 'kill "$GATEWAY" 2>/dev/null || true' EXIT INT TERM

# Core never sees the Gemini key: only the gateway talks to the internet.
cd "$ROOT/jarvis-core"
# shellcheck disable=SC1091
source .venv/bin/activate
env -u GEMINI_API_KEY jarvis "$@"
