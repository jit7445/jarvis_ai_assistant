from datetime import date

from jarvis import config, gateway_client
from jarvis.core.result import Result
from jarvis.research import note, summarise
from jarvis.research.note import Source

MAX_TOPIC_CHARS = 120
MAX_SOURCES = 5


class BadReply(Exception):
    pass


def _ask_gateway(topic: str) -> tuple[str, list[Source]]:
    """The gateway fetches Wikipedia and summarises; core only accepts the shape it expects."""
    data = gateway_client.post("/research", config.SUMMARY_TIMEOUT_SECONDS,
                               json={"topic": topic}).json()
    if not isinstance(data, dict):
        raise BadReply()
    summary, raw = data.get("summary"), data.get("sources")
    if not isinstance(summary, str) or not isinstance(raw, list):
        raise BadReply()
    sources = [Source(" ".join(s["title"].split())[:150], s["url"]) for s in raw[:MAX_SOURCES]
               if isinstance(s, dict) and isinstance(s.get("title"), str)
               and isinstance(s.get("url"), str) and s["url"].startswith(config.WIKI_PAGE_PREFIX)
               and not any(c in s["url"] for c in " \n\r()")]
    return summary, sources


# Replaced in tests.
fetch = _ask_gateway
today = date.today

_FAILED = {
    "setup": "Research needs the gateway with a Gemini key, so I did nothing.",
    "offline": "I couldn't reach the gateway, so I did nothing.",
    "busy": "Gemini is busy right now, so I did nothing.",
    "upstream": "I couldn't reach Wikipedia or Gemini, so I did nothing.",
}


def run(topic: str) -> Result:
    topic = " ".join(topic.split())[:MAX_TOPIC_CHARS]
    try:
        summary, sources = fetch(topic)
    except gateway_client.GatewayError as error:
        if error.kind == "notfound":
            return Result(False, f"I couldn't find anything about {topic}.")
        return Result(False, _FAILED.get(error.kind, "That didn't work, so I did nothing."))
    except (BadReply, ValueError):
        return Result(False, "The research came back garbled, so I did nothing.")
    summary = summarise.clean(summary)
    if not summary or not sources:
        return Result(False, f"I couldn't find anything about {topic}.")
    note.write(topic, summary, sources, today())
    return Result(True, f"Saved a research note on {topic} in your research folder.")
