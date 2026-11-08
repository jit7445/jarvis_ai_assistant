# jarvis-gateway

The network side of Jarvis: Gemini, Wikipedia, YouTube downloads and the browser dashboard. It binds to `127.0.0.1:4300` and is the only process allowed to use the internet. Everything that touches the Mac (and the policy gate) lives in `jarvis-core`.

## Setup

```bash
cd jarvis-gateway
npm ci --ignore-scripts      # exact versions from package-lock.json, no install scripts
npm test                     # 42 tests
npm run lint                 # TypeScript check
```

`GEMINI_API_KEY` comes from your shell (for example `~/.zshrc`). YouTube notes need `yt-dlp` on the PATH (`brew install yt-dlp`) or `YT_DLP` pointing at it.

Run it together with core from the repository root with `scripts/dev.sh`, which also creates the shared secret. Alone it refuses to start without `JARVIS_CORE_TOKEN`.

## Layout

| Path | Contents |
| --- | --- |
| `server.ts` | Entry: HTTP server on 127.0.0.1, `WS /live`, Vite in development |
| `server/app.ts` | Routes: core-only (`/plan`, `/research`, `/summarise`, `/youtube-audio`, `/events`) and dashboard (`/status`, `/history`, `/command`) |
| `server/security.ts` | Token, Host and Origin checks |
| `server/gemini.ts` | Gemini client (one attempt, timeouts), planner memory, summary prompts with untrusted text fenced |
| `server/wiki.ts`, `server/youtube.ts` | Wikipedia (fixed host) and yt-dlp (`--ignore-config`, canonical URLs only) |
| `src/` | The React dashboard: Arc Reactor HUD, live state, typed commands |
| `test/` | `node --test` suites |
