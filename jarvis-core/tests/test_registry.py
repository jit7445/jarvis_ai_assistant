import pytest

from jarvis.core.intent import Intent
from jarvis.tools.registry import TOOLS, InvalidIntent, check


def test_valid_intent_passes():
    intent = Intent("fs.make_dir", {"name": "Research"})
    assert check(intent) is intent


@pytest.mark.parametrize("intent", [
    Intent("shell.run", {"cmd": "ls"}),
    Intent("fs.delete_all", {}),
    Intent("FS.MAKE_DIR", {"name": "x"}),
    Intent("fs.make_dir", {}),
    Intent("fs.make_dir", {"name": "x", "path": "/etc"}),
    Intent("fs.make_dir", {"Name": "x"}),
    Intent("fs.make_dir", {"name": 7}),
    Intent("fs.make_dir", {"name": "   "}),
    Intent("fs.write_file", {"name": "x"}),
    Intent("fs.list_dir", {"name": "x"}),
    Intent("app.open", {"app_name": ["Terminal"]}),
    Intent("fs.make_dir", ["name", "x"]),
    Intent("fs.make_dir", {"name": "x"}, confirm="yes"),
])
def test_invalid_intents_are_refused(intent):
    with pytest.raises(InvalidIntent):
        check(intent)


def test_registry_has_exactly_the_planned_tools():
    assert set(TOOLS) == {"fs.make_dir", "fs.write_file", "fs.read_file", "fs.list_dir", "app.open"}
