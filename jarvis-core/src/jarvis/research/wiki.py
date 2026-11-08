from dataclasses import dataclass

import httpx

from jarvis import config


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    text: str


class SourceUnavailable(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(timeout=config.RESEARCH_TIMEOUT_SECONDS, follow_redirects=False,
                        headers={"User-Agent": config.USER_AGENT})


def _get(client: httpx.Client, params: dict) -> dict:
    try:
        response = client.get(config.WIKI_API, params={**params, "format": "json",
                                                       "formatversion": "2"})
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise SourceUnavailable() from None


def search(topic: str, client: httpx.Client | None = None) -> list[Source]:
    """Up to RESEARCH_SOURCES Wikipedia articles about the topic, as plain text."""
    with client or _client() as http:
        hits = _get(http, {"action": "query", "list": "search", "srsearch": topic,
                           "srlimit": config.RESEARCH_SOURCES})
        sources = []
        for hit in hits.get("query", {}).get("search", [])[:config.RESEARCH_SOURCES]:
            page_id = hit.get("pageid")
            if not isinstance(page_id, int):
                continue
            pages = _get(http, {"action": "query", "prop": "extracts|info", "inprop": "url",
                                "explaintext": 1, "pageids": page_id})
            for page in pages.get("query", {}).get("pages", []):
                url, text, title = page.get("fullurl"), page.get("extract"), page.get("title")
                if not (isinstance(url, str) and url.startswith(config.WIKI_PAGE_PREFIX)
                        and isinstance(text, str) and text.strip() and isinstance(title, str)):
                    continue
                sources.append(Source(title, url, text.strip()[:config.RESEARCH_PAGE_CHARS]))
        return sources
