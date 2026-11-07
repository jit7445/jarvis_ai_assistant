from pathlib import Path, PurePosixPath

from jarvis import config


def safe_path(name: str) -> Path:
    if not isinstance(name, str):
        raise PermissionError("name must be text")
    name = name.strip()
    if not name or any(ord(c) < 32 for c in name):
        raise PermissionError(f"invalid name: {name!r}")
    # pathlib does not expand "~", so "~/x" would otherwise land harmlessly inside the workspace
    # and hide the intent; refuse it outright.
    if name.startswith("~"):
        raise PermissionError(f"outside workspace: {name}")
    if any(part.startswith(".") and part != "." for part in PurePosixPath(name).parts):
        raise PermissionError(f"hidden or parent path: {name}")

    root = config.WORKSPACE.resolve(strict=True)
    target = (root / name).resolve()
    if root not in target.parents:
        raise PermissionError(f"outside workspace: {name}")
    return target
