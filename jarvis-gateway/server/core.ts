import { config } from "./config.ts";

export class CoreError extends Error {
  constructor(public status: number, message = "core") { super(message); }
}

/** Requests to jarvis-core on 127.0.0.1, always with the shared secret. */
export async function core(path: string, init: { method?: string; body?: unknown; timeoutMs?: number } = {}) {
  let response: Response;
  try {
    response = await fetch(`http://127.0.0.1:${config.corePort}${path}`, {
      method: init.method ?? (init.body === undefined ? "GET" : "POST"),
      headers: { [config.tokenHeader]: config.token, "content-type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: AbortSignal.timeout(init.timeoutMs ?? 10_000),
      redirect: "error",
    });
  } catch {
    throw new CoreError(503, "core unreachable");
  }
  if (!response.ok) throw new CoreError(response.status);
  return response.json();
}
