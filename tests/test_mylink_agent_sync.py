from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mylink_agent_sync import fetch_feed, render_markdown, sync


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_fetch_feed_validates_envelope(monkeypatch):
    monkeypatch.setattr(
        "tools.mylink_agent_sync.urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {"ok": True, "posts": [{"agent_id": "a1", "text": "hello", "replies": "bad"}]}
        ),
    )
    feed = fetch_feed("https://example.test/api/feed")
    assert feed["posts"][0]["agent_id"] == "a1"
    assert feed["posts"][0]["replies"] == []


def test_fetch_feed_rejects_invalid_url():
    with pytest.raises(ValueError, match="HTTPS"):
        fetch_feed("http://example.test/feed")


def test_render_markdown_is_bounded_and_instruction_safe():
    markdown = render_markdown(
        {"source": "https://example.test/feed", "posts": [{"id": "1", "agent_id": "agent", "kind": "post", "text": "line 1\nline 2", "endorsements": 2}]},
        limit=1,
    )
    assert "Read-only snapshot" in markdown
    assert "line 1 line 2" in markdown
    assert "agent" in markdown


def test_sync_writes_parent_directories_atomically(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "tools.mylink_agent_sync.urlopen",
        lambda *_args, **_kwargs: FakeResponse({"ok": True, "posts": [{"agent_id": "a1", "text": "hello"}]}),
    )
    output = tmp_path / ".aide" / "feed.md"
    result = sync("https://example.test/feed", output, 30)
    assert result["posts"] == 1
    assert output.read_text(encoding="utf-8").startswith("# MyLink feed context")
    assert list(output.parent.glob(".*.feed.md.*")) == []
