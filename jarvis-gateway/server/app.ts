import express, { type Response } from "express";
import { config } from "./config.ts";
import { CoreError } from "./core.ts";
import { GeminiError, type LLM, type Page, type Planner, RESEARCH_PROMPT, VIDEO_PROMPT,
         researchRequest, summarise, videoRequest } from "./gemini.ts";
import type { History } from "./history.ts";
import { hostGuard, requireOrigin, requireToken } from "./security.ts";
import { WikiError } from "./wiki.ts";
import { YoutubeError, type Audio } from "./youtube.ts";

export interface Deps {
  core: (path: string, init?: { body?: unknown; timeoutMs?: number }) => Promise<any>;
  planner: Planner | null;
  llm: LLM | null;
  search: (topic: string) => Promise<Page[]>;
  download: (url: string) => Promise<Audio>;
  history: History;
  broadcast: (message: object) => void;
}

const MAX_TEXT = 2000;
const MAX_TRANSCRIPT = 200_000;

function geminiFailed(res: Response, error: unknown) {
  const kind = error instanceof GeminiError ? error.kind : "upstream";
  const status = { busy: 429, setup: 503, upstream: 502, bad: 502 }[kind];
  return res.status(status).json({ error: kind });
}

function text(value: unknown, max: number): string | null {
  return typeof value === "string" && value.trim() && value.length <= max ? value.trim() : null;
}

export function createApp(deps: Deps) {
  const app = express();
  app.disable("x-powered-by");
  app.use(hostGuard);
  app.use(express.json({ limit: "2mb" }));

  // Called by jarvis-core only: everything that needs the internet.
  app.post("/plan", requireToken, async (req, res) => {
    const sentence = text(req.body?.text, MAX_TEXT);
    if (!sentence) return res.status(422).json({ error: "text" });
    if (!deps.planner) return res.status(503).json({ error: "no gemini key" });
    try {
      res.json({ proposal: await deps.planner.propose(sentence) });
    } catch (error) {
      geminiFailed(res, error);
    }
  });

  app.post("/research", requireToken, async (req, res) => {
    const topic = text(req.body?.topic, 200);
    if (!topic) return res.status(422).json({ error: "topic" });
    if (!deps.llm) return res.status(503).json({ error: "no gemini key" });
    let pages: Page[];
    try {
      pages = await deps.search(topic);
    } catch (error) {
      return res.status(error instanceof WikiError ? 502 : 500).json({ error: "wikipedia" });
    }
    if (!pages.length) return res.status(404).json({ error: "nothing found" });
    try {
      const summary = await summarise(deps.llm, RESEARCH_PROMPT, researchRequest(topic, pages), 800);
      res.json({ summary, sources: pages.map(({ title, url }) => ({ title, url })) });
    } catch (error) {
      geminiFailed(res, error);
    }
  });

  app.post("/summarise", requireToken, async (req, res) => {
    const title = text(req.body?.title, 300), transcript = text(req.body?.transcript, MAX_TRANSCRIPT);
    if (req.body?.kind !== "video" || !title || !transcript) return res.status(422).json({ error: "input" });
    if (!deps.llm) return res.status(503).json({ error: "no gemini key" });
    try {
      res.json({ summary: await summarise(deps.llm, VIDEO_PROMPT, videoRequest(title, transcript), 1500) });
    } catch (error) {
      geminiFailed(res, error);
    }
  });

  app.post("/youtube-audio", requireToken, async (req, res) => {
    try {
      const audio = await deps.download(req.body?.url);
      res.set("x-title", encodeURIComponent(audio.title.slice(0, 200))).type(audio.type).send(audio.bytes);
    } catch (error) {
      res.status(error instanceof YoutubeError && error.kind === "toolong" ? 413 : 502).json({ error: "youtube" });
    }
  });

  app.post("/events", requireToken, (req, res) => {
    const { state, text: said } = req.body ?? {};
    if (typeof state !== "string" || typeof said !== "string") return res.status(422).end();
    deps.broadcast({ type: "state", ...deps.history.add(state, said) });
    res.status(204).end();
  });

  // The browser UI, served from this same origin.
  app.get("/status", async (_req, res) => {
    let core: unknown = null;
    try { core = await deps.core("/health", { timeoutMs: 2000 }); } catch { core = null; }
    res.json({ core, gemini: Boolean(deps.llm) });
  });

  app.get("/history", (_req, res) => res.json(deps.history.list()));

  app.post("/command", requireOrigin, async (req, res) => {
    const sentence = text(req.body?.text, MAX_TEXT);
    if (!sentence) return res.status(422).json({ error: "text" });
    deps.history.add("typed", sentence);
    try {
      const { reply } = await deps.core("/command", { body: { text: sentence }, timeoutMs: 600_000 });
      res.json({ reply });
    } catch (error) {
      const down = error instanceof CoreError && error.status === 503;
      res.status(502).json({ reply: down ? "Jarvis core isn't running." : "Jarvis core refused that." });
    }
  });

  return app;
}

export { config };
