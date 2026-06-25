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
- [`searches/viewer-search.session`](./searches/viewer-search.session) - starter `cubiomes-viewer` session for reusable default conditions
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

## Starter Session

The starter session is [`searches/viewer-search.session`](./searches/viewer-search.session). It is meant to hold reusable default conditions.

The starter stack starts with one global climate gate, then a spawn-relative climate stack, and ends with a larger global sea-coverage sample.

- `Waterworld climate`
  Global coarse gate over X/Z `-2048` to `2048`.
  Non-default limit: `continentalness <= -4550`
- `Spawn anchor`
  `Spawn` condition over X/Z `-1024` to `1024`.
  Every condition listed through `Relief diversity` is relative to this anchor.

Spawn-relative local gates:

- `Coastal`
  Window: X/Z `-128` to `128` around the spawn anchor
  `continentalness <= -1100`
- `Warm sea`
  Window: X/Z `-256` to `256` around the spawn anchor
  Keeps the spawn-adjacent water biased warmer even though the larger central sea gate now accepts cold variants.
  `temperature >= 1000`
  `continentalness <= -1800`
- `Open terrain`
  Window: X/Z `-64` to `64` around the spawn anchor
  `erosion >= 1500`
  `-2000 <= weirdness <= 2000`

Spawn-relative regional gates:

- `Hot/wet climate`
  Window: X/Z `-1536` to `1536` around the spawn anchor
  `temperature >= 1000`
  `humidity >= 1000`
  `erosion >= 1000`
- `Hot/dry climate`
  Window: X/Z `-1536` to `1536` around the spawn anchor
  `temperature >= 1000`
  `-2500 <= humidity <= -500`
- `Taiga climate`
  Window: X/Z `-1536` to `1536` around the spawn anchor
  `-2000 <= temperature <= 250`
  `0 <= humidity <= 2000`
- `Relief diversity`
  Window: X/Z `-1536` to `1536` around the spawn anchor
  `continentalness >= -500`
  `erosion <= -500`

Global coverage gate:

- `Central sea coverage`
  Global sample over X/Z `-1536` to `1536`
  Allowed sampled biomes: `ocean`, `deep_ocean`, `cold_ocean`, `warm_ocean`, `lukewarm_ocean`, `deep_cold_ocean`, `deep_lukewarm_ocean`
  Minimum sampled coverage: `53%`
  Confidence: `95%`
  Kept after the climate conditions so the cheaper climate filters can reject seeds first.
- `Mushroom island`
  Global `Locate biome center` search over X/Z `-1536` to `1536`
  Target biome: `mushroom_fields`
  Required instances: `1`
  Minimum biome size: `256` (about `16` square chunks in the viewer's size estimate)
  Border tolerance: `2` to allow slight edge irregularity without turning this into a loose shape match

Current direction:

- Prefer `Climate parameters` for most coarse reusable starter conditions.
- Keep a small number of explicit biome sample checks when they express a real requirement more directly than climate noise alone.

## Non-Goals

At least for now, this repo is not trying to be:

- A general-purpose Minecraft tooling project
- A polished CLI or web app
- A complete archive of every seed worth keeping

## Notes

If you add new searches, use directory and file names that describe the search target or stage clearly.

CSV files under `searches/<search-name>/data/` are tracked with Git LFS via [`.gitattributes`](/home/qoc_user/source/personal/seed-sifter/.gitattributes). Run `git lfs install` once on a machine before cloning or committing LFS-backed data.
