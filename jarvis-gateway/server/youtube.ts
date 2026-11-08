import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdir, readdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { config } from "./config.ts";

export class YoutubeError extends Error {
  constructor(public kind: "toolong" | "unavailable") { super(kind); }
}

const HOSTS = new Set(["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"]);
const ID = /^[A-Za-z0-9_-]{11}$/;

/** The canonical watch URL rebuilt from the video ID alone, or null. */
export function canonical(url: unknown): string | null {
  if (typeof url !== "string") return null;
  let parts: URL;
  try { parts = new URL(url.trim()); } catch { return null; }
  if (parts.protocol !== "https:" && parts.protocol !== "http:") return null;
  const host = parts.hostname.toLowerCase();
  let id: string | null = null;
  if (host === "youtu.be") id = parts.pathname.replace(/^\//, "").split("/")[0];
  else if (HOSTS.has(host)) {
    if (parts.pathname === "/watch") id = parts.searchParams.get("v");
    else if (/^\/(shorts|live|embed)\//.test(parts.pathname)) id = parts.pathname.split("/")[2];
  }
  return id && ID.test(id) ? `https://www.youtube.com/watch?v=${id}` : null;
}

function run(args: string[], timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    // --ignore-config: a yt-dlp config file could otherwise add --exec. "--" ends the options.
    const child = spawn(config.ytDlp, ["--ignore-config", "--no-warnings", ...args],
                        { stdio: ["ignore", "pipe", "ignore"] });
    let out = "";
    child.stdout.on("data", (chunk) => { out += chunk; });
    const timer = setTimeout(() => child.kill("SIGKILL"), timeoutMs);
    child.on("error", () => { clearTimeout(timer); reject(new YoutubeError("unavailable")); });
    child.on("close", (code) => {
      clearTimeout(timer);
      code === 0 ? resolve(out) : reject(new YoutubeError("unavailable"));
    });
  });
}

const TYPES: Record<string, string> = { ".m4a": "audio/mp4", ".webm": "audio/webm",
                                        ".mp3": "audio/mpeg", ".opus": "audio/ogg", ".ogg": "audio/ogg" };

export interface Audio { bytes: Buffer; type: string; title: string }

export async function download(url: string): Promise<Audio> {
  const clean = canonical(url);
  if (!clean) throw new YoutubeError("unavailable");
  const probe = (await run(["--skip-download", "--no-playlist", "--print",
                            "%(duration)s\t%(is_live)s\t%(title)s", "--", clean], 60_000)).trim();
  const [duration, live, ...title] = probe.split("\t");
  if (live === "True") throw new YoutubeError("unavailable");
  if (Number(duration) > config.maxVideoSeconds) throw new YoutubeError("toolong");
  const dir = path.join(config.tmpDir, randomUUID());
  await mkdir(dir, { recursive: true });
  try {
    await run(["--no-playlist", "--quiet", "--no-progress", "-f", "bestaudio[ext=m4a]/bestaudio",
               "--max-filesize", String(config.maxDownloadBytes), "-o", path.join(dir, "audio.%(ext)s"),
               "--", clean], config.downloadTimeoutMs);
    const file = (await readdir(dir)).find((f) => f.startsWith("audio."));
    const type = file && TYPES[path.extname(file)];
    if (!file || !type) throw new YoutubeError("unavailable");
    return { bytes: await readFile(path.join(dir, file)), type, title: title.join("\t") || "YouTube video" };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}
