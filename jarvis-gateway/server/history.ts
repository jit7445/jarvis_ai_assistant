import { config } from "./config.ts";

export interface Entry { at: number; state: string; text: string }

/** Recent states, in memory only: the plan's rule is to log what happened, not keep what was said. */
export class History {
  private entries: Entry[] = [];
  constructor(private size = config.historySize) {}

  add(state: string, text: string, at = Date.now()): Entry {
    const entry = { at, state: String(state).slice(0, 32), text: String(text).slice(0, 2000) };
    this.entries.push(entry);
    if (this.entries.length > this.size) this.entries.splice(0, this.entries.length - this.size);
    return entry;
  }

  list(): Entry[] { return [...this.entries]; }
}
