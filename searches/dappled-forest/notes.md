# Dappled Forest search

A focused session for narrowing in on **Dappled Forest**, a biome added in
Minecraft **26.3 Snapshot 1** (June 2026): a cold, very dry, high-weirdness
forest with poplar trees, orange-brown grass, and red shrubs.

## What this search actually is (read this first)

This is a **climate-box proxy**, not a true Dappled Forest finder:

- cubiomes / cubiomes-viewer (4.1.2, 1.21 Winter Drop) have **no `dappled_forest`
  biome id** and **no verified parameter row**. We cannot add a biome-presence
  check the way the starter does for Cherry Grove / Pale Garden, and the viewer
  cannot resolve the biome.
- So this session filters the **raw 6D noise** for the biome's described
  signature — cold, very little humidity, high weirdness — and finds locations
  where that climate occurs. In a 1.21 world those columns resolve to whatever
  biome currently wins there (grove, cherry grove, old-growth taiga, etc.).
- It is **forward-looking** and assumes the noise field is stable between 1.21
  and 26.3. That has held when past biomes were carved out of existing parameter
  space, but it is not guaranteed. Treat results as candidate regions, not
  confirmed Dappled Forest.

## Climate box (cubiomes scaled integers, game value * 10000)

Derived from the starter's `Dappled Forest climate` estimate, tightened only on
the two traits the biome is actually described by:

| Parameter       | Range            | Source                                            |
| :-------------- | :--------------- | :------------------------------------------------ |
| temperature     | `-4500 .. -1500` | "cold" → level 1; floor excludes frozen/snowy      |
| humidity        | `.. -3500`       | "very little humidity" → driest level 0            |
| continentalness | `-1899 ..`       | unchanged from starter (inland); not described     |
| erosion         | `500 ..`         | flat/plains terrain (level 3/4 band edge; see theory below); orthogonal to weirdness |
| weirdness       | `3333 ..`        | variant lever; eased back from 3667 now erosion shares the load |

## Working theory: plains replacement

A community theory holds that Dappled Forest replaces **plains that border
cold/snowy biomes**. That corner of climate space — cold, dry, inland — already
matches the box. Its new contribution is **erosion**: plains are flat, and flat
terrain is high erosion (low erosion = jagged/shattered). So an `erosion >= 1500`
floor biases toward flat, plains-like ground, and it is *orthogonal* to
weirdness — a second independent lever once cranking weirdness alone hit
diminishing returns. Unlike weirdness, erosion has 7 defined bands (like
temperature/humidity), so the floor is set to a real band edge: `500` is the
level 3/4 boundary, dropping the jagged levels 0-3 and keeping the flatter levels
4-6. The next stricter edge up is `4500` (level 5+), if 500 proves too noisy.

This is a hypothesis layered on a proxy for an undocumented biome. If Dappled
Forest turns out to generate on varied terrain, the erosion floor costs recall.
A/B it: same seeds with and without the floor, compare precision.

## Dials (if results are too sparse or too noisy)

- **Too few hits:** widen temperature back toward level 2 (`-1500` → up to
  `2000`), or relax humidity (`-3500` → `-1000`). Temperature is the most
  aggressive cut here.
- **Too noisy:** push weirdness higher (currently `3333`) or raise the erosion
  floor (currently `500`) to the next band edge `4500` (level 5+, flatter).
  Weirdness has no fixed level
  bands to snap to above 0 (unlike temperature and humidity): 0 is the only hard
  line (base biome vs. "weirder" variant), and the per-biome sub-ranges aren't
  published for Dappled Forest. So tune the floor empirically against hit rate --
  round numbers like 4000 carry no special meaning here.
- All values are named constants at the top of
  `scripts/narrow_dappled_forest.py`.

## Regenerate

```
python3 searches/dappled-forest/scripts/narrow_dappled_forest.py
```

Re-reads the current starter session and re-applies the narrowing, so starter
changes (new conditions, area tweaks) carry through automatically. Revisit the
parameters once cubiomes adds a real `dappled_forest` row — at that point a
biome-presence check should replace this proxy.
