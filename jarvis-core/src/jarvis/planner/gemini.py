import json
import os
import time

from google import genai
from google.genai import errors, types

from jarvis import config
from jarvis.planner import (PlannerBadReply, PlannerBusy, PlannerSetup, PlannerUnavailable)
from jarvis.planner.prompt import system_prompt


class GeminiPlanner:
    """Sends the transcript and the tool list, nothing else. Free-tier requests may be used by
    Google to improve its products."""

    def __init__(self, api_key: str, model: str = config.GEMINI_MODEL,
                 timeout: float = config.PLANNER_TIMEOUT_SECONDS, client=None) -> None:
        self.model = model
        # One attempt: a voice reply that waits through retries is worse than a quick "no".
        self._client = client or genai.Client(api_key=api_key, http_options=types.HttpOptions(
            timeout=int(timeout * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
        self._config = types.GenerateContentConfig(
            system_instruction=system_prompt(), response_mime_type="application/json",
            temperature=0.2, max_output_tokens=300)
        self._history: list[types.Content] = []
        self._last_turn = 0.0

    def forget(self) -> None:
        self._history.clear()

    def propose(self, transcript: str):
        if time.monotonic() - self._last_turn > config.CHAT_MEMORY_SECONDS:
            self.forget()
        asked = types.Content(role="user", parts=[types.Part(text=transcript)])
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=[*self._history, asked], config=self._config)
        except errors.ClientError as error:
            if error.code == 429:
                raise PlannerBusy() from None
            if error.code in (400, 401, 403):
                raise PlannerSetup() from None
            raise PlannerUnavailable() from None
        except Exception:
            raise PlannerUnavailable() from None
        try:
            proposal = json.loads(response.text)
        except (TypeError, ValueError):
            raise PlannerBadReply() from None
        answered = types.Content(role="model", parts=[types.Part(text=response.text)])
        self._history = [*self._history, asked, answered][-2 * config.CHAT_MEMORY_TURNS:]
        self._last_turn = time.monotonic()
        return proposal


def from_environment() -> GeminiPlanner | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return GeminiPlanner(key) if key else None
