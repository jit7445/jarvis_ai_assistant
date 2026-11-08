from jarvis.core.intent import Intent

TOOLS: dict[str, dict[str, type]] = {
    "fs.make_dir": {"name": str},
    "fs.write_file": {"name": str, "body": str},
    "fs.read_file": {"name": str},
    "fs.list_dir": {},
    "app.open": {"app_name": str},
    "web.research": {"topic": str},
}


class InvalidIntent(ValueError):
    pass


def check(intent: Intent) -> Intent:
    schema = TOOLS.get(intent.tool)
    if schema is None:
        raise InvalidIntent(f"unknown tool: {intent.tool!r}")
    if not isinstance(intent.args, dict) or set(intent.args) != set(schema):
        raise InvalidIntent(f"{intent.tool} takes exactly {sorted(schema)}")
    for key, kind in schema.items():
        value = intent.args[key]
        if not isinstance(value, kind):
            raise InvalidIntent(f"{intent.tool}.{key} must be {kind.__name__}")
        if kind is str and key != "body" and not value.strip():
            raise InvalidIntent(f"{intent.tool}.{key} is empty")
    if not isinstance(intent.confirm, bool):
        raise InvalidIntent("confirm must be a bool")
    return intent
