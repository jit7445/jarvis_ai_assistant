import json
import os

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
            temperature=0.0, max_output_tokens=256)

    def propose(self, transcript: str):
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=transcript, config=self._config)
        except errors.ClientError as error:
            if error.code == 429:
                raise PlannerBusy() from None
            if error.code in (400, 401, 403):
                raise PlannerSetup() from None
            raise PlannerUnavailable() from None
        except Exception:
            raise PlannerUnavailable() from None
        try:
            return json.loads(response.text)
        except (TypeError, ValueError):
            raise PlannerBadReply() from None


def from_environment() -> GeminiPlanner | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return GeminiPlanner(key) if key else None
