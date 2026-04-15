#!/usr/bin/env python3
"""Validate every modules/*.yaml against schemas/catalog-v0.yaml.

The schema is intentionally descriptive rather than a strict JSON
Schema — the rules enforced here are the load-bearing ones:
  - required fields present
  - kind in allowed set
  - builds_from present on non-external entries
  - builds_from target exists in the catalog (graph closure)
  - status in allowed set
  - id uniqueness

Run: python3 tools/validate.py
Exits non-zero if any check fails; prints each failure with the
offending file + key.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "modules"

VALID_KINDS = {"tier", "tool", "base", "external"}
VALID_STATUSES = {"active", "stale", "orphaned", "legacy"}
VALID_VARIANTS = {"primary", "source", None}


def load_modules() -> dict[str, tuple[Path, dict]]:
    entries: dict[str, tuple[Path, dict]] = {}
    for path in sorted(MODULES_DIR.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f)
        if data is None:
            fail(path, "-", "empty file")
        if "id" not in data:
            fail(path, "-", "missing required field: id")
        eid = data["id"]
        if eid in entries:
            fail(path, "id", f"duplicate id: {eid} (also in {entries[eid][0].name})")
        entries[eid] = (path, data)
    return entries


errors: list[str] = []


def fail(path: Path, key: str, msg: str) -> None:
    errors.append(f"{path.name} [{key}]: {msg}")


def check_entry(path: Path, data: dict, all_ids: set[str]) -> None:
    eid = data.get("id", "<unknown>")

    kind = data.get("kind")
    if kind not in VALID_KINDS:
        fail(path, "kind", f"invalid kind: {kind!r} (expected one of {sorted(VALID_KINDS)})")

    if "image" not in data or not isinstance(data["image"], dict):
        fail(path, "image", "missing or non-dict")
    else:
        if not data["image"].get("repo"):
            fail(path, "image.repo", "missing")

    builds_from = data.get("builds_from")
    if kind != "external":
        if not builds_from:
            fail(path, "builds_from", "required on non-external entries")
        elif builds_from not in all_ids:
            fail(path, "builds_from", f"{builds_from!r} is not a known catalog id")

    status = data.get("status")
    if status not in VALID_STATUSES:
        fail(path, "status", f"invalid status: {status!r} (expected one of {sorted(VALID_STATUSES)})")

    variant = data.get("variant")
    if variant not in VALID_VARIANTS:
        fail(path, "variant", f"invalid variant: {variant!r} (expected primary|source|null)")


def main() -> int:
    if not MODULES_DIR.exists():
        print(f"no modules/ dir at {MODULES_DIR}", file=sys.stderr)
        return 1

    entries = load_modules()
    all_ids = set(entries)
    for path, data in entries.values():
        check_entry(path, data, all_ids)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(f"OK: {len(entries)} catalog entries valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
