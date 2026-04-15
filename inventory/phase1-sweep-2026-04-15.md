# BioDepot Docker Fleet Inventory - Phase 1 Sweep
**Date:** 2026-04-15

## Executive Summary

This inventory captures a snapshot of the BioDepot Docker fleet across the GitHub org, local development repos, and remote storage. The primary enumeration used GitHub's `search/code` API (paginated, partial due to rate limits) combined with local glob patterns and remote discovery. We identified **133 unique Dockerfiles** spanning 34 repositories.

### Methodology

- **GitHub API:** `gh api search/code?q=org:BioDepot+filename:Dockerfile` (partial batch due to 403 rate limit)
- **Local directories:**
  - `/mnt/pikachu/BioDepot-workflow-builder/widgets/` -> 82 widget Dockerfiles with 32 JSON siblings
  - `/mnt/pikachu/bwb-nextflow-utils/` -> 1 tier/tool Dockerfiles
- **Remote:** `ssh lhhung@128.208.252.232:/srv/lhhung/Dockerfiles` -> 1 orphan Dockerfile
- **Widget JSON sibling scan:** Extracted `docker_image_name` and `docker_image_tag` from 32 colocated `.json` files

### Counts Summary

| Dimension | Count |
|-----------|-------|
| **Total unique Dockerfiles** | 133 |
| **BioDepot org repos** | 132 |
| **lhhunghimself user** | 0 |
| **Sunflower orphan** | 1 |
| **With widget JSON sibling** | 32 |

### Kind Breakdown

| Kind | Count | Purpose |
|------|-------|---------|
| widget | 82 | Workflow widgets (BioDepot-workflow-builder) |
| unknown | 38 | Unclassified (need review) |
| base | 11 | Base/tier images (Bioc, Jupyter) |
| tool | 1 | Specialized tools (LINCS, etc.) |
| tier | 1 | Tier abstractions |

### Category Breakdown (widgets only)

| Category | Total | With JSON |
|----------|-------|-----------|
| Utilities | 13 | 11 |
| Scripting | 10 | 10 |
| RNA_seq | 8 | 8 |
| Jupyter | 3 | 3 |

## Top 5 Most-Referenced Docker Images

Based on `docker_image_name` in widget JSON siblings:

1. **biodepot/kallisto** — referenced 2 times
2. **biodepot/star** — referenced 2 times
3. **biodepot/python** — referenced 2 times
4. **biodepot/jupyter-r** — referenced 1 times
5. **biodepot/jupyter-bioc-r** — referenced 1 times


## Hotspots & Observations

### Repositories with >5 Dockerfiles

- **BioDepot/BioDepot-workflow-builder** — 37 Dockerfiles
- **BioDepot/COVID-RNAseq** — 12 Dockerfiles
- **BioDepot/fiji-demo** — 11 Dockerfiles
- **BioDepot/LINCS_RNAseq_cpp** — 7 Dockerfiles
- **BioDepot/fast-bff** — 6 Dockerfiles


### Overrepresented Categories

- **Utilities** (13/34 widgets): Gen3, S3, cloud download/upload, fastqDump, fiji, IGV, etc.
  - Suggests heavy integration with external data sources and GUI tools
- **Scripting** (10/34 widgets): Python, Perl, Java, R, Nextflow, Cromwell
  - Core workflow orchestration layer; mature ecosystem
- **RNA_seq** (8/34 widgets): STAR, Kallisto, Salmon, RSEM, Sleuth, DESeq2
  - Well-covered, aligns with seed Bioc 3.22 chain

### Gaps & Surprises

#### Widgets Without JSON Siblings

50 widget Dockerfiles are missing colocated `.json` metadata:

- BioDepot/BioDepot-workflow-builder: `widgets/Utilities/fastqDump/Dockerfiles/Dockerfiles-alpine/Dockerfile`
- BioDepot/BioDepot-workflow-builder: `widgets/Utilities/fastqDump/Dockerfiles/Dockerfiles-debian/Dockerfile`
- BioDepot/COVID-RNAseq: `Salmon-workflows-generalized/star_salmon_dashboard/widgets/star_salmon_dashboard/R_notebook/Dockerfiles/Dockerfile`
- BioDepot/COVID-RNAseq: `star_salmon_dashboard/widgets/star_salmon_dashboard/10x_format_fa_gtf/Dockerfiles/Dockerfile`
- BioDepot/COVID-RNAseq: `star_salmon_dashboard/widgets/star_salmon_dashboard/R_notebook/Dockerfiles/Dockerfile`
- ... and 45 more


#### Non-biodepot/ Docker Images

5 external image references detected (not `biodepot/*`):
- `nextflow/nextflow`
- `openjdk`
- `quay.io/ucsc_cgl/rsem`
- `varikmp/cromwell`
- `varikmp/toil_slurm`


#### Multiple Dockerfiles per Widget

A few widgets have multiple Dockerfile variants (e.g., alpine, debian, GPU):
- `fastqDump` — 3 variants (main, alpine, debian)
- `bonito`, `dorado`, `guppySetup` — GPU variants

These should be consolidated into single entries with variant tags in `modules/` entries.

### Known Gaps

- **GitHub API rate limit:** Only 98 entries retrieved before 403 error. Estimated ~270 total via first query; need authenticated pagination or retry after cooldown.
- **lhhunghimself user:** Could not enumerate due to rate limit; biodepot_baseimages transferred today, but older refs may exist.
- **Remote sunflower:** Single entry enumerated; no content inspection (low confidence on classification).
- **Last-modified dates:** Deferred; would require individual `gh api repos/X/commits?path=Y` calls (~270 more API hits).

## Recommendations for Next Phase

### Immediate (High-Value)

1. **Retry GitHub API enumeration** after rate limit recovery or with authenticated token. Aim for complete list of ~270 Dockerfiles.
2. **Promote tier images first:**
   - `BioDepot/bwb-bioc-images`: `docker/bioc-{bulk-rna, single-cell, bridges}` — re-usable foundations
   - `BioDepot/biodepot_baseimages`: Bioc 3.22 tier chain + legacy versions
   - These unlock downstream widgets.

3. **High-fanout tools** (appear in many workflows):
   - `biodepot/star` (aligner, RNA-seq backbone)
   - `biodepot/kallisto` (lightweight quantification)
   - `biodepot/salmon` (modern aligner/quantifier)
   - `biodepot/python*` (scripting base)

### Secondary (Good Candidates)

4. **RNA_seq pipeline tools** — mature, well-supported by Bioconductor:
   - Sleuth (transcriptomics statistics)
   - RSEM (expectation-maximization quantification)
   - DESeq2 (differential expression)

5. **Data access & utilities**:
   - FastQDump (SRA ingestion) — 3 variants, consolidate
   - S3/GCloud/Gen3 upload/download (cloud integration)
   - FastQC (universal QC)

### Defer (Lower Priority for v1)

6. **User/Miscellaneous/One-off widgets:**
   - QuPath (imaging, spatial) — specialized use case
   - Jupyter variants (already covered by tier)
   - Orchestration tools (Nextflow, Cromwell) — meta-tools, not data processing

## Next Steps

1. Resolve GitHub API rate limit and re-run enumeration.
2. Classify all 270 entries (kind_guess, category, priority).
3. Extract all docker_image_name/tag pairs for consistency audit.
4. Cross-check Docker Hub availability (images that are built vs. external refs).
5. Begin promoting top 20-30 entries into `modules/` directory.

---

**Report generated:** 2026-04-15  
**Data source:** Partial GitHub API batch + local enumeration  
**Next sweep:** After full GitHub enumeration and module promotion milestone
