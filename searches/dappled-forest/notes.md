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
| erosion         | `1000 ..`        | flat/plains terrain (mid level 4; see theory below); orthogonal to weirdness |
| weirdness       | `3333 ..`        | variant lever; eased back from 3667 now erosion shares the load |

## Working theory: plains replacement

A community theory holds that Dappled Forest replaces **plains that border
cold/snowy biomes**. That corner of climate space — cold, dry, inland — already
matches the box. Its new contribution is **erosion**: plains are flat, and flat
terrain is high erosion (low erosion = jagged/shattered). So an erosion floor
biases toward flat, plains-like ground, and it is *orthogonal* to weirdness — a
second independent lever once cranking weirdness alone hit diminishing returns.

Erosion has 7 defined bands (like temperature/humidity, unlike weirdness). The
floor started at the principled band edge `500` (level 3/4, which drops the
jagged levels 0-3), then was nudged up to `1000` for a stronger flat bias.
`1000` is mid-level-4, so it carries no biome-assignment significance — but
terrain ruggedness responds to raw erosion continuously, so a higher floor still
selects flatter ground. The next actual band edge up is `4500` (level 5+), a
large jump that drops all of level 4.

This is a hypothesis layered on a proxy for an undocumented biome. If Dappled
Forest turns out to generate on varied terrain, the erosion floor costs recall.
A/B it: same seeds with and without the floor, compare precision.

## Dials (if results are too sparse or too noisy)

- **Too few hits:** widen temperature back toward level 2 (`-1500` → up to
  `2000`), or relax humidity (`-3500` → `-1000`). Temperature is the most
  aggressive cut here.
- **Too noisy:** push weirdness higher (currently `3333`) or raise the erosion
  floor (currently `1000`; next actual band edge is `4500`, level 5+, flatter).
  Weirdness has no fixed level
  bands to snap to above 0 (unlike temperature and humidity): 0 is the only hard
  line (base biome vs. "weirder" variant), and the per-biome sub-ranges aren't
  published for Dappled Forest. So tune the floor empirically against hit rate --
  round numbers like 4000 carry no special meaning here.
- All values are named constants at the top of
  `scripts/narrow_dappled_forest.py`.

## Variant: snowy-adjacent coastal survival (`dappled-forest-snowy.session`)

A second version aimed at a **varied coastal-survival seed** — archipelago
geography, strong biome transitions, "home base plus expeditions." It is the base
Dappled Forest proxy **plus one extra root climate gate** requiring a genuinely
snowy region in the central map.

| Parameter       | Range       | Source                                                |
| :-------------- | :---------- | :---------------------------------------------------- |
| temperature     | `.. -4500`  | snowy = temperature level 0; the band directly *below* the Dappled Forest floor |
| continentalness | `-1100 ..`  | coast-or-inland, so it wants snowy *land* not frozen open ocean |

Why snowy: the Dappled Forest box floors temperature at `-4500` to *exclude*
frozen/snowy land (it is a grassy level-1 forest). Snowy biomes sit just below
that edge. Requiring both in the same `-1792..1792` area forces the two adjacent
bands to coexist — cold grassy forest abutting frozen terrain — which is the
strong-transition adjacency the survival goal is built around. The Central-sea
coverage gate (already in the base) supplies the warm-leaning seas around it, so
the combination reads as snowy islands in a navigable archipelago.

The continentalness floor is the **first dial to relax** if hits are too sparse
(`-1100` → `INT_MIN` lets frozen ocean satisfy it). It is *orthogonal* to all the
Dappled Forest dials — this variant inherits whatever the base box currently is.

## Regenerate

Base Dappled Forest proxy:

```
python3 searches/dappled-forest/scripts/narrow_dappled_forest.py
```

Re-reads the current starter session and re-applies the narrowing, so starter
changes (new conditions, area tweaks) carry through automatically.

Snowy coastal variant — derives the base narrowing in memory from the same
starter and adds the snowy gate, so it never rewrites `dappled-forest.session`
(that file accumulates run results):

```
python3 searches/dappled-forest/scripts/narrow_dappled_forest_snowy.py
```

Revisit the parameters once cubiomes adds a real `dappled_forest` row — at that
point a biome-presence check should replace this proxy.
