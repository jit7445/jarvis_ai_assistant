from jarvis import config
from jarvis.tools.registry import TOOLS

ABOUT = {
    "fs.make_dir": "Create a folder. name: the folder name.",
    "fs.write_file": "Create a note, or replace one. name: the note name. body: the note text, "
                     "or an empty string.",
    "fs.read_file": "Read a note aloud. name: the note name.",
    "fs.list_dir": "Say what folders and notes exist.",
    "app.open": "Open an app. app_name: one of {apps}.",
}


def system_prompt() -> str:
    lines = []
    for tool, schema in TOOLS.items():
        args = ", ".join(f'"{key}": string' for key in schema)
        about = ABOUT[tool].format(apps=", ".join(sorted(config.ALLOWED_APPS)))
        lines.append(f'- {tool} {{{args}}}: {about}')
    return (
        "You turn one spoken command for a voice assistant into a single tool call.\n"
        "Reply with one JSON object and nothing else, shaped exactly like\n"
        '{"tool": "<tool name>", "args": {<arguments>}}.\n\n'
        "Tools:\n" + "\n".join(lines) + "\n\n"
        "Names are plain names such as Projects or groceries, never paths.\n"
        'If no tool fits, or the sentence is a question, chat or unclear, reply {"tool": null}.\n'
        "Never invent tools or arguments."
    )
