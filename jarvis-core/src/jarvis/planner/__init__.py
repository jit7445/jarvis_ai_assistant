from typing import Any, Protocol


class Planner(Protocol):
    def propose(self, transcript: str) -> Any:
        """The model's parsed JSON reply. Untrusted: validate before use."""


class PlannerError(Exception):
    pass


class PlannerUnavailable(PlannerError):
    """No network, timeout, or a server error."""


class PlannerBusy(PlannerError):
    """Rate limited (HTTP 429)."""


class PlannerSetup(PlannerError):
    """The service refused the key or the request (HTTP 400, 401, 403)."""


class PlannerBadReply(PlannerError):
    """The reply was not JSON."""
