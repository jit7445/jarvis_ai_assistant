import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

export const config = {
  host: "127.0.0.1",
  port: Number(process.env.JARVIS_GATEWAY_PORT ?? 4300),
  corePort: Number(process.env.JARVIS_CORE_PORT ?? 8765),
  token: (process.env.JARVIS_CORE_TOKEN ?? "").trim(),
  tokenHeader: "x-jarvis-token",
  geminiKey: (process.env.GEMINI_API_KEY ?? "").trim(),
  model: "gemini-3.5-flash-lite",
  // Gemini rejects deadlines under 10 s.
  planTimeoutMs: 15_000,
  summaryTimeoutMs: 90_000,
  chatTurns: 6,
  chatMemoryMs: 5 * 60_000,
  wikiApi: "https://en.wikipedia.org/w/api.php",
  wikiPagePrefix: "https://en.wikipedia.org/wiki/",
  // Wikimedia answers 403 unless the agent carries a contact URL in this form.
  userAgent: "jarvis-gateway/0.1 (https://github.com/jit7445/jarvis_ai_assistant)",
  wikiSources: 2,
  wikiPageChars: 6000,
  wikiTimeoutMs: 10_000,
  ytDlp: process.env.YT_DLP ?? "yt-dlp",
  maxVideoSeconds: 90 * 60,
  maxDownloadBytes: 300 * 1024 * 1024,
  downloadTimeoutMs: 10 * 60_000,
  // Downloads land here and nowhere else: the gateway's own folder.
  tmpDir: path.join(ROOT, "tmp"),
  historySize: 100,
};
