# elizaOS Benchmarks — repository guide for agents

This is the standalone **elizaOS benchmarks** repo: every benchmark suite used
to evaluate Eliza agents, the harness adapters that run the same suites against
other agent backends (Hermes, OpenClaw, Smithers, Codex), and the
`@elizaos/plugin-benchmarks` action-vocabulary plugin. It was extracted from the
elizaOS monorepo. elizaOS runtime dependencies resolve **from source via the
`eliza/` git submodule** (the elizaOS monorepo pinned at a known commit) —
several published `@elizaos` npm betas reference transitive versions that were
never published, so registry resolution is permanently broken. After cloning
(and after every submodule bump) run:

```bash
bash scripts/setup-eliza.sh        # init submodule, install, codegen, build, sync
bash scripts/setup-eliza.sh --pull # same, but fast-forward the submodule first
```

The root `package.json` `workspaces`/`overrides`/`patchedDependencies` sections
below the repo's own members are **generated** by
`python3 scripts/sync_eliza_workspace.py` — never hand-edit them; rerun the
script instead. TS packages consume unbuilt submodule sources through the
`eliza-source` export condition (`customConditions` in tsconfig, vitest
`resolve.conditions`); packages whose exports require `dist/` are built by
`setup-eliza.sh` via turbo.

`CLAUDE.md` and `AGENTS.md` in every directory are **identical** — author
`CLAUDE.md`, then copy it to `AGENTS.md`. Read the directory-local doc before
working inside any suite or package; this root file is the map.

## Layout

```
suites/            One self-contained benchmark per directory. Each carries
                   README.md + AGENTS.md + CLAUDE.md with its exact run command
                   and a no-key smoke path.
harnesses/         Agent-backend adapters: eliza / hermes / openclaw / smithers / codex.
                   The eliza harness boots a real AgentRuntime + model plugins and
                   serves /api/benchmark/message.
registry/          Source of truth. registry/commands.py defines every benchmark
                   (id, run command, requirements, result locator); registry/scores.py
                   holds the scorers. A benchmark is "integrated" only when it has both.
framework/         Shared harness framework (Python + framework/typescript for Bun).
lib/               Shared helpers: results store, pricing, trajectory normalizer,
                   random baseline, TS schemas (lib/src).
plugin-benchmarks/ @elizaos/plugin-benchmarks — published npm plugin with canonical
                   Action wrappers for benchmark tool vocabularies.
viewer/            Static browser UI for inspecting normalized results.
scripts/           Acceptance gate, cost computation, CI helpers.
tests/             Suite-level tests (registry, scoring, normalization, acceptance gate).
docs/              Cross-cutting docs: runbooks, coverage matrices, cost reports.
benchmark_results/ Generated run output — GITIGNORED, never commit.
```

Root Python files (`run.py`, `compare.py`, `bench_cli_types.py`,
`campaign_profile.py`, `action_calling_contract.py`, `publication_contracts.py`)
are the shared bench CLI contract, imported across suites as
`benchmarks.<module>`. The repo imports as the `benchmarks` Python package —
run `python -m benchmarks.…` from the repo's **parent** directory (checkout
must be named `benchmarks`), or put the parent dir on `PYTHONPATH`. The root
`__init__.py` extends the package search path with `suites/`, so each suite
imports as `benchmarks.<suite>` (e.g. `benchmarks.orchestrator`,
`benchmarks.standard`).

## Toolchain

- **TypeScript:** Bun workspaces (`plugin-benchmarks`, `lib`,
  `framework/typescript`, `suites/*`). ESM only.
  `bun install` at the root.
- **Python:** venv at the repo root; per-suite `requirements.txt` where needed.
  Tests with `pytest`.
- **Rust:** the HyperliquidBench runner; `cargo test`.

## Run a benchmark

```bash
# List integrated benchmarks + adapter coverage
python -m benchmarks.orchestrator list-benchmarks

# Run one (idempotent: skips already-successful signatures)
python -m benchmarks.orchestrator run --benchmarks <id> --provider <p> --model <m>

# Run all
python -m benchmarks.orchestrator run --all --provider cerebras --model gemma-4-31b

# Standard academic adapters (MMLU / HumanEval / GSM8K / MT-Bench)
python -m benchmarks.run <mmlu|humaneval|gsm8k|mt_bench> [adapter-args...]
```

`--rerun-failed` reruns only failed signatures; `--force` always makes a fresh
run; `--extra '<json>'` passes benchmark-specific options. Each suite's own
`AGENTS.md` documents the direct (non-orchestrator) command and a no-key
smoke/mock path.

## Test

```bash
pytest tests/ -v                        # suite-level
pytest suites/<benchmark>/.../tests -v  # one benchmark (see its AGENTS.md)
bun run --cwd plugin-benchmarks test    # plugin vitest suite
```

## Conventions

- **One directory per benchmark.** All of a benchmark's code, data, tests, and
  docs live under its `suites/` directory. Don't scatter benchmark code into
  shared dirs.
- **The registry is the source of truth.** A benchmark is integrated only when
  it has an entry in `registry/commands.py` and a scorer in
  `registry/scores.py`. Some directories are run-only / experimental and not
  yet registered — their `AGENTS.md` says so.
- **Results are generated, not committed.** Anything under `benchmark_results/`
  (and per-benchmark run output) is gitignored. Never commit result JSON,
  SQLite DBs, trajectories, logs, or coverage.
- **Every benchmark carries all three docs.** `README.md` (overview),
  `AGENTS.md` (how to run + smoke + test), `CLAUDE.md` (identical to AGENTS.md).
- **No mocked "results".** A green harness run over mock fixtures is not a
  score. Publishable numbers come from real-model runs with the provider/model
  recorded and per-item trajectories captured and spot-reviewed. Scorers reject
  mock results for publishable runs — keep it that way.
- **Fail fast; never fabricate.** Harness code throws on missing data instead
  of substituting zeros/empties. Timeout / partial-output handling must surface
  the failure in the scored artifact, not paper over it.

## Add a benchmark

1. Create `suites/<your-benchmark>/` (harness + tests + three docs).
2. Add a `BenchmarkDefinition` in `registry/commands.py` and a scorer in
   `registry/scores.py`.
3. Classify its CI lane (`scheduled` / `smoke` / `manual`) in the orchestrator's
   CI coverage map — suite tests keep the mapping 1:1 with the registry.
4. Verify with `python -m benchmarks.orchestrator list-benchmarks`.

Operator runbook (remote GPU, calibration/readiness gates, code-agent matrix):
[`docs/ORCHESTRATOR_SUBAGENT_BENCHMARK_RUNBOOK.md`](docs/ORCHESTRATOR_SUBAGENT_BENCHMARK_RUNBOOK.md).
