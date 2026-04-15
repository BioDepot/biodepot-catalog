#!/usr/bin/env python3
"""Smoke-test the MCP server's tool functions without a client.

Imports the tool callables directly from mcp_server and exercises each
against the real catalog. Runs in CI so schema or code drift surfaces
without requiring a stdio MCP handshake.
"""

from __future__ import annotations

import sys

# Import the tool functions. FastMCP exposes them as attributes of
# the server module; calling the underlying function works for tests.
from mcp_server import (
    list_modules,
    get_module,
    find_by_capability,
    module_update_candidates,
)


def _unwrap(tool):
    """Accept either a raw callable or an MCP-wrapped one. FastMCP may
    wrap the function in a Tool object; if so, pull out .fn."""
    if callable(tool):
        return tool
    return getattr(tool, "fn", tool)


def main() -> int:
    errors: list[str] = []

    ls = _unwrap(list_modules)
    gm = _unwrap(get_module)
    fc = _unwrap(find_by_capability)
    uc = _unwrap(module_update_candidates)

    # list_modules without filters returns every module.
    all_mods = ls()
    if not isinstance(all_mods, list) or not all_mods:
        errors.append(f"list_modules() returned {type(all_mods).__name__} (expected non-empty list)")
    else:
        print(f"OK list_modules() -> {len(all_mods)} entries")

    # Filter by kind.
    tiers = ls(kind="tier")
    print(f"OK list_modules(kind='tier') -> {len(tiers)} entries")
    if any(e["kind"] != "tier" for e in tiers):
        errors.append("list_modules(kind='tier') returned non-tier entries")

    # Filter by family.
    bioc = ls(family="bioconductor")
    print(f"OK list_modules(family='bioconductor') -> {len(bioc)} entries")

    # get_module known-good id.
    entry = gm("bioc-bulk-rna")
    if entry.get("id") != "bioc-bulk-rna":
        errors.append(f"get_module('bioc-bulk-rna') returned id={entry.get('id')!r}")
    else:
        print(f"OK get_module('bioc-bulk-rna') -> {entry['image']['repo']}:{entry['image']['tag']}")

    # get_module missing id raises.
    try:
        gm("no-such-module-xyz")
        errors.append("get_module('no-such-module-xyz') did not raise")
    except LookupError:
        print("OK get_module(missing) raises LookupError")

    # find_by_capability hit.
    deseq = fc("deseq2")
    if not deseq:
        errors.append("find_by_capability('deseq2') returned empty (expected bioc-bulk-rna)")
    else:
        print(f"OK find_by_capability('deseq2') -> {[m['id'] for m in deseq]}")

    # find_by_capability miss returns empty, not error.
    miss = fc("no-such-capability-xyz")
    if miss != []:
        errors.append(f"find_by_capability(miss) returned {miss!r} (expected [])")
    else:
        print("OK find_by_capability(miss) -> []")

    # module_update_candidates: pretend Bioc 3.23 exists; every
    # Bioc-release-tracking entry on 3.22 should show up.
    cands = uc(tracks="bioconductor-release", current_upstream="3.23")
    print(f"OK module_update_candidates(bioc->3.23) -> {len(cands)} candidates")
    if not cands:
        errors.append("module_update_candidates(3.23) found 0 candidates (expected several)")

    # module_update_candidates: current release returns empty.
    cands_now = uc(tracks="bioconductor-release", current_upstream="3.22")
    if cands_now:
        errors.append(f"module_update_candidates(3.22) returned {len(cands_now)} (expected 0)")
    else:
        print("OK module_update_candidates(3.22) -> 0 candidates")

    if errors:
        print("\nFAIL:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("\nALL MCP TOOL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
