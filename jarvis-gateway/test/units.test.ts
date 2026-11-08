import "./helpers.ts";
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { type LLM, Planner } from "../server/gemini.ts";
import { sameOrigin, sameToken } from "../server/security.ts";
import { search } from "../server/wiki.ts";
import { canonical } from "../server/youtube.ts";

describe("youtube links", () => {
  for (const [url, out] of [
    ["https://www.youtube.com/watch?v=jNQXAC9IVRw&list=PL1&t=5s", "https://www.youtube.com/watch?v=jNQXAC9IVRw"],
    ["https://youtu.be/jNQXAC9IVRw?si=x", "https://www.youtube.com/watch?v=jNQXAC9IVRw"],
    ["https://m.youtube.com/shorts/jNQXAC9IVRw", "https://www.youtube.com/watch?v=jNQXAC9IVRw"],
  ]) it(`rebuilds ${url}`, () => assert.equal(canonical(url), out));
  for (const url of ["https://evil.com/watch?v=jNQXAC9IVRw", "https://youtube.com.evil.com/watch?v=jNQXAC9IVRw",
                     "https://www.youtube.com/watch?v=--exec=ls", "file:///etc/passwd", "", null, 42]) {
    it(`refuses ${String(url)}`, () => assert.equal(canonical(url), null));
  }
});

describe("secrets and origins", () => {
  it("token compare", () => {
    assert.ok(sameToken("abc", "abc"));
    for (const given of ["abd", "ab", "", undefined, ["abc"]]) assert.ok(!sameToken(given, "abc"));
    assert.ok(!sameToken("", ""));
  });
  it("origin", () => {
    assert.ok(sameOrigin("http://127.0.0.1:4300", 4300) && sameOrigin("http://localhost:4300", 4300));
    for (const o of ["http://127.0.0.1:4301", "https://127.0.0.1:4300", "null", undefined, "http://evil.com"]) {
      assert.ok(!sameOrigin(o, 4300));
    }
  });
});

describe("planner memory", () => {
  it("sends recent turns and forgets after quiet", async () => {
    const seen: string[][] = [];
    const llm: LLM = { async generate(o) { seen.push(o.turns.map((t) => t.text)); return '{"tool": null, "reply": "ok"}'; } };
    let now = 0;
    const p = new Planner(llm, async () => "P", () => now);
    await p.propose("tell me a joke");
    now += 30_000;
    await p.propose("explain it");
    assert.deepEqual(seen[1], ["tell me a joke", '{"tool": null, "reply": "ok"}', "explain it"]);
    now += 6 * 60_000;
    await p.propose("hello");
    assert.deepEqual(seen[2], ["hello"]);
  });
  it("keeps only the last six exchanges", async () => {
    const seen: number[] = [];
    const llm: LLM = { async generate(o) { seen.push(o.turns.length); return "{}"; } };
    const p = new Planner(llm, async () => "P", () => 0);
    for (let i = 0; i < 20; i++) await p.propose(`m${i}`);
    assert.equal(seen.at(-1), 13);
  });
});

describe("wikipedia", () => {
  it("only talks to Wikipedia and drops foreign page URLs", async () => {
    const hosts: string[] = [];
    const original = globalThis.fetch;
    globalThis.fetch = (async (input: URL) => {
      hosts.push(input.host);
      const q = input.searchParams;
      if (q.get("list") === "search") return Response.json({ query: { search: [{ pageid: 1 }, { pageid: 2 }] } });
      const url = q.get("pageids") === "1" ? "https://en.wikipedia.org/wiki/Black_hole" : "https://evil.example/x";
      return Response.json({ query: { pages: [{ title: "T", fullurl: url, extract: "Text ".repeat(3000) }] } });
    }) as typeof fetch;
    try {
      const pages = await search("black holes");
      assert.deepEqual(pages.map((p) => p.url), ["https://en.wikipedia.org/wiki/Black_hole"]);
      assert.equal(pages[0].text.length, 6000);
      assert.deepEqual([...new Set(hosts)], ["en.wikipedia.org"]);
    } finally {
      globalThis.fetch = original;
    }
  });
});
