---
name: bioc-module-update
description: Detect a new Bioconductor release, propose updates to BioDepot tier images and downstream consumers, and coordinate the manifest-update PR flow across bwb-bioc-images and biodepot-catalog. Use when a user mentions a new Bioc release, when `bioconductor/bioconductor_docker` publishes a new `RELEASE_X_Y` tag, or when asked to check whether our Bioc tiers are current.
---

# Bioconductor Module Update

This skill coordinates the detect → propose → land loop for Bioc-tiered
images across the BioDepot fleet. The authoritative catalog for
affected modules is `BioDepot/biodepot-catalog`; the canonical image
sources are `BioDepot/bwb-bioc-images` (curated tiers) and
`BioDepot/biodepot_baseimages` (lower-level bases).

## When to invoke

Trigger on any of:
- User says: "is Bioc X out", "we should bump Bioc", "new Bioconductor release"
- Upstream signal: new tag on `bioconductor/bioconductor_docker` Docker
  Hub, or `release_version` bump in `https://bioconductor.org/config.yaml`
- Scheduled poll (see the companion cron agent, if configured)

Do **not** invoke for R-only or CRAN-only version bumps; those follow
their own cadence and don't require the tier rebuild flow.

## Procedure

### 1. Detect current vs catalog state

```bash
# Upstream current release
curl -sSL https://bioconductor.org/config.yaml | \
  awk '/^release_version:/ {gsub(/"/,"",$2); print $2}'

# Catalog-recorded current release per tier
# (once biodepot-catalog is populated)
gh api repos/BioDepot/biodepot-catalog/contents/modules/bioc-bulk-rna.yaml \
  --jq '.content' | base64 -d | yq '.upstream.current'
```

If upstream > catalog for any Bioc tier, flag for update.

### 2. Identify affected catalog entries

Any entry where either:
- `upstream.tracks == "bioconductor-release"`, OR
- `builds_from` transitively resolves to a catalog entry whose upstream
  tracks Bioc.

Use the catalog's `builds_from` graph (required on non-external
entries) to walk dependents. No grep needed.

### 3. Propose rebuild PRs (home-repo first, catalog second)

For each affected tier:

**3a. Source repo PR** (e.g. `BioDepot/bwb-bioc-images`):
- Branch: `bump/bioc-X.Y`
- Changes: update `BIOC_RELEASE` and `BIOC_RELEASE_TAG` defaults in
  Dockerfile ARG lines and in `scripts/build_and_push.sh`.
- Do NOT hand-edit installed package lists. The hardened `install.R`
  will resolve against the new release; if a package dropped, the
  build will fail loudly at `verify_packages` (that's a feature).
- Title format: `bump: bioc X.Y → X.Z`

**3b. Manifest PR** (same source repo, auto-filed by build CI after
green build):
- CI publishes image, captures digest, updates
  `manifests/bioc_image_digests.yaml` via `peter-evans/create-pull-request`.
- Reviewer's job: inspect the smoke-test log in CI, approve.

**3c. Catalog PR** (`BioDepot/biodepot-catalog`):
- Branch: `bump/bioc-X.Y-<tier>`
- Changes: `upstream.current: X.Y`, `image.tag`, `image.digest`,
  rerun tag-parts parser, bump `status_computed_at`.
- One PR per tier keeps review tractable.

### 4. Human approval checkpoint

Never merge any of the three PRs without human review. The skill
*proposes* rebuilds and opens PRs; it does not auto-merge. Reviewer
decisions:
- Does the smoke test output look plausible?
- Are any newly-required packages absent from the install list?
- Does `BiocManager::valid()` output show `0 too-new` (hard bar)?

### 5. Downstream consumer sweep

After the tier PRs merge, query the catalog for `consumers[]` of each
updated entry. For each consumer that pins by tag (not digest), file
an issue (not a PR — consumer-side pin choices are ambiguous) noting:
- new digest available
- whether the pin should move (tag-following consumers) or stay
  (digest-pinned consumers, which are fine)

## Hardening expectations

Any rebuild flow must preserve the install-time hardening standard
set in `BioDepot/bwb-bioc-images/docker/common/install_helpers.R`:

- `hardened_bioc_install()` — intercepts silent-failure warnings as fatal
- `verify_packages()` — `library()` load-check + `packageVersion()`
- `verify_bioc_valid()` — `$too_new` is always fatal; required-package
  `$out_of_date` is fatal; routine CRAN utility drift is log-only
- `record_installed_versions()` — writes resolved versions into the
  image at `/opt/biodepot/installed_packages.json`

If a rebuild PR removes, weakens, or side-steps any of these checks,
block it.

## Scope boundaries

- **In scope**: Bioc-release-driven bumps for tier images
  (`bwb-bioc-images`), base images (`biodepot_baseimages/bioc-r`),
  and their direct catalog entries. Downstream consumer *notifications*.
- **Out of scope**: arbitrary tool upgrades (`chromap`, `STAR`, etc.) —
  those have their own cadences. Widget-level refactors in BWB. Any
  change to the catalog schema itself.

## Quick commands

```bash
# What Bioc release is current upstream?
curl -sSL https://bioconductor.org/config.yaml | \
  awk '/^release_version:/ {gsub(/"/,"",$2); print $2}'

# What tag does that correspond to for bioconductor/bioconductor_docker?
# Convention: X.Y → RELEASE_X_Y
# e.g. 3.22 → RELEASE_3_22

# Local rebuild of a tier against a new release
cd /path/to/bwb-bioc-images
BIOC_RELEASE=3.22 ./scripts/build_and_push.sh bioc-bulk-rna
# Add PUSH=1 UPDATE_MANIFEST=1 for full publish

# Verify a built image's install manifest
docker run --rm biodepot/bioc-bulk-rna:3.22__... \
  cat /opt/biodepot/installed_packages.json
```

## Related

- Catalog schema: see runbook `docker_module_catalog_reorganization_runbook.md` §6 in `agentic-repo-coordinator`
- Hardening helpers: `BioDepot/bwb-bioc-images/docker/common/install_helpers.R`
- Scheduled poller: optional companion cron agent (separate skill / CronCreate)
