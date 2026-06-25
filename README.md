# seed-sifter

`seed-sifter` stores `cubiomes-viewer` search artifacts.

The repo currently contains saved session files, exported CSVs, notes, and analysis artifacts for Minecraft seed searches. It is not a standalone application, library, or automated seed-finding pipeline.

## What This Repo Is For

- Keeping repeatable `cubiomes-viewer` search setups in one place
- Recording the criteria behind a search, so results can be reproduced later
- Storing supporting notes about worldgen, biome noise, and search strategy

## Repository Layout

Current contents:

- [`docs/`](./docs/) - supporting notes and analysis
- [`docs/Cubiomes Multi-Noise System Analysis.md`](./docs/Cubiomes%20Multi-Noise%20System%20Analysis.md) - background research on Cubiomes and Minecraft's multi-noise biome system
- [`searches/`](./searches/) - one folder per seed-hunting investigation
- [`searches/pale-spawns/`](./searches/pale-spawns/) - search artifacts for the `pale-spawns` investigation

Folder conventions:

- `searches/<search-name>/sessions/` - saved `cubiomes-viewer` session files
- `searches/<search-name>/data/raw/` - raw exports from broad scans
- `searches/<search-name>/data/refined/` - narrowed follow-up exports
- `searches/<search-name>/data/analysis-inputs/` - standalone inputs used by notebooks or ranking passes
- `searches/<search-name>/analysis/` - notebooks or ad hoc analysis artifacts
- `searches/<search-name>/results/` - shortlists or final candidate seeds
- `notes/` or `docs/` - writeups explaining search goals, tradeoffs, and findings

## How To Use This Repo

1. Open the relevant session or config in `cubiomes-viewer`.
2. Review the accompanying notes, exports, or analysis files.
3. Run or refine the search.
4. Save updated sessions/configs back into the repo so the work stays reproducible.

For larger searches, prefer creating a dedicated folder under `searches/` rather than dropping exports at repo root.

## Non-Goals

At least for now, this repo is not trying to be:

- A general-purpose Minecraft tooling project
- A polished CLI or web app
- A complete archive of every seed worth keeping

## Notes

If you add new searches, use directory and file names that describe the search target or stage clearly.

CSV files under `searches/<search-name>/data/` are tracked with Git LFS via [`.gitattributes`](/home/qoc_user/source/personal/seed-sifter/.gitattributes). Run `git lfs install` once on a machine before cloning or committing LFS-backed data.
