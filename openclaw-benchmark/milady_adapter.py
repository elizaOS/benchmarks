"""Milady adapter for OpenClaw Benchmark suite.

This adapter runs the OpenClaw benchmark tasks against the milady benchmark server.
The benchmark suite tests AI coding assistants on standard tasks like:
- Setup: Environment initialization
- Implementation: Feature development (e.g., Weather CLI)
- Refactoring: Code improvement
- Testing: Writing and running tests

Usage:
    python milady_adapter.py --task setup
    python milady_adapter.py --task implementation --list
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for milady_adapter imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "milaidy-adapter"))
from milady_adapter import MiladyClient, MiladyServerManager

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BENCHMARK_DIR = Path(__file__).resolve().parent
TASKS_FILE = BENCHMARK_DIR / "benchmark" / "standard_tasks.md"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MILADY_URL = os.getenv("MILADY_BENCH_URL", "http://localhost:3939")

# Standard benchmark tasks
STANDARD_TASKS = {
    "setup": {
        "name": "Environment Setup",
        "description": "Initialize the development environment",
        "prompt": "Set up a new Node.js project with TypeScript. Create the basic project structure with src/, tests/, and configuration files (package.json, tsconfig.json). Initialize git.",
    },
    "implementation": {
        "name": "Feature Implementation",
        "description": "Implement a weather CLI application",
        "prompt": "Implement a CLI tool that fetches weather data. It should accept a city name as argument, call a weather API (use OpenWeatherMap or similar), and display temperature, humidity, and conditions. Include error handling for invalid cities and network errors.",
    },
    "refactoring": {
        "name": "Code Refactoring",
        "description": "Improve code quality and structure",
        "prompt": "Refactor the weather CLI to use a modular architecture. Extract the API client to a separate module, add proper TypeScript types, implement dependency injection for testability, and add configuration management for API keys.",
    },
    "testing": {
        "name": "Test Implementation",
        "description": "Write and run tests",
        "prompt": "Write comprehensive tests for the weather CLI. Include unit tests for the API client (with mocked responses), integration tests for the CLI commands, and add test coverage reporting. Use Jest or Vitest as the test framework.",
    },
}


class MiladyOpenClawRunner:
    """Run OpenClaw benchmark tasks against milady."""

    def __init__(self, client: MiladyClient):
        self.client = client

    def run_task(self, task_id: str) -> dict:
        """Run a single benchmark task."""
        if task_id not in STANDARD_TASKS:
            return {"error": f"Unknown task: {task_id}"}

        task = STANDARD_TASKS[task_id]

        # Reset milady session
        self.client.reset(task_id=task_id, benchmark="openclaw")

        start_time = time.time()

        # Send the task prompt
        response = self.client.send_message(
            text=task["prompt"],
            context={
                "benchmark": "openclaw",
                "task_id": task_id,
                "task_name": task["name"],
                "task_description": task["description"],
            },
        )

        duration_ms = (time.time() - start_time) * 1000

        # Build result
        result = {
            "task_id": task_id,
            "task_name": task["name"],
            "prompt": task["prompt"],
            "response": response.text,
            "thought": response.thought,
            "actions": response.actions,
            "params": response.params,
            "duration_ms": duration_ms,
        }

        # Basic scoring - check if response contains expected elements
        score = self._score_response(task_id, response.text, response.actions)
        result["score"] = score

        return result

    def _score_response(self, task_id: str, response: str, actions: list[str]) -> dict:
        """Score the response based on task requirements."""
        checks = []
        passed = 0

        if task_id == "setup":
            checks = [
                ("mentions package.json", "package.json" in response.lower()),
                ("mentions tsconfig", "tsconfig" in response.lower()),
                ("mentions git", "git" in response.lower()),
                ("creates src directory", "src" in response.lower() or "mkdir" in str(actions)),
            ]
        elif task_id == "implementation":
            checks = [
                ("mentions API", "api" in response.lower()),
                ("mentions fetch/request", any(x in response.lower() for x in ["fetch", "request", "http", "axios"])),
                ("handles errors", any(x in response.lower() for x in ["error", "catch", "try"])),
                ("processes city argument", "city" in response.lower() or "argument" in response.lower()),
            ]
        elif task_id == "refactoring":
            checks = [
                ("mentions modules", any(x in response.lower() for x in ["module", "import", "export"])),
                ("mentions types", any(x in response.lower() for x in ["type", "interface", "typescript"])),
                ("mentions injection", any(x in response.lower() for x in ["inject", "dependency", "di"])),
                ("mentions config", "config" in response.lower()),
            ]
        elif task_id == "testing":
            checks = [
                ("mentions test framework", any(x in response.lower() for x in ["jest", "vitest", "mocha"])),
                ("mentions mocking", any(x in response.lower() for x in ["mock", "stub", "spy"])),
                ("mentions coverage", "coverage" in response.lower()),
                ("mentions assertions", any(x in response.lower() for x in ["expect", "assert", "should"])),
            ]

        for name, passed_check in checks:
            if passed_check:
                passed += 1

        return {
            "passed": passed,
            "total": len(checks),
            "score": passed / len(checks) if checks else 0,
            "checks": [{"name": name, "passed": p} for name, p in checks],
        }

    def run_all(self) -> dict:
        """Run all benchmark tasks."""
        results = {}
        total_score = 0
        task_count = 0

        for task_id in STANDARD_TASKS:
            result = self.run_task(task_id)
            results[task_id] = result
            if "score" in result:
                total_score += result["score"]["score"]
                task_count += 1

        return {
            "tasks": results,
            "overall_score": total_score / task_count if task_count > 0 else 0,
            "tasks_completed": task_count,
        }


def main():
    parser = argparse.ArgumentParser(description="Run OpenClaw benchmark against milady")
    parser.add_argument("--task", "-t", type=str, default=None,
                        help="Task to run (setup, implementation, refactoring, testing)")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Run all tasks")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available tasks")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output JSON")
    parser.add_argument("--start-server", action="store_true",
                        help="Auto-start milady benchmark server")

    args = parser.parse_args()

    if args.list:
        print("Available OpenClaw benchmark tasks:")
        for task_id, task in STANDARD_TASKS.items():
            print(f"  {task_id:15s} — {task['name']}")
            print(f"  {'':15s}   {task['description']}")
        return

    # Setup client
    if args.start_server:
        mgr = MiladyServerManager()
        mgr.start()
        client = mgr.client
    else:
        client = MiladyClient(MILADY_URL)
        client.wait_until_ready()

    runner = MiladyOpenClawRunner(client)

    if args.all:
        result = runner.run_all()
    elif args.task:
        result = runner.run_task(args.task)
    else:
        print("Error: Specify --task or --all")
        return

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.all:
            print(f"\n{'='*60}")
            print("OPENCLAW BENCHMARK RESULTS")
            print(f"{'='*60}")
            print(f"\nOverall Score: {result['overall_score']:.2%}")
            print(f"Tasks Completed: {result['tasks_completed']}")
            for task_id, task_result in result.get("tasks", {}).items():
                score = task_result.get("score", {})
                print(f"\n  {task_id}: {score.get('passed', 0)}/{score.get('total', 0)} checks passed")
        else:
            print(f"\n{'='*60}")
            print(f"TASK: {result.get('task_name', 'Unknown')}")
            print(f"{'='*60}")
            print(f"\nResponse: {result.get('response', '')[:300]}...")
            score = result.get("score", {})
            print(f"\nScore: {score.get('passed', 0)}/{score.get('total', 0)} checks")
            for check in score.get("checks", []):
                status = "✓" if check["passed"] else "✗"
                print(f"  {status} {check['name']}")

    if args.start_server:
        mgr.stop()


if __name__ == "__main__":
    main()
