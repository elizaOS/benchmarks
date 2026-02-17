#!/usr/bin/env python3
"""Milady adapter for OpenClaw Benchmark suite.

IMPORTANT: This benchmark measures CONCEPTUAL RESPONSE QUALITY, not actual
code execution. The scoring checks for presence of expected concepts in the
LLM's response text. It does NOT:
- Execute any code
- Verify files were created
- Run tests
- Measure actual implementation quality

For real code execution benchmarks, use SWE-Bench or similar.

Usage:
    python milady_adapter.py --task setup
    python milady_adapter.py --all --json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for milady_adapter imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "milaidy-adapter"))

try:
    from milady_adapter import MiladyClient, MiladyServerManager
    MILADY_AVAILABLE = True
except ImportError:
    MILADY_AVAILABLE = False
    print("Warning: milady_adapter not available, running in standalone mode")

# ---------------------------------------------------------------------------
# Paths & Configuration
# ---------------------------------------------------------------------------
BENCHMARK_DIR = Path(__file__).resolve().parent
MILADY_URL = os.environ.get("MILADY_BENCH_URL", "http://localhost:3939")

# Standard benchmark tasks - these test conceptual understanding, not execution
STANDARD_TASKS = {
    "setup": {
        "name": "Environment Setup",
        "description": "Test understanding of Node.js/TypeScript project initialization",
        "prompt": "Set up a new Node.js project with TypeScript. Create the basic project structure with src/, tests/, and configuration files (package.json, tsconfig.json). Initialize git.",
        # Concepts we expect the LLM to mention - NOT verification of actual work
        "expected_concepts": [
            ("npm init", ["npm init", "package.json", "npm", "pnpm", "yarn"]),
            ("typescript config", ["tsconfig", "typescript", "tsc"]),
            ("git init", ["git init", "git", ".gitignore"]),
            ("directory structure", ["src/", "src", "mkdir", "directory", "folder"]),
        ],
    },
    "implementation": {
        "name": "Feature Implementation",
        "description": "Test understanding of CLI application development",
        "prompt": "Implement a CLI tool that fetches weather data. It should accept a city name as argument, call a weather API (use OpenWeatherMap or similar), and display temperature, humidity, and conditions. Include error handling for invalid cities and network errors.",
        "expected_concepts": [
            ("API call", ["fetch", "axios", "http", "api", "request"]),
            ("argument parsing", ["argv", "argument", "commander", "yargs", "process.argv"]),
            ("error handling", ["try", "catch", "error", "throw", "exception"]),
            ("display output", ["console.log", "print", "output", "display"]),
        ],
    },
    "refactoring": {
        "name": "Code Refactoring",
        "description": "Test understanding of software architecture patterns",
        "prompt": "Refactor the weather CLI to use a modular architecture. Extract the API client to a separate module, add proper TypeScript types, implement dependency injection for testability, and add configuration management for API keys.",
        "expected_concepts": [
            ("module extraction", ["module", "import", "export", "separate"]),
            ("typescript types", ["interface", "type", "types", "typing"]),
            ("dependency injection", ["inject", "dependency", "di", "constructor"]),
            ("configuration", ["config", "environment", "env", "dotenv"]),
        ],
    },
    "testing": {
        "name": "Test Implementation",
        "description": "Test understanding of testing practices",
        "prompt": "Write comprehensive tests for the weather CLI. Include unit tests for the API client (with mocked responses), integration tests for the CLI commands, and add test coverage reporting. Use Jest or Vitest as the test framework.",
        "expected_concepts": [
            ("test framework", ["jest", "vitest", "mocha", "test"]),
            ("mocking", ["mock", "stub", "spy", "vi.mock", "jest.mock"]),
            ("coverage", ["coverage", "istanbul", "c8"]),
            ("assertions", ["expect", "assert", "should", "toBe"]),
        ],
    },
}


def score_conceptual_understanding(task_id: str, response: str) -> dict:
    """
    Score based on conceptual understanding shown in response.

    WARNING: This is NOT code verification. It only checks if the LLM
    mentioned the expected concepts. An LLM could pass by describing
    concepts without actually implementing anything.
    """
    if task_id not in STANDARD_TASKS:
        return {"error": f"Unknown task: {task_id}", "score": 0}

    task = STANDARD_TASKS[task_id]
    response_lower = response.lower()

    checks = []
    passed = 0

    for concept_name, keywords in task["expected_concepts"]:
        found = any(kw.lower() in response_lower for kw in keywords)
        checks.append({
            "concept": concept_name,
            "keywords": keywords,
            "found": found,
        })
        if found:
            passed += 1

    total = len(checks)
    score = passed / total if total > 0 else 0

    return {
        "task_id": task_id,
        "scoring_type": "conceptual_understanding",
        "warning": "This measures concept mention, NOT actual implementation",
        "passed": passed,
        "total": total,
        "score": score,
        "checks": checks,
    }


class OpenClawBenchRunner:
    """Run OpenClaw benchmark tasks."""

    def __init__(self, client=None):
        self.client = client

    def run_task(self, task_id: str) -> dict:
        """Run a single benchmark task."""
        if task_id not in STANDARD_TASKS:
            return {"error": f"Unknown task: {task_id}"}

        task = STANDARD_TASKS[task_id]
        start_time = time.time()

        if self.client:
            # Use milady benchmark server
            self.client.reset(task_id=task_id, benchmark="openclaw")
            response = self.client.send_message(
                text=task["prompt"],
                context={
                    "benchmark": "openclaw",
                    "task_id": task_id,
                    "task_name": task["name"],
                    "task_description": task["description"],
                },
            )
            response_text = response.text
            actions = response.actions
        else:
            # Standalone mode - just return the prompt for manual testing
            response_text = "[No LLM response - running in standalone mode]"
            actions = []

        duration_ms = (time.time() - start_time) * 1000

        # Score conceptual understanding
        score = score_conceptual_understanding(task_id, response_text)

        return {
            "task_id": task_id,
            "task_name": task["name"],
            "prompt": task["prompt"],
            "response": response_text,
            "actions": actions,
            "duration_ms": duration_ms,
            "score": score,
        }

    def run_all(self) -> dict:
        """Run all benchmark tasks."""
        results = {}
        total_score = 0
        task_count = 0

        for task_id in STANDARD_TASKS:
            result = self.run_task(task_id)
            results[task_id] = result
            if "score" in result and isinstance(result["score"], dict):
                total_score += result["score"].get("score", 0)
                task_count += 1

        return {
            "benchmark": "openclaw",
            "scoring_type": "conceptual_understanding",
            "warning": "Scores measure concept mention only, NOT actual implementation",
            "tasks": results,
            "overall_score": total_score / task_count if task_count > 0 else 0,
            "tasks_completed": task_count,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Run OpenClaw benchmark against milady",
        epilog="WARNING: Scores measure conceptual understanding only, not code execution."
    )
    parser.add_argument("--task", "-t", type=str, default=None,
                        help="Task to run (setup, implementation, refactoring, testing)")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Run all tasks")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available tasks")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output JSON")
    parser.add_argument("--output-dir", "-o", type=str, default=None,
                        help="Output directory for results")
    parser.add_argument("--start-server", action="store_true",
                        help="Auto-start milady benchmark server")

    args = parser.parse_args()

    if args.list:
        print("Available OpenClaw benchmark tasks:")
        print("\nWARNING: These measure conceptual understanding, not code execution.\n")
        for task_id, task in STANDARD_TASKS.items():
            print(f"  {task_id:15s} - {task['name']}")
            print(f"  {'':15s}   {task['description']}")
        return

    # Setup client
    client = None
    mgr = None
    if MILADY_AVAILABLE:
        if args.start_server:
            mgr = MiladyServerManager()
            mgr.start()
            client = mgr.client
        else:
            client = MiladyClient(MILADY_URL)
            try:
                client.wait_until_ready(timeout=10)
            except TimeoutError:
                print("Warning: Milady server not available, running in standalone mode")
                client = None

    runner = OpenClawBenchRunner(client)

    if args.all:
        result = runner.run_all()
    elif args.task:
        result = runner.run_task(args.task)
    else:
        print("Error: Specify --task or --all")
        return

    # Save to file if output-dir specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = int(time.time())
        output_file = output_dir / f"openclaw_{args.task or 'all'}_{timestamp}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        if not args.json:
            print(f"Results saved to: {output_file}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.all:
            print(f"\n{'='*60}")
            print("OPENCLAW BENCHMARK RESULTS")
            print("WARNING: Measures concept mention, NOT actual implementation")
            print(f"{'='*60}")
            print(f"\nOverall Score: {result['overall_score']:.1%}")
            print(f"Tasks Completed: {result['tasks_completed']}")
            for task_id, task_result in result.get("tasks", {}).items():
                score = task_result.get("score", {})
                print(f"\n  {task_id}: {score.get('passed', 0)}/{score.get('total', 0)} concepts mentioned")
        else:
            print(f"\n{'='*60}")
            print(f"TASK: {result.get('task_name', 'Unknown')}")
            print("WARNING: Measures concept mention, NOT actual implementation")
            print(f"{'='*60}")
            print(f"\nResponse: {result.get('response', '')[:300]}...")
            score = result.get("score", {})
            print(f"\nConcepts mentioned: {score.get('passed', 0)}/{score.get('total', 0)}")
            for check in score.get("checks", []):
                status = "+" if check["found"] else "-"
                print(f"  {status} {check['concept']}")

    if mgr:
        mgr.stop()


if __name__ == "__main__":
    main()
