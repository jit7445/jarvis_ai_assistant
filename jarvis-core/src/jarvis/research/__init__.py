from datetime import date

from jarvis.core.result import Result
from jarvis.planner import PlannerBusy, PlannerError
from jarvis.research import note, summarise, wiki

MAX_TOPIC_CHARS = 120

# Replaced in tests.
find = wiki.search
summariser = summarise.from_environment
today = date.today


def run(topic: str) -> Result:
    topic = " ".join(topic.split())[:MAX_TOPIC_CHARS]
    writer = summariser()
    if writer is None:
        return Result(False, "Research needs the Gemini key, so I did nothing.")
    try:
        sources = find(topic)
    except wiki.SourceUnavailable:
        return Result(False, "I couldn't reach Wikipedia, so I did nothing.")
    if not sources:
        return Result(False, f"I couldn't find anything about {topic}.")
    try:
        summary = summarise.clean(writer.summarise(topic, sources))
    except PlannerBusy:
        return Result(False, "Gemini is busy right now, so I did nothing.")
    except PlannerError:
        return Result(False, "I couldn't reach Gemini, so I did nothing.")
    if not summary:
        return Result(False, "I couldn't summarise that, so I did nothing.")
    path = note.write(topic, summary, sources, today())
    return Result(True, f"Saved a research note on {topic} in your research folder.")
