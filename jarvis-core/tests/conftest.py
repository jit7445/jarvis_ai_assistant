import pytest


@pytest.fixture(autouse=True)
def no_home_scan(monkeypatch):
    """Routing an unknown app name looks for a project; tests must not depend on this Mac."""
    from jarvis.coding import repos
    monkeypatch.setattr(repos, "all_repos", lambda root=None: [])
