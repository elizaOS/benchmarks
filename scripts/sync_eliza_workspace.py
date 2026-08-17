#!/usr/bin/env python3
"""Sync the root bun workspace with the `eliza/` submodule.

The benchmarks repo consumes elizaOS packages from source via the `eliza/`
git submodule instead of npm (several published @elizaos betas reference
transitive versions that were never published, so registry resolution is
permanently broken — see .github/workflows/ci.yml).

This script makes that consumption self-maintaining. It:

1. Scans our own workspace packages for `@elizaos/*` dependencies declared
   as `workspace:*`.
2. Resolves each to its directory under `eliza/packages/` or `eliza/plugins/`
   and walks the transitive `workspace:*` closure inside the submodule.
3. Writes the resulting directory list into the root package.json
   `workspaces` array (after the repo's own members).
4. Mirrors the submodule root's `overrides`, `patchedDependencies` (with
   paths rewritten to `eliza/...`), and `trustedDependencies` into the root
   package.json — bun only honors these fields at the install root.

Run it after every submodule bump:

    git submodule update --remote eliza
    (cd eliza && bun install)      # optional but keeps the submodule usable standalone
    python3 scripts/sync_eliza_workspace.py
    bun install

Fails loudly when a needed package no longer exists in the submodule.
Stdlib only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ELIZA = REPO_ROOT / "eliza"

# Our own workspace members (kept first in the workspaces array).
OWN_WORKSPACES = [
    "plugin-benchmarks",
    "lib",
    "framework/typescript",
    "suites/*",
    # Nested packages `suites/*` does not match:
    "suites/eliza-1/vision-cua-e2e",
    "suites/lifeops-bench/runner",
]

PRUNE_DIRS = {"node_modules", "dist", ".turbo", ".git", "coverage"}


def load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def scan_submodule_packages() -> dict[str, Path]:
    """Map @elizaos package name -> directory inside the submodule."""
    if not (ELIZA / "package.json").exists():
        sys.exit("eliza/ submodule missing — run: git submodule update --init --depth 1")
    found: dict[str, Path] = {}
    for base in (ELIZA / "packages", ELIZA / "plugins"):
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
            if "package.json" not in files:
                continue
            try:
                name = load(Path(root) / "package.json").get("name")
            except (json.JSONDecodeError, OSError):
                continue
            if name:
                found.setdefault(name, Path(root))
    return found


def own_package_jsons() -> list[Path]:
    out: list[Path] = []
    for pattern in ("plugin-benchmarks", "lib", "framework/typescript"):
        pj = REPO_ROOT / pattern / "package.json"
        if pj.exists():
            out.append(pj)
    suites = REPO_ROOT / "suites"
    for root, dirs, files in os.walk(suites):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        if "package.json" in files:
            out.append(Path(root) / "package.json")
    return out


def needed_roots(packages: dict[str, Path]) -> set[str]:
    """@elizaos names our own packages depend on via workspace:*."""
    needed: set[str] = set()
    for pj in own_package_jsons():
        data = load(pj)
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, spec in (data.get(section) or {}).items():
                if not name.startswith("@elizaos/"):
                    continue
                if not str(spec).startswith("workspace:"):
                    continue
                if name not in packages:
                    sys.exit(
                        f"{pj.relative_to(REPO_ROOT)} needs {name} as workspace:* "
                        "but it does not exist in the eliza submodule"
                    )
                needed.add(name)
    return needed


def workspace_closure(roots: set[str], packages: dict[str, Path]) -> set[str]:
    """Transitive closure over workspace:* dependencies inside the submodule."""
    seen: set[str] = set()
    stack = sorted(roots)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        data = load(packages[name] / "package.json")
        # devDependencies included: bun installs devDeps of every workspace
        # member, so their workspace:* refs must be present too.
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            for dep, spec in (data.get(section) or {}).items():
                if not str(spec).startswith("workspace:"):
                    continue
                if dep not in packages:
                    sys.exit(
                        f"{name} depends on {dep} (workspace:*) but it does not "
                        "exist in the eliza submodule — upstream moved or removed it"
                    )
                if dep not in seen:
                    stack.append(dep)
    return seen


def main() -> None:
    packages = scan_submodule_packages()
    roots = needed_roots(packages)
    closure = workspace_closure(roots, packages)

    dirs = sorted(
        str(packages[name].relative_to(REPO_ROOT)).replace(os.sep, "/") for name in closure
    )

    root_pj_path = REPO_ROOT / "package.json"
    root_pj = load(root_pj_path)
    eliza_pj = load(ELIZA / "package.json")

    root_pj["workspaces"] = OWN_WORKSPACES + dirs
    root_pj["overrides"] = eliza_pj.get("overrides", {})
    root_pj["patchedDependencies"] = {
        spec: f"eliza/{path}" for spec, path in (eliza_pj.get("patchedDependencies") or {}).items()
    }
    for spec, path in root_pj["patchedDependencies"].items():
        if not (REPO_ROOT / path).exists():
            sys.exit(f"patch file missing: {path} (for {spec})")
    root_pj["trustedDependencies"] = eliza_pj.get("trustedDependencies", [])

    # Mirror @elizaos/* npm-alias shims from the submodule root (e.g.
    # @elizaos/vitest-vite -> npm:vite@…, required by the vitest patch).
    # Workspace-spec entries are skipped — those resolve as members.
    shims = {}
    for section in ("dependencies", "devDependencies"):
        for name, spec in (eliza_pj.get(section) or {}).items():
            if name.startswith("@elizaos/") and not str(spec).startswith("workspace:"):
                shims[name] = spec
    dev = root_pj.setdefault("devDependencies", {})
    stale = [k for k in dev if k.startswith("@elizaos/") and k not in shims]
    for k in stale:
        del dev[k]
    dev.update(shims)

    with open(root_pj_path, "w") as f:
        json.dump(root_pj, f, indent=2)
        f.write("\n")

    print(f"roots: {len(roots)}  closure: {len(closure)} submodule packages")
    print(f"workspaces written to {root_pj_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
