"""Exercise standalone matrix and inventory commands outside the checkout cwd."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("command", ["validate-matrix", "inventory"])
def test_repository_commands_resolve_their_own_checkout(command: str, tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repository.parent)
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks.orchestrator", command, "--format", "json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    if command == "validate-matrix":
        assert report["cells"], "The command must produce adapter/harness decisions"
        assert report["error_count"] == 0
    else:
        assert report["adapter_count"] > 0
