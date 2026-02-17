from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


_SUPPORTED_NAMESPACES = {"openclaw", "milady"}


def _read_json_config(path: str) -> dict:
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize_namespace(namespace: str | None) -> str:
    ns = str(namespace or "openclaw").strip().lower()
    if ns not in _SUPPORTED_NAMESPACES:
        supported = ", ".join(sorted(_SUPPORTED_NAMESPACES))
        raise ValueError(f"Unsupported gateway namespace '{namespace}'. Expected one of: {supported}")
    return ns


def _namespace_settings(namespace: str) -> dict[str, str]:
    if namespace == "milady":
        return {
            "config_path": "~/.milady/milady.json",
            "env_gateway_url": "MILADY_GATEWAY_URL",
            "env_gateway_token": "MILADY_GATEWAY_TOKEN",
            "env_agent_id": "MILADY_AGENT_ID",
            "agent_header": "x-milady-agent-id",
        }

    return {
        "config_path": "~/.openclaw/openclaw.json",
        "env_gateway_url": "OPENCLAW_GATEWAY_URL",
        "env_gateway_token": "OPENCLAW_GATEWAY_TOKEN",
        "env_agent_id": "OPENCLAW_AGENT_ID",
        "agent_header": "x-openclaw-agent-id",
    }


def resolve_gateway_config(overrides: dict | None = None, *, namespace: str = "openclaw") -> dict[str, str]:
    overrides = overrides or {}
    ns = _normalize_namespace(namespace)
    settings = _namespace_settings(ns)
    cfg = _read_json_config(settings["config_path"])

    port = (
        cfg.get("gateway", {}).get("http", {}).get("port")
        or cfg.get("gateway", {}).get("port")
        or 18789
    )

    url = (
        overrides.get("gateway_url")
        or os.environ.get(settings["env_gateway_url"])
        or (os.environ.get("OPENCLAW_GATEWAY_URL") if ns == "milady" else None)
        or f"http://127.0.0.1:{port}"
    )
    token = (
        overrides.get("gateway_token")
        or os.environ.get(settings["env_gateway_token"])
        or (os.environ.get("OPENCLAW_GATEWAY_TOKEN") if ns == "milady" else None)
        or cfg.get("gateway", {}).get("auth", {}).get("token")
        or ""
    )
    agent_id = (
        overrides.get("agent_id")
        or os.environ.get(settings["env_agent_id"])
        or (os.environ.get("OPENCLAW_AGENT_ID") if ns == "milady" else None)
        or "main"
    )

    return {
        "namespace": ns,
        "gateway_url": str(url).rstrip("/"),
        "gateway_token": str(token),
        "agent_id": str(agent_id),
        "agent_header": settings["agent_header"],
    }


def invoke_tool(
    *,
    tool: str,
    tool_args: dict,
    session_key: str = "main",
    config: dict | None = None,
    namespace: str = "openclaw",
) -> Any:
    resolved = resolve_gateway_config(config, namespace=namespace)
    token = resolved["gateway_token"]
    if not token:
        if resolved["namespace"] == "milady":
            raise RuntimeError(
                "Gateway token is required (MILADY_GATEWAY_TOKEN or ~/.milady/milady.json)"
            )
        raise RuntimeError(
            "Gateway token is required (OPENCLAW_GATEWAY_TOKEN or ~/.openclaw/openclaw.json)"
        )

    url = resolved["gateway_url"] + "/tools/invoke"
    payload = {
        "tool": tool,
        "args": tool_args,
        "sessionKey": session_key,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        resolved["agent_header"]: resolved["agent_id"],
    }
    if resolved["namespace"] == "milady":
        # Keep legacy header for mixed stacks that still read OpenClaw naming.
        headers["x-openclaw-agent-id"] = resolved["agent_id"]

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gateway error ({e.code}): {err_body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway request failed: {e}") from e

    data = json.loads(body)
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"tools/invoke returned unexpected payload: {body[:2000]}")
    return data.get("result")
