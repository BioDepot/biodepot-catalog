#!/usr/bin/env python3
"""MCP server exposing the biodepot-catalog as queryable tools.

Tools:
  - list_modules(kind?, family?, status?, variant?)
  - get_module(id)
  - find_by_capability(capability)
  - module_update_candidates(tracks, current_upstream)

All tools are read-only — the server never writes catalog files.
Data source: modules/*.yaml under the repo root (resolved relative
to this file). Each call re-reads from disk so edits land without
a restart.

Run:
  python3 tools/mcp_server.py
(uses stdio transport — connect from a client like Claude Code)

Dependencies:
  pip install 'mcp[cli]' pyyaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from mcp.server.fastmcp import FastMCP


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "modules"

mcp = FastMCP("biodepot-catalog")


def _load_all() -> list[dict[str, Any]]:
    """Load every modules/*.yaml. Fresh read on every call so agents
    see catalog edits without a server restart."""
    entries: list[dict[str, Any]] = []
    for path in sorted(MODULES_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f)
        if data:
            entries.append(data)
    return entries


def _matches(entry: dict, kind: Optional[str], family: Optional[str],
             status: Optional[str], variant: Optional[str]) -> bool:
    if kind is not None and entry.get("kind") != kind:
        return False
    if family is not None and entry.get("family") != family:
        return False
    if status is not None and entry.get("status") != status:
        return False
    if variant is not None and entry.get("variant") != variant:
        return False
    return True


@mcp.tool()
def list_modules(
    kind: Optional[str] = None,
    family: Optional[str] = None,
    status: Optional[str] = None,
    variant: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List catalog modules, optionally filtered.

    Filters stack (all must match). Returns a compact view with the
    fields most useful for discovery: id, kind, family, variant,
    image.repo, image.tag, status, upstream.current. Call get_module
    for the full record.
    """
    out: list[dict[str, Any]] = []
    for e in _load_all():
        if not _matches(e, kind, family, status, variant):
            continue
        img = e.get("image", {}) or {}
        ups = e.get("upstream", {}) or {}
        out.append({
            "id": e.get("id"),
            "kind": e.get("kind"),
            "family": e.get("family"),
            "variant": e.get("variant"),
            "image_repo": img.get("repo"),
            "image_tag": img.get("tag"),
            "status": e.get("status"),
            "upstream_current": ups.get("current"),
        })
    return out


@mcp.tool()
def get_module(id: str) -> dict[str, Any]:
    """Return the full catalog record for a module id. Raises
    LookupError if the id is not found."""
    for e in _load_all():
        if e.get("id") == id:
            return e
    raise LookupError(f"no catalog entry with id={id!r}")


@mcp.tool()
def find_by_capability(capability: str) -> list[dict[str, Any]]:
    """Return modules whose capabilities list contains the given
    capability (case-insensitive exact match on list elements).

    Useful when an agent needs to answer "which image gives us X"
    without knowing which catalog id provides it.
    """
    cap = capability.lower()
    out: list[dict[str, Any]] = []
    for e in _load_all():
        caps = [c.lower() for c in (e.get("capabilities") or [])]
        if cap in caps:
            img = e.get("image", {}) or {}
            out.append({
                "id": e.get("id"),
                "kind": e.get("kind"),
                "image_repo": img.get("repo"),
                "image_tag": img.get("tag"),
                "capabilities": e.get("capabilities"),
            })
    return out


@mcp.tool()
def module_update_candidates(
    tracks: str,
    current_upstream: str,
) -> list[dict[str, Any]]:
    """Return modules that would need a bump given an upstream state.

    Args:
      tracks: upstream feed id to check against (e.g.
        "bioconductor-release").
      current_upstream: what the upstream feed says is current now
        (e.g. "3.23").

    A module is a candidate iff
      - upstream.tracks == tracks
      - upstream.current != current_upstream

    The server doesn't poll upstream itself — callers (e.g. the
    bioc-module-update skill) fetch the current upstream state and
    pass it in. Keeps the server side-effect-free.
    """
    out: list[dict[str, Any]] = []
    for e in _load_all():
        ups = e.get("upstream") or {}
        if ups.get("tracks") != tracks:
            continue
        have = str(ups.get("current") or "")
        if have == current_upstream:
            continue
        img = e.get("image", {}) or {}
        out.append({
            "id": e.get("id"),
            "current": have,
            "upstream": current_upstream,
            "image_repo": img.get("repo"),
            "image_tag": img.get("tag"),
            "source_repo": (e.get("source") or {}).get("repo"),
            "source_path": (e.get("source") or {}).get("path"),
        })
    return out


if __name__ == "__main__":
    mcp.run()
