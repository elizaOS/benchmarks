#!/usr/bin/env python3
"""Run the experience benchmark suite.

Usage:
    python run_benchmark.py
    python run_benchmark.py --experiences 2000 --queries 200 --output results.json
"""

import argparse
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "plugin-experience" / "python"))

from elizaos_experience_bench.runner import ExperienceBenchmarkRunner
from elizaos_experience_bench.types import BenchmarkConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Experience Plugin Benchmark")
    parser.add_argument("--experiences", type=int, default=1000, help="Number of synthetic experiences")
    parser.add_argument("--queries", type=int, default=100, help="Number of retrieval queries")
    parser.add_argument("--learning-cycles", type=int, default=20, help="Number of learning cycle scenarios")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    config = BenchmarkConfig(
        num_experiences=args.experiences,
        num_retrieval_queries=args.queries,
        num_learning_cycles=args.learning_cycles,
        seed=args.seed,
    )

    runner = ExperienceBenchmarkRunner(config)
    runner.run_and_report(output_path=args.output)


if __name__ == "__main__":
    main()
