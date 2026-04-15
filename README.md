# biodepot-catalog

Curated index of BioDepot Docker modules. One YAML file per module
under `modules/`; schema under `schemas/`; tooling (tag parser,
validator) under `tools/`.

This repo **does not store Dockerfiles**. Source Dockerfiles live in
the repos that ship them (widget repos, `bwb-bioc-images`,
`biodepot_baseimages`, etc.). The catalog records pointers to source,
image metadata, and lifecycle state.

## Quick layout

```
biodepot-catalog/
├── schemas/
│   └── catalog-v0.yaml           authoritative schema, v0
├── tools/
│   ├── tag_parser.py             Python port of biodepot-tools tag scheme
│   ├── validate.py               schema validator (run in CI)
│   ├── mcp_server.py             MCP server exposing catalog queries
│   ├── mcp_smoke_test.py         tests MCP tools without a client (CI)
│   └── requirements.txt          mcp[cli] + pyyaml
├── modules/                      one YAML per module id
│   ├── bioc-r-primary.yaml
│   ├── bioc-r-source.yaml
│   ├── bioc-bulk-rna.yaml
│   └── ...
├── inventory/                    periodic sweep snapshots (non-authoritative)
│   └── phase1-sweep-2026-04-15.yaml
└── .github/workflows/
    └── validate.yml              schema + MCP smoke checks on PR
```

## MCP surface

`tools/mcp_server.py` exposes the catalog as four MCP tools:

| Tool | Purpose |
| --- | --- |
| `list_modules(kind?, family?, status?, variant?)` | Compact list view with optional filters |
| `get_module(id)` | Full record for one module |
| `find_by_capability(capability)` | Reverse lookup — "which image gives us X?" |
| `module_update_candidates(tracks, current_upstream)` | Modules whose `upstream.current` lags the caller-supplied upstream state |

Run the server locally (stdio transport):

```
pip install -r tools/requirements.txt
python3 tools/mcp_server.py
```

Connect from a client (Claude Code or any MCP-compatible agent).
Every tool call re-reads `modules/*.yaml` from disk, so catalog
edits land without a restart.

The server is **read-only** and **side-effect-free** — it never
polls upstream feeds, never hits Docker Hub, never writes files.
Callers (e.g. the `bioc-module-update` skill) gather upstream state
themselves and pass it in.

## Entry kinds (`kind` discriminator)

- **`tier`** — a curated multi-package image (e.g. `bioc-bulk-rna`).
- **`tool`** — a single-tool image (e.g. `chromap`, `fastqc`).
- **`base`** — a foundational image that other BioDepot images build
  FROM (e.g. `bioc-r-primary`, `rbase`).
- **`external`** — a non-BioDepot image referenced by our workflows
  (e.g. `bioconductor/bioconductor_docker`, biocontainers).

`builds_from` is required on every non-external entry; it names
another catalog id. External upstreams that our images build FROM
are recorded as `kind: external` so the graph closes.

## Field authority

See `schemas/catalog-v0.yaml` for the authority classification:
**authored** (human-owned, stable), **derived** (computed at ingest
time from image or build state), and **seeded** (agent or sweep
populates, human edits freely).

## Bioconductor two-path policy

Bioconductor-flavored images are published in two variants per
release: a **primary** path built FROM
`bioconductor/bioconductor_docker` and a **source** path built FROM
`biodepot/rbase` (source-compiled R with explicit BLAS/LAPACK). Both
are first-class catalog entries. See
`BioDepot/biodepot_baseimages/bioc-r/README.md` for the policy; the
catalog records both variants with distinct ids
(`bioc-r-primary`, `bioc-r-source`).

## Update procedure

The update-agent skill at `~/.claude/skills/bioc-module-update/`
(user-level) coordinates Bioc release bumps across
`bwb-bioc-images`, `biodepot_baseimages`, and this catalog. See
`docker_module_catalog_reorganization_runbook.md` in
`agentic-repo-coordinator` for the broader architecture.
