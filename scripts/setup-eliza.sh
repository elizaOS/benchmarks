#!/usr/bin/env bash
# Bootstrap (or refresh) the eliza/ submodule so @elizaos/* packages resolve
# from source. Run after cloning and after every submodule bump:
#
#   bash scripts/setup-eliza.sh          # init/refresh + install + build + sync
#   bash scripts/setup-eliza.sh --pull   # also fast-forward the submodule to
#                                        # upstream develop first
#
# See scripts/sync_eliza_workspace.py for how the root workspace absorbs the
# submodule's package closure.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "${1:-}" == "--pull" ]]; then
  git submodule update --remote --depth 1 eliza
else
  git submodule update --init --depth 1 eliza
fi

echo "==> bun install (submodule)"
(cd eliza && bun install)

echo "==> codegen (action-search keywords)"
(cd eliza && bun run generate:action-search-keywords)

echo "==> turbo build (dist for packages without an eliza-source '.' export)"
# The filters are exactly the @elizaos roots our workspace packages consume;
# turbo builds each one's dependency graph. Keep in sync with
# `python3 scripts/sync_eliza_workspace.py` output (its "roots").
(cd eliza && bunx turbo build \
  --filter=@elizaos/core \
  --filter=@elizaos/agent \
  --filter=@elizaos/shared \
  --filter=@elizaos/scenario-runner \
  --filter=@elizaos/plugin-agent-orchestrator \
  --filter=@elizaos/plugin-calendar \
  --filter=@elizaos/plugin-local-inference \
  --filter=@elizaos/plugin-personal-assistant \
  --filter=@elizaos/plugin-sql \
  --filter=@elizaos/plugin-anthropic \
  --filter=@elizaos/plugin-openai \
  --filter=@elizaos/plugin-computeruse \
  --filter=@elizaos/plugin-cli-inference)

echo "==> sync root workspace from submodule"
python3 scripts/sync_eliza_workspace.py

echo "==> bun install (root)"
bun install

echo "setup-eliza: done"
