#!/usr/bin/env python3
"""Parse BioDepot Docker image tags into structured components.

Ported from biodepot-tools widgetTools.pm tag-hash scheme.

BioDepot tag conventions in the wild (observed 2026-04-15):

  RELEASE_X_Y                           Bioc tier images (e.g. RELEASE_3_22)
  RELEASE_X_Y-source                    Source-path variant
  {version}__{base}__{hashA}            Two-hash widget tag
  {version}__{base}__{hashA}__{hashB}   Three-hash widget tag
  {version}__{base}__{hashA}__{hashB}__{hashC}   Five-part widget tag
  {version}__{base}                     Baseimage tag (e.g. 4.5.2__bookworm-slim)

The hashes (in five-part form) encode build inputs per the Perl:
  A = dockerfile_dir_hash   (widgetTools.pm::dockerFilesDirectoryHash, first 8)
  B = source_commit         (first 8 of the source repo commit)
  C = layer_id              (first 8 of a composed layer identifier)

Non-BioDepot tags (quay.io/biocontainers/*, library/*) do NOT follow
this scheme — parse_tag returns TagParts(raw=tag, scheme="external")
in that case, signaling that individual components aren't meaningful.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional


RELEASE_RE = re.compile(r"^RELEASE_(\d+)_(\d+)(-source)?$")
UNDERSCORE_RE = re.compile(r"^(?P<version>[^_]+)__(?P<base>[^_]+)(?:__(?P<a>[^_]+))?(?:__(?P<b>[^_]+))?(?:__(?P<c>[^_]+))?$")


@dataclass
class TagParts:
    """Structured view of a parsed tag. Fields set to None are not
    applicable for the matched scheme."""

    raw: str
    scheme: str  # "bioc-release" | "biodepot-hash" | "external"
    version: Optional[str] = None
    base: Optional[str] = None
    dockerfile_dir_hash: Optional[str] = None
    commit: Optional[str] = None
    layer_id: Optional[str] = None
    variant: Optional[str] = None  # "primary" | "source" — only set for bioc-release tags

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def parse_tag(tag: str) -> TagParts:
    """Parse a Docker image tag into TagParts. Never raises on
    unrecognized shapes — returns scheme=external with raw preserved."""
    if not tag:
        raise ValueError("empty tag")

    m = RELEASE_RE.match(tag)
    if m:
        major, minor, source = m.group(1), m.group(2), m.group(3)
        return TagParts(
            raw=tag,
            scheme="bioc-release",
            version=f"{major}.{minor}",
            variant="source" if source else "primary",
        )

    m = UNDERSCORE_RE.match(tag)
    if m:
        return TagParts(
            raw=tag,
            scheme="biodepot-hash",
            version=m.group("version"),
            base=m.group("base"),
            dockerfile_dir_hash=m.group("a"),
            commit=m.group("b"),
            layer_id=m.group("c"),
        )

    return TagParts(raw=tag, scheme="external")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("tag", help="Tag to parse, e.g. RELEASE_3_22 or 2.6.0c__bookworm-slim__4df49ea8")
    p.add_argument("--json", action="store_true", help="Emit JSON")
    args = p.parse_args(argv)

    parts = parse_tag(args.tag)
    if args.json:
        print(json.dumps(parts.to_dict(), indent=2))
    else:
        for k, v in parts.to_dict().items():
            print(f"{k:24s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
