import http from "node:http";
import path from "node:path";
import express from "express";
import { WebSocketServer } from "ws";
import { createApp } from "./server/app.ts";
import { config, ROOT } from "./server/config.ts";
import { core } from "./server/core.ts";
import { GeminiLLM, Planner } from "./server/gemini.ts";
import { History } from "./server/history.ts";
import { allowedHosts, sameOrigin } from "./server/security.ts";
import { search } from "./server/wiki.ts";
import { download } from "./server/youtube.ts";

if (!config.token) {
  console.error("JARVIS_CORE_TOKEN is not set. Start both services with scripts/dev.sh.");
  process.exit(1);
}

const llm = config.geminiKey ? new GeminiLLM(config.geminiKey) : null;
let prompt: string | null = null;
// The tool list and its prompt come from core, the single source of truth for what exists.
const systemPrompt = async () => (prompt ??= (await core("/tools")).prompt as string);
const sockets = new Set<import("ws").WebSocket>();
const history = new History();

const app = createApp({
  core, history, search, download, llm,
  planner: llm ? new Planner(llm, systemPrompt) : null,
  broadcast: (message) => {
    const data = JSON.stringify(message);
    for (const socket of sockets) socket.send(data);
  },
});

const server = http.createServer(app);
const live = new WebSocketServer({ noServer: true });
server.on("upgrade", (req, socket, head) => {
  if (req.url !== "/live") return;  // Vite's own reload channel handles its path
  if (!allowedHosts().has(req.headers.host ?? "") || !sameOrigin(req.headers.origin)) {
    socket.destroy();
    return;
  }
  live.handleUpgrade(req, socket, head, (ws) => {
    sockets.add(ws);
    ws.on("close", () => sockets.delete(ws));
  });
});

if (process.env.NODE_ENV === "production") {
  const dist = path.join(ROOT, "dist");
  app.use(express.static(dist));
  app.get("*", (_req, res) => res.sendFile(path.join(dist, "index.html")));
} else {
  const { createServer } = await import("vite");
  const vite = await createServer({ server: { middlewareMode: true, ws: { server } }, appType: "spa" });
  app.use(vite.middlewares);
}

server.listen(config.port, config.host, () => {
  console.log(`Gateway on http://${config.host}:${config.port} (Gemini ${llm ? "on" : "off: GEMINI_API_KEY not set"})`);
});
