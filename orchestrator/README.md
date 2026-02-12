# ElizaOS Benchmark Orchestrator

Run any integrated benchmark (or all benchmarks), store normalized results in
SQLite/JSON, and inspect history in the browser viewer.

## Paths

- Results DB: `benchmarks/benchmark_results/orchestrator.sqlite`
- Viewer dataset: `benchmarks/benchmark_results/viewer_data.json`
- Static viewer UI: `benchmarks/viewer/index.html`

## List integrated benchmarks

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator list-benchmarks
```

This verifies adapter coverage for all benchmark directories under `benchmarks/`.

## Run benchmarks idempotently

Run one benchmark:

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator run \
  --benchmarks solana \
  --provider groq \
  --model qwen/qwen3-32b
```

Run all benchmarks:

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator run \
  --all \
  --provider groq \
  --model qwen/qwen3-32b
```

Idempotent behavior:

- Existing successful signatures are skipped automatically.
- `--rerun-failed` reruns only signatures whose latest run failed.
- `--force` always creates a fresh run.

Examples:

```bash
# rerun only failed signatures
/opt/miniconda3/bin/python -m benchmarks.orchestrator run --all --rerun-failed --provider groq --model qwen/qwen3-32b

# force fresh runs
/opt/miniconda3/bin/python -m benchmarks.orchestrator run --all --force --provider groq --model qwen/qwen3-32b
```

## Extra benchmark config

Use `--extra` with a JSON object for benchmark-specific knobs.
Adapter defaults are applied first, then `--extra` overrides are merged on top.
This keeps `run --all` idempotent with stable per-benchmark baseline settings
while still letting you override knobs when needed.

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator run \
  --benchmarks osworld \
  --provider groq \
  --model qwen/qwen3-32b \
  --rerun-failed \
  --extra '{"max_tasks":1,"headless":true,"vm_ready_timeout_seconds":21600}'
```

## Viewer

Serve live viewer API + UI:

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator serve-viewer --host 127.0.0.1 --port 8877
```

Open: `http://127.0.0.1:8877/`

Viewer supports:

- Historical runs across all benchmarks.
- Sorting by `agent`, `run_id`, and other columns.
- High-score comparison columns (`high_score`, `delta`).
- Filtering by benchmark/status and text search.

## Rebuild viewer dataset

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator export-viewer-data
```

## Recover stale/interrupted runs

If an orchestrator process is interrupted, rows can remain in `running` state.
Recover them immediately and regenerate the viewer dataset:

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator recover-stale-runs --stale-seconds 0
```

Default behavior only recovers runs older than 300 seconds:

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator recover-stale-runs
```

## Show runs in terminal

```bash
/opt/miniconda3/bin/python -m benchmarks.orchestrator show-runs --desc --limit 200
```

`show-runs` is sorted by `(agent, run_id)` and is useful for quick auditing.

## Stored metadata per run

Each run stores:

- benchmark ID + directory
- run ID + run group ID + signature + attempt
- status, duration, score, metrics, artifacts
- provider, model, agent label
- extra config used for the run
- benchmark and Eliza commit/version metadata
- high-score reference and delta
