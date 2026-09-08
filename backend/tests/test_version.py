import subprocess

from fastapi.testclient import TestClient

from main import app
from routers import version as version_router
from routers.version import _resolve_commit

client = TestClient(app)


def setup_function() -> None:
    # The resolver is cached for the process lifetime, so each test has to start
    # from a clean slate or it just re-reads whatever the previous one resolved.
    _resolve_commit.cache_clear()


def teardown_function() -> None:
    _resolve_commit.cache_clear()


def test_version_reports_a_commit_and_its_source():
    body = client.get("/version").json()
    assert body["commit"]
    assert body["source"]
    # Must hold whether or not the tree this runs in happens to be dirty.
    assert body["short"] == version_router._shorten(body["commit"])


def test_deploy_env_var_wins_over_the_working_tree(monkeypatch):
    # The deployed case: Render injects the commit and there is no .git to read.
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    body = client.get("/version").json()
    assert body["commit"] == "a" * 40
    assert body["short"] == "aaaaaaa"
    assert body["source"] == "RENDER_GIT_COMMIT"


def test_falls_back_to_the_working_tree_when_no_env_var(monkeypatch):
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_COMMIT"):
        monkeypatch.delenv(var, raising=False)
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    body = client.get("/version").json()
    assert body["source"] == "git"
    # Passes in CI (clean checkout) and on a developer's machine mid-edit alike.
    assert body["commit"].removesuffix("-dirty") == expected


def test_marks_a_dirty_working_tree(monkeypatch):
    # Uncommitted edits mean the running code isn't the commit it would name.
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_COMMIT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        version_router,
        "_git",
        lambda *args: "b" * 40 if args[0] == "rev-parse" else " M some/file.py",
    )
    body = client.get("/version").json()
    assert body["commit"] == "b" * 40 + "-dirty"
    # Abbreviating must not drop the marker — it's the informative half.
    assert body["short"] == "bbbbbbb-dirty"


def test_clean_working_tree_is_not_marked(monkeypatch):
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_COMMIT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        version_router,
        "_git",
        lambda *args: "c" * 40 if args[0] == "rev-parse" else "",
    )
    body = client.get("/version").json()
    assert body["commit"] == "c" * 40
    assert body["short"] == "ccccccc"


def test_deployed_commit_is_never_marked_dirty(monkeypatch):
    # A deploy builds from a clean checkout, and the env var path must not shell
    # out to git at all — there is no working tree to ask about.
    monkeypatch.setenv("RENDER_GIT_COMMIT", "d" * 40)

    def fail(*args, **kwargs):
        raise AssertionError("must not run git when the deploy told us the commit")

    monkeypatch.setattr(version_router, "_git", fail)
    body = client.get("/version").json()
    assert body["commit"] == "d" * 40
    assert "-dirty" not in body["short"]


def test_reports_unknown_rather_than_failing_when_nothing_resolves(monkeypatch):
    # A deployed image with neither the env var nor a working tree must still
    # answer: the endpoint exists to be asked when things look wrong.
    for var in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_COMMIT"):
        monkeypatch.delenv(var, raising=False)

    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", no_git)
    body = client.get("/version").json()
    assert body["commit"] == "unknown"
    assert body["short"] == "unknown"
    assert body["source"] == "unavailable"
