import os

import pytest

from jarvis import config
from jarvis.tools.paths import safe_path


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(config, "WORKSPACE", ws)
    return ws


@pytest.mark.parametrize("bad", [
    # from the plan
    "../secrets.txt", "../../.ssh/id_rsa", "/etc/passwd",
    "notes/../../.env", "~/Documents/taxes.pdf",
    # more ways out
    "..", "../", "a/../../b", "./../x", "notes/../groceries.md", "/", "//etc/passwd", "/Users",
    "~", "~root/.profile", "~/.ssh",
    # hidden names, including inside the workspace
    ".env", ".ssh/id_rsa", "notes/.env", ".git/config", ".hidden",
    # the workspace itself, and empties
    "", ".", "./", "   ", "notes/..",
    # control characters
    "a\x00b", "line\nbreak", "tab\there",
])
def test_rejects_escape(bad):
    with pytest.raises(PermissionError):
        safe_path(bad)


@pytest.mark.parametrize("bad", [None, 7, b"notes", ["notes"]])
def test_rejects_non_strings(bad):
    with pytest.raises(PermissionError):
        safe_path(bad)


def test_rejects_symlink_out_of_workspace(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    os.symlink(outside, workspace / "link")
    with pytest.raises(PermissionError):
        safe_path("link/secret.txt")
    with pytest.raises(PermissionError):
        safe_path("link")


def test_rejects_symlinked_file_out_of_workspace(workspace, tmp_path):
    target = tmp_path / "secret.txt"
    target.write_text("secret")
    os.symlink(target, workspace / "innocent.md")
    with pytest.raises(PermissionError):
        safe_path("innocent.md")


def test_allows_symlink_that_stays_inside(workspace):
    (workspace / "real").mkdir()
    os.symlink(workspace / "real", workspace / "alias")
    assert safe_path("alias/note.md") == workspace.resolve() / "real" / "note.md"


@pytest.mark.parametrize("good, expected", [
    ("Research", "Research"),
    ("Research Jarvis Agent", "Research Jarvis Agent"),
    ("groceries.md", "groceries.md"),
    ("projects/ideas.md", "projects/ideas.md"),
    ("  Research  ", "Research"),
])
def test_allows_ordinary_names(workspace, good, expected):
    assert safe_path(good) == workspace.resolve() / expected


def test_missing_workspace_fails_closed(workspace, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE", workspace / "does-not-exist")
    with pytest.raises(FileNotFoundError):
        safe_path("Research")
