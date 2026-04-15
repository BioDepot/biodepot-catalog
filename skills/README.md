# Catalog-adjacent skills

Skills that coordinate with the BioDepot catalog live here under
version control. Each subdirectory ships one skill; install by
symlinking into your agent's skills directory.

## Install

For Claude Code (user-level skills):

```
ln -s $(pwd)/skills/bioc-module-update ~/.claude/skills/bioc-module-update
```

For a repo-local Claude Code install in another project:

```
ln -s /mnt/pikachu/biodepot-catalog/skills/bioc-module-update ./.claude/skills/bioc-module-update
```

Using a symlink (rather than copy) keeps the installed skill on
whatever commit the catalog checkout is at — pulls here propagate
immediately.

## Skills index

- [bioc-module-update](bioc-module-update/SKILL.md) — detects new
  Bioconductor releases, coordinates updates across
  `bwb-bioc-images`, `biodepot_baseimages`, and this catalog.

## Why here

These skills are catalog consumers — they query the MCP surface at
`tools/mcp_server.py` and propose updates to catalog entries. Living
in the catalog repo keeps the skill, the schema it reads, and the
images it updates under one reviewable history.
