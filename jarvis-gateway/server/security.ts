import { timingSafeEqual } from "node:crypto";
import type { NextFunction, Request, Response } from "express";
import { config } from "./config.ts";

export function allowedHosts(port = config.port): Set<string> {
  return new Set([`127.0.0.1:${port}`, `localhost:${port}`]);
}

/** A page that rebinds its own name to 127.0.0.1 still sends its own Host header. */
export function hostGuard(req: Request, res: Response, next: NextFunction) {
  if (!allowedHosts().has(req.headers.host ?? "")) return res.status(403).json({ error: "host" });
  next();
}

export function sameToken(given: unknown, expected = config.token): boolean {
  if (typeof given !== "string" || !expected) return false;
  const a = Buffer.from(given), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

/** Routes only core may call. */
export function requireToken(req: Request, res: Response, next: NextFunction) {
  if (!sameToken(req.headers[config.tokenHeader])) return res.status(401).json({ error: "token" });
  next();
}

export function sameOrigin(origin: string | undefined, port = config.port): boolean {
  return origin === `http://127.0.0.1:${port}` || origin === `http://localhost:${port}`;
}

/** Browser routes that change something: another website's page must not be able to send them. */
export function requireOrigin(req: Request, res: Response, next: NextFunction) {
  if (!sameOrigin(req.headers.origin)) return res.status(403).json({ error: "origin" });
  next();
}
