import { config } from "./config.ts";
import type { Page } from "./gemini.ts";

export class WikiError extends Error {}

async function get(params: Record<string, string>): Promise<any> {
  const url = new URL(config.wikiApi);
  for (const [k, v] of Object.entries({ ...params, format: "json", formatversion: "2" })) {
    url.searchParams.set(k, v);
  }
  try {
    const response = await fetch(url, { headers: { "user-agent": config.userAgent },
                                         signal: AbortSignal.timeout(config.wikiTimeoutMs),
                                         redirect: "error" });
    if (!response.ok) throw new WikiError(String(response.status));
    return await response.json();
  } catch {
    throw new WikiError("unreachable");
  }
}

/** Up to two Wikipedia articles as plain text. The host is fixed; no URL from a page is followed,
 * and any page whose URL is not on Wikipedia is dropped. */
export async function search(topic: string): Promise<Page[]> {
  const hits = await get({ action: "query", list: "search", srsearch: topic,
                           srlimit: String(config.wikiSources) });
  const pages: Page[] = [];
  for (const hit of (hits?.query?.search ?? []).slice(0, config.wikiSources)) {
    if (!Number.isInteger(hit?.pageid)) continue;
    const data = await get({ action: "query", prop: "extracts|info", inprop: "url",
                             explaintext: "1", pageids: String(hit.pageid) });
    for (const page of data?.query?.pages ?? []) {
      const { fullurl: url, extract: text, title } = page ?? {};
      if (typeof url === "string" && url.startsWith(config.wikiPagePrefix) && typeof text === "string"
          && text.trim() && typeof title === "string") {
        pages.push({ title, url, text: text.trim().slice(0, config.wikiPageChars) });
      }
    }
  }
  return pages;
}
