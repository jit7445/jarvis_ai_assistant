from jarvis import config, gateway_client
from jarvis.planner import PlannerBadReply, PlannerBusy, PlannerSetup, PlannerUnavailable


class GatewayPlanner:
    """Gemini, reached through the gateway. The reply comes back raw and is checked here, in
    core, exactly as before: the gate never moves."""

    model = "Gemini via the gateway"

    def propose(self, transcript: str):
        try:
            response = gateway_client.post("/plan", config.PLANNER_TIMEOUT_SECONDS,
                                           json={"text": transcript})
        except gateway_client.GatewayError as error:
            if error.kind == "busy":
                raise PlannerBusy() from None
            if error.kind == "setup":
                raise PlannerSetup() from None
            raise PlannerUnavailable() from None
        try:
            return response.json()["proposal"]
        except (ValueError, KeyError, TypeError):
            raise PlannerBadReply() from None


def from_environment() -> GatewayPlanner | None:
    return GatewayPlanner() if gateway_client.token() else None
