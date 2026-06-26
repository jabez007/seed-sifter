# seed-sifter

`seed-sifter` is a small workspace for reproducible `cubiomes-viewer` seed
searches.

It is not a standalone application, library, or automated seed-finding
pipeline. The repo currently focuses on one reusable starter session, one
script that regenerates that session, and supporting notes about Minecraft
worldgen and Cubiomes search strategy.

## Purpose

- Keep reusable `cubiomes-viewer` sessions under version control
- Record search criteria and rationale alongside the saved sessions
- Leave room for future search exports, analysis inputs, and shortlists

## Current Contents

- [`docs/`](./docs/) - supporting notes and background analysis
- [`docs/Cubiomes Multi-Noise System Analysis.md`](./docs/Cubiomes%20Multi-Noise%20System%20Analysis.md) - reference notes on Cubiomes and Minecraft's multi-noise biome system
- [`searches/viewer-search.session`](./searches/viewer-search.session) - starter `cubiomes-viewer` session with reusable default filters
- [`searches/scripts/update_starter_session.py`](./searches/scripts/update_starter_session.py) - regenerates the starter session from a hard-coded condition set

## Intended Search Layout

When a search grows beyond the shared starter session, create a dedicated folder
under `searches/`:

- `searches/<search-name>/sessions/` - saved `cubiomes-viewer` session files
- `searches/<search-name>/data/raw/` - broad raw exports
- `searches/<search-name>/data/refined/` - narrowed follow-up exports
- `searches/<search-name>/data/analysis-inputs/` - files prepared for ranking or notebook work
- `searches/<search-name>/analysis/` - notebooks or ad hoc analysis artifacts
- `searches/<search-name>/results/` - shortlists or final candidate seeds
- `searches/<search-name>/notes.md` or `docs/` - search-specific writeups and decisions

## Workflow

1. Open [`searches/viewer-search.session`](./searches/viewer-search.session) in `cubiomes-viewer`.
2. Review the notes in [`docs/`](./docs/) if you need the reasoning behind the filters.
3. Run or refine the search in the viewer.
4. If you change the shared starter condition set, update the generator script and regenerate the session with `python3 searches/scripts/update_starter_session.py`.
5. For search-specific work, create a dedicated folder under `searches/` and keep the outputs there.

## Starter Session

The starter session is meant to be a reusable baseline for water-heavy seeds
with broad biome-climate variety around spawn and in the surrounding region.

In plain English, it is trying to find worlds with these traits:

- A central map that is more sea than land
- A spawn area that is coastal and biased toward warmer nearby water
- Enough flatter terrain near spawn to make early movement and building easier
- A central surrounding region that still includes several distinct climate families and some Pale Garden-leaning continental/weirdness pockets
- At least one mushroom island in the central search area

The session is still a heuristic filter stack, not a guarantee of exact biome
layouts. Most of the climate checks mean "this kind of terrain exists
somewhere in the search area," not "the whole area looks like this."

### Condition Map

| Goal                   | Conditions                                                                                                                     | What they are trying to enforce                                                                                                                                                                      |
| :--------------------- | :----------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ocean-dominant world   | `Oceanic climate`, `Central sea coverage`, `Mushroom island`                                                                   | Keep the central region strongly water-heavy rather than mostly continental, and require one meaningful mushroom island within that same broad ocean search area.                                    |
| Coastal spawn          | `Spawn anchor`, `Coastal`, `Warm sea`, `Open terrain`                                                                          | Bias spawn toward coast or open water, with warmer nearby sea and a somewhat easier local terrain patch.                                                                                             |
| Regional biome variety | `Hot/wet climate`, `Hot/dry climate`, `Taiga climate`, `Cherry Grove climate`, `Pale Garden climate`, `Dappled Forest climate`, `Cherry Grove present`, `Pale Garden present` | Improve odds that the central search region includes multiple climate families and some Cherry Grove / Pale Garden / Dappled Forest-style terrain pockets without tying those checks to exact spawn. For Cherry Grove and Pale Garden the climate box is only a fast prefilter; a paired biome-presence check then confirms the biome actually generates, since a climate box is a superset of the region that resolves to the biome. The two presence checks are the heaviest conditions, so they run last, after every climate gate and the other biome scans. |

### Exact Condition Summary

| Condition                | Search area                        | Requirement                                                                                                                   |
| :----------------------- | :--------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| `Oceanic climate`        | Global X/Z `-2048` to `2048`       | `continentalness <= -4550`                                                                                                    |
| `Hot/wet climate`        | Global X/Z `-1792` to `1792`       | `1000 <= temperature <= 5500`, `humidity >= 1000`, `continentalness >= -1100`, `erosion >= 5500`                              |
| `Hot/dry climate`        | Global X/Z `-1792` to `1792`       | `temperature >= 2000`, `humidity <= -1000`, `erosion <= 500`                                                                  |
| `Taiga climate`          | Global X/Z `-1792` to `1792`       | `-4499 <= temperature <= -1500`, `humidity >= 1000`, `continentalness >= -1900`                                               |
| `Cherry Grove climate`   | Global X/Z `-1792` to `1792`       | `-4500 <= temperature <= 2000`, `humidity <= -1000`, `continentalness >= 300`, `-7799 <= erosion <= 500`, `weirdness >= 2666` |
| `Pale Garden climate`    | Global X/Z `-1792` to `1792`       | `-1500 <= temperature <= 2000`, `humidity >= 3000`, `continentalness >= 300`, `-7799 <= erosion <= 500`, `weirdness >= 2666`  |
| `Dappled Forest climate` | Global X/Z `-1792` to `1792`       | `-4500 <= temperature <= 2000`, `humidity <= -1000`, `continentalness >= -1899`, `weirdness >= 2666`                          |
| `Central sea coverage`   | Central X/Z `-1536` to `1536`      | At least `53%` ocean-family biome coverage at `95%` confidence                                                                |
| `Mushroom island`        | Central X/Z `-1536` to `1536`      | At least one `mushroom_fields` island, minimum size `256`, border tolerance `2`                                               |
| `Cherry Grove present`   | Global X/Z `-1792` to `1792`       | At least one `cherry_grove` (id `185`) island, minimum size `384` (~78x78 blocks), border tolerance `2`                       |
| `Pale Garden present`    | Global X/Z `-1792` to `1792`       | At least one `pale_garden` (id `186`) island, minimum size `128` (~45x45 blocks), border tolerance `2`                        |
| `Spawn anchor`           | X/Z `-1024` to `1024`              | Establishes the spawn-relative reference point for the local spawn checks only                                                |
| `Coastal`                | Spawn-relative X/Z `-128` to `128` | `continentalness <= -1100`                                                                                                    |
| `Warm sea`               | Spawn-relative X/Z `-192` to `192` | `temperature >= 2001`, `continentalness <= -1900`                                                                             |
| `Open terrain`           | Spawn-relative X/Z `-64` to `64`   | `erosion >= 1500`, `-2000 <= weirdness <= 2000`                                                                               |

### Target Biome Reference

These are the cubiomes biome-parameter ranges for the main biomes the starter
session is trying to bias toward. `Any` means cubiomes does not constrain that
parameter for the biome. `Dappled Forest` is an estimate based on current
snapshot descriptions, not a verified cubiomes row.

| Biome                          | Temperature    | Humidity     | Continentalness | Erosion      | Weirdness | Why it matters                                                                                                                               |
| :----------------------------- | :------------- | :----------- | :-------------- | :----------- | :-------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| `swamp`                        | `-4500..2000`  | `Any`        | `>= -1100`      | `>= 5500`    | `Any`     | Helps explain why the hot/wet filter uses very high erosion and modest inlandness.                                                           |
| `mangrove_swamp`               | `>= 2000`      | `Any`        | `>= -1100`      | `>= 5500`    | `Any`     | Shares the same strong erosion signal as swamp, but in a hotter band.                                                                        |
| `sparse_jungle`                | `2000..5500`   | `1000..3000` | `>= -1899`      | `Any`        | `>= -500` | A useful jungle-side target that still fits the hot/wet filter without demanding full jungle space.                                          |
| `bamboo_jungle`                | `2000..5500`   | `>= 3000`    | `>= -1899`      | `Any`        | `>= -500` | Pushes the hot/wet filter toward hotter, wetter jungle-family terrain.                                                                       |
| `taiga`                        | `<= -1500`     | `>= 1000`    | `>= -1900`      | `Any`        | `Any`     | The base taiga target: cool, moist, and broadly inland.                                                                                      |
| `old_growth_pine_taiga`        | `-4500..-1500` | `>= 3000`    | `>= -1899`      | `Any`        | `>= -500` | One half of the old-growth split; shares the taiga temperature band but wants much higher humidity.                                          |
| `old_growth_spruce_taiga`      | `-4500..-1500` | `>= 3000`    | `>= -1900`      | `Any`        | `<= -500` | The other old-growth half; same cool/wet band as pine, but on the opposite weirdness side.                                                   |
| `savanna`                      | `2000..5500`   | `<= -1000`   | `>= -1900`      | `Any`        | `Any`     | One of the main reasons the hot/dry filter starts at higher temperature and drier humidity.                                                  |
| `savanna_plateau`              | `2000..5500`   | `<= -1000`   | `>= -1100`      | `<= 500`     | `Any`     | Contributes the low-erosion signal that keeps hot/dry closer to savanna/badlands terrain.                                                    |
| `badlands`                     | `>= 5500`      | `<= 1000`    | `>= -1899`      | `<= 500`     | `Any`     | Shares the low-erosion requirement with plateaus and helps justify the badlands lean in hot/dry.                                             |
| `eroded_badlands`              | `>= 5500`      | `<= -1000`   | `>= -1899`      | `<= 500`     | `>= -500` | A stricter hot/dry endpoint that reinforces the low-erosion and drier-humidity bias.                                                         |
| `cherry_grove`                 | `-4500..2000`  | `<= -1000`   | `>= 300`        | `-7799..500` | `>= 2666` | Relevant because it shares the same inland, low-erosion, high-weirdness shape as Pale Garden, but in a colder/drier climate band.            |
| `pale_garden`                  | `-1500..2000`  | `>= 3000`    | `>= 300`        | `-7799..500` | `>= 2666` | This now matches the full cubiomes Pale Garden climate box, which keeps it more distinct from Cherry Grove.                                  |
| `dappled_forest` _(estimated)_ | `-4500..2000`  | `<= -1000`   | `>= -1899`      | `Any`        | `>= 2666` | Estimated from current descriptions: cold, very dry, high-weirdness land that can still appear across varied terrain and near colder coasts. |

Current direction:

- Prefer climate-parameter gates for coarse reusable filtering
- Keep explicit biome checks only where they capture a real requirement better than climate noise alone
- Cherry Grove and Pale Garden now follow a hybrid pattern: the climate gate is a fast prefilter and a paired biome-presence check confirms the biome actually generates. Climate boxes are the nominal cubiomes parameter rows, which are a superset of the region that resolves to the biome (assignment is a nearest-neighbor vote in 6D space), so a box alone admits seeds where every column resolves to a neighbor. The biome check only runs on seeds that already clear the cheap gate.

## Non-Goals

This repo is not trying to be:

- A general-purpose Minecraft tooling project
- A polished CLI or web app
- A complete archive of every seed worth keeping

## Notes

Use descriptive names for search folders and artifacts so runs are still legible
later.

CSV files under `searches/<search-name>/data/` are tracked with Git LFS via
[`.gitattributes`](./.gitattributes). Run `git lfs install` once on a machine
before cloning or committing LFS-backed data.
