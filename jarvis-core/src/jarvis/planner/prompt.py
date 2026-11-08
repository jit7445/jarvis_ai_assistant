from jarvis import config
from jarvis.tools.registry import TOOLS

ABOUT = {
    "fs.make_dir": "Create a folder. name: the folder name.",
    "fs.write_file": "Create a note, or replace one. name: the note name. body: the note text, "
                     "or an empty string.",
    "fs.read_file": "Read a note aloud. name: the note name.",
    "fs.list_dir": "Say what folders and notes exist.",
    "app.open": "Open an app. app_name: one of {apps}.",
    "web.research": "Look a subject up on Wikipedia and save a research note with sources. "
                    "topic: the subject, in a few words.",
}


def system_prompt() -> str:
    lines = []
    for tool, schema in TOOLS.items():
        args = ", ".join(f'"{key}": string' for key in schema)
        about = ABOUT[tool].format(apps=", ".join(sorted(config.ALLOWED_APPS)))
        lines.append(f'- {tool} {{{args}}}: {about}')
    return (
        "You are Jarvis, a friendly voice assistant on the user's Mac. Every reply is one JSON "
        "object and nothing else.\n\n"
        "If the sentence asks for something one of these tools does, reply\n"
        '{"tool": "<tool name>", "args": {<arguments>}}.\n\n'
        "Tools:\n" + "\n".join(lines) + "\n\n"
        "Names are plain names such as Projects or groceries, never paths. "
        "Never invent tools or arguments.\n\n"
        "Otherwise, for questions, small talk or anything no tool covers, reply\n"
        '{"tool": null, "reply": "<what you say back>"}.\n'
        "The reply is spoken aloud: one to three short sentences, plain words, no markdown, lists, "
        "emoji or links. Be warm and natural. Never claim to have done something on the computer; "
        "if asked for an action no tool covers, say you can't do that yet. You cannot see live news, "
        "weather or the time, so say so if asked; for background on a subject, web.research can "
        "save a note."
    )
