from jarvis.core.router import normalise

_YES = {"yes", "yeah", "yep", "yes please", "sure", "go ahead", "do it", "overwrite it", "confirm",
        "yes overwrite it", "yes do it", "yes go ahead"}
_NO = {"no", "nope", "no thanks", "no thank you", "don't", "do not", "cancel", "stop",
       "leave it", "don't overwrite it", "never mind", "nevermind"}


def parse_answer(transcript: str) -> bool | None:
    if not isinstance(transcript, str):
        return None
    text = normalise(transcript).lower().replace(",", "")
    if text in _YES:
        return True
    if text in _NO:
        return False
    return None
