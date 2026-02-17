from __future__ import annotations

import json
from pathlib import Path

import pytest

from openclaw_memory_bench.gateway_client import invoke_tool, resolve_gateway_config


def test_resolve_gateway_config_milady_reads_local_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg_dir = tmp_path / ".milady"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "gateway": {
            "http": {"port": 19009},
            "auth": {"token": "cfg-token"},
        }
    }
    (cfg_dir / "milady.json").write_text(json.dumps(cfg), encoding="utf-8")

    resolved = resolve_gateway_config(namespace="milady")

    assert resolved["namespace"] == "milady"
    assert resolved["gateway_url"] == "http://127.0.0.1:19009"
    assert resolved["gateway_token"] == "cfg-token"
    assert resolved["agent_id"] == "main"
    assert resolved["agent_header"] == "x-milady-agent-id"


def test_resolve_gateway_config_milady_env_overrides(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MILADY_GATEWAY_URL", "http://127.0.0.1:19999/")
    monkeypatch.setenv("MILADY_GATEWAY_TOKEN", "env-token")
    monkeypatch.setenv("MILADY_AGENT_ID", "agent-42")

    resolved = resolve_gateway_config(namespace="milady")

    assert resolved["gateway_url"] == "http://127.0.0.1:19999"
    assert resolved["gateway_token"] == "env-token"
    assert resolved["agent_id"] == "agent-42"


def test_invoke_tool_milady_sets_expected_headers(monkeypatch) -> None:
    monkeypatch.setenv("MILADY_GATEWAY_URL", "http://127.0.0.1:18888")
    monkeypatch.setenv("MILADY_GATEWAY_TOKEN", "token-123")
    monkeypatch.setenv("MILADY_AGENT_ID", "agent-main")

    captured: dict[str, object] = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"ok": true, "result": {"status": "ok"}}'

    def _urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["body"] = req.data.decode("utf-8")
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    out = invoke_tool(
        tool="memory_recall",
        tool_args={"query": "hello", "limit": 2},
        session_key="bench-main",
        namespace="milady",
    )

    assert out == {"status": "ok"}
    assert captured["url"] == "http://127.0.0.1:18888/tools/invoke"
    assert captured["timeout"] == 120

    headers = captured["headers"]
    assert headers["authorization"] == "Bearer token-123"
    assert headers["x-milady-agent-id"] == "agent-main"
    assert headers["x-openclaw-agent-id"] == "agent-main"

    body = json.loads(str(captured["body"]))
    assert body == {
        "tool": "memory_recall",
        "args": {"query": "hello", "limit": 2},
        "sessionKey": "bench-main",
    }


def test_resolve_gateway_config_rejects_unknown_namespace() -> None:
    with pytest.raises(ValueError, match="Unsupported gateway namespace"):
        resolve_gateway_config(namespace="not-real")
