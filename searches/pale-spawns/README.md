# Pale Spawns

This folder contains the `pale-spawns` search artifacts.

The saved session file records a `cubiomes-viewer` search for Minecraft `1.21 WD`.

Per `cubiomes-viewer` source, these named conditions are `Biome samples` filters: they sample biomes in an area and require a minimum proportion of sampled cells to match an allowed biome set.

In this session, the named conditions decode as:

- `Waterworld` - at least `53%` of sampled cells must be one of:
  `ocean`, `river`, `deep_ocean`, `warm_ocean`, `lukewarm_ocean`, or `deep_lukewarm_ocean`
- `Open terrain` - at least `47%` of sampled cells must be one of these cubiomes biome IDs:
  `plains`, `mountains`, `jungle_hills`, `savanna`, `savanna_plateau`, `sunflower_plains`, `flower_forest`, `shattered_savanna`, `meadow`, or `grove`
- `11% Ocean` - at least `11%` of sampled cells must be one of:
  `ocean`, `deep_ocean`, `warm_ocean`, `lukewarm_ocean`, or `deep_lukewarm_ocean`
- `3% Pale Garden` - at least `3%` of sampled cells must be `pale_garden`
- `2% River or Ocean` - at least `2%` of sampled cells must be one of:
  `ocean`, `river`, `deep_ocean`, `warm_ocean`, `lukewarm_ocean`, or `deep_lukewarm_ocean`

The paired biome exports show that this search was evaluated on a `1:4` biome scale:

- Broad window: X `-2692` to `2688`, Z `-2468` to `2464`
- Narrow window: X `-2384` to `2380`, Z `-2468` to `2464`

## Time Window

The files in this folder are timestamped between November 18, 2025 and November 24, 2025.

## Layout

- [`sessions/viewer-search.session`](./sessions/viewer-search.session) - saved `cubiomes-viewer` session with the original search conditions
- [`data/raw/structures-broad-window.csv`](./data/raw/structures-broad-window.csv) - broad structure export, `5,647,303` rows across `1,038` seeds
- [`data/raw/biomes-broad-window.csv`](./data/raw/biomes-broad-window.csv) - broad biome summary export, `1,038` rows
- [`data/refined/biomes-narrow-window.csv`](./data/refined/biomes-narrow-window.csv) - narrowed biome summary export, `256` rows
- [`data/analysis-inputs/structures-parity-input.csv`](./data/analysis-inputs/structures-parity-input.csv) - standalone structure export used by the notebook ranking pass, `430,961` rows across `90` seeds
- [`analysis/parity-interest-report.ipynb`](./analysis/parity-interest-report.ipynb) - notebook that ranks candidate seeds using a parity-interest scoring heuristic
- [`scripts/regenerate_narrow_structures.py`](./scripts/regenerate_narrow_structures.py) - rebuilds the narrowed structure export on demand from the broad structure export plus the narrow biome seed set
- [`results/candidate-seeds-2025-11-21.txt`](./results/candidate-seeds-2025-11-21.txt) - shortlist of `14` candidate seeds saved on November 21, 2025

## Suggested Reading Order

1. Start with the saved session file.
2. Review the raw biome and structure exports.
3. Review the narrow biome export.
4. Open the notebook to inspect how `data/analysis-inputs/structures-parity-input.csv` was ranked.
5. Use the text file in `results/` as the saved shortlist.

## Relationships

- The historical narrowed structure export was an exact row subset of `structures-broad-window.csv`.
- `biomes-narrow-window.csv` and the regenerated narrowed structure export cover the same `256` seeds.
- `structures-parity-input.csv` overlaps with the broad and narrow structure exports, but it is not a subset of either one.
- Every seed in `candidate-seeds-2025-11-21.txt` is present in `structures-broad-window.csv`.
- Not every seed in `candidate-seeds-2025-11-21.txt` is present in the narrow-window or parity-input seed sets.

## Session Notes

- The session contains one additional unnamed condition record with zeroed trailing float values. This README does not assign semantics to that record.
- Each named condition above also carries a shared trailing float of `0.95` in the session payload. This README does not interpret that field.
- The biome names above come from cubiomes biome IDs. Some of those IDs use legacy names in source, even when modern Minecraft UI names differ.

## Consolidation Notes

- The narrowed structure export is no longer tracked because it is reproducible.
- Regeneration command:
  `python3 searches/pale-spawns/scripts/regenerate_narrow_structures.py`
- The script was verified against the removed historical file for row-for-row equality before consolidation.
- The CSV files in `data/` are covered by the repo's Git LFS rule.
