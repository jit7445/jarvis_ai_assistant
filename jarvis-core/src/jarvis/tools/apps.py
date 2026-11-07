import subprocess

from jarvis import config
from jarvis.core.result import Result


def resolve(spoken_name: str) -> str:
    """The allowlisted app for a spoken name, or PermissionError."""
    if not isinstance(spoken_name, str):
        raise PermissionError("not allowed")
    key = " ".join(spoken_name.split()).lower()
    if key.endswith(" browser"):
        key = key.removesuffix(" browser")
    app = config.ALLOWED_APPS.get(key)
    if app is None or key in config.BANNED_APPS or app.lower() in config.BANNED_APPS:
        raise PermissionError("not allowed")
    return app


def open_app(spoken_name: str) -> Result:
    app = resolve(spoken_name)
    subprocess.run(["open", "-a", app], check=True, timeout=10, capture_output=True)
    return Result(True, f"Opening {app}.")
