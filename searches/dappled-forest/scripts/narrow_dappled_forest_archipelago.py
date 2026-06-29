#!/usr/bin/env python3
"""Archipelago variant of the snowy Dappled Forest proxy session.

Third link in the chain. It takes the snowy coastal-survival session and adds a
spawn-relative archipelago shape: open water and habitable land must coexist
around the base, with neither drowning nor dominating it. The intent is the
"home base among islands" half of the goal -- the existing Central-sea gate and
the biome-presence / Dappled / snowy gates are the "expeditions outward" half.

    viewer-search.session                  (hand-maintained starter)
      -> update_starter_session.py         -> regenerates the starter
      -> narrow_dappled_forest.py          -> dappled-forest.session
      -> narrow_dappled_forest_snowy.py    -> dappled-forest-snowy.session
      -> THIS script                       -> dappled-forest-archipelago.session

Like the snowy script, this derives everything in memory (via build_snowy_lines)
and writes only its own session. It never rewrites the base or snowy sessions,
so run results are never clobbered, and starter / Dappled / snowy changes all
flow through on each run.

What the cubiomes-viewer source allows (verified against search.cpp at the
pinned submodule commit e61f905):

  - F_BIOME_CENTER counts clusters of a *single* biome id (no biome mask) with a
    *minimum* size only. So it cannot count "landmasses in general" nor cap a
    continent's size -- the natural "count the islands" filter is not expressible.
  - F_BIOME_SAMPLE measures the *minimum* coverage fraction of a biome *set* with
    a confidence. Two complementary minimums (sea AND land) bound the sea share
    from both sides -- this is the workhorse here.
  - F_CLIMATE_NOISE checks, per parameter independently and cheaply, that the
    area's value range overlaps a required band. Two such gates on continentalness
    over one tight window force open water AND solid land to both occur there --
    i.e. a coastline runs through the base. This is the cheap prefilter.

None of these count islands. Balanced coverage at a small window is a *proxy* for
fragmentation: it reliably rejects "one continent" and "drowned world", and at a
1536-block window a balanced split is almost always threaded terrain rather than
one clean diagonal coast -- but it cannot prove a specific island count.

Run: python3 searches/dappled-forest/scripts/narrow_dappled_forest_archipelago.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STARTER_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(STARTER_SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narrow_dappled_forest_snowy import build_snowy_lines  # noqa: E402

from update_starter_session import (  # noqa: E402
    build_climate_template,
    build_biome_sample_template,
    set_biome_mask,
    decode_condition,
    encode_condition,
    INT_MIN,
    INT_MAX,
    NP_CONTINENTALNESS,
)

ARCHIPELAGO_SESSION = (
    Path(__file__).resolve().parents[1] / "sessions" / "dappled-forest-archipelago.session"
)

# Save slots. Unique within the session; the starter spans 1..16 and the snowy
# gate uses 17, so the archipelago gates take 18..25.
SAVE_COAST_WATER = 18
SAVE_COAST_LAND = 19
SAVE_SEA_COVERAGE = 20
SAVE_LAND_COVERAGE = 21
SAVE_MOAT_E = 22
SAVE_MOAT_W = 23
SAVE_MOAT_N = 24
SAVE_MOAT_S = 25

# Spawn-relative, matching the starter's Coastal / Warm sea / Open terrain gates,
# which reference the spawn anchor in save slot 2.
SPAWN_RELATIVE = 2

# Continentalness band edges (cubiomes scaled integers), reusing the same edges
# the starter already relies on: -1900 is the ocean/coast boundary (Warm sea uses
# it) and 300 is the near_inland/mid_inland boundary (Cherry/Pale use it). The
# -1900..300 gap between them is the transition band, so requiring water below
# -1900 and land above 300 forces a genuine shore rather than a marshy waterline.
CONT_OCEAN = -1900
CONT_INLAND = 300

# Window half-widths (blocks), offsets from spawn.
COAST_HALF = 512   # tight: a coast must run within ~0.5 km of the base
BALANCE_HALF = 768  # wider: the land/sea balance is measured over ~1.5 km

# Spawn-moat arms: ocean must occur in each cardinal direction near spawn, so the
# spawn landmass is bounded by water all around -- i.e. spawn is on an island, not
# on a continent that runs off in some direction. Each arm is a rectangular strip
# from MOAT_INNER..MOAT_OUTER out, MOAT_HALF wide. It uses limok (ocean *exists*
# in the strip), not limex (the strip is *entirely* ocean): this is "spawn on its
# own island within the archipelago" and tolerates neighbouring islets in the
# moat, rather than "lone island in empty sea" which would fight the island field.
#
# Limits worth remembering: four cardinal rectangles leave the diagonals
# uncovered, so a landmass joined to a continent by a diagonal isthmus can still
# pass. And there is no connected-component test (F_BIOME_CENTER clusters a single
# biome with a minimum size only), so this bounds the spawn land geometrically
# rather than proving it is one piece.
MOAT_INNER = 256   # arm starts this far out (past the spawn island)
MOAT_OUTER = 640   # ... and reaches this far
MOAT_HALF = 384    # perpendicular half-width (wide -> better corner overlap)
MOAT_OCEAN = -1100  # continentalness at/below the waterline counts as water;
# lower toward -1900 to demand genuine open ocean (not just shore) each direction.

# Coverage thresholds (fraction) and Monte-Carlo confidence.
#
# SEA_COVERAGE 0.47 : at least 47% open water -> not a continent.
# LAND_COVERAGE 0.31: at least 31% of the curated habitable-land set -> not
#                     drowned, and specifically pleasant base terrain. Note the
#                     land set below is a *curated subset* of all land (no snowy,
#                     desert, badlands, jungle, dark forest, swamp), so this floor
#                     is markedly stricter than the same fraction of land in
#                     general. The snowy region the snowy gate requires is *not*
#                     in this set (except grove), so it lives in the uncounted
#                     remainder by design -- snowy is the expedition target, the
#                     curated islands are the base. At 0.47 + 0.31 the two floors
#                     claim 78% of the window, leaving ~22% for shore, snowy land,
#                     and everything else -- a tight filter. SEA and LAND are the
#                     first two dials to relax if hits are too sparse.
SEA_COVERAGE = 0.47
LAND_COVERAGE = 0.31
COVERAGE_CONFIDENCE = 0.90

# Open-water set (the island separator): the full ocean family including frozen
# variants, since this is the snowy line. Verified ids (cubiomes biomes.h,
# commit e61f905).
WATER_BIOMES = [
    0,   # ocean
    10,  # frozen_ocean
    24,  # deep_ocean
    44,  # warm_ocean
    45,  # lukewarm_ocean
    46,  # cold_ocean
    48,  # deep_lukewarm_ocean
    49,  # deep_cold_ocean
    50,  # deep_frozen_ocean
]

# Curated habitable-land set for the base. Exactly the biomes requested: pleasant,
# buildable, resource-rich temperate-to-cold terrain. Verified ids (biomes.h,
# commit e61f905); old_growth_spruce_taiga is 160 (giant_tree_taiga+128), not 32.
LAND_BIOMES = [
    1,    # plains
    129,  # sunflower_plains
    35,   # savanna
    32,   # old_growth_pine_taiga (giant_tree_taiga)
    160,  # old_growth_spruce_taiga (giant_spruce_taiga)
    168,  # bamboo_jungle
    4,    # forest
    5,    # taiga
    23,   # sparse_jungle (jungle_edge)
    27,   # birch_forest
    155,  # old_growth_birch_forest (tall_birch_forest)
    132,  # flower_forest
    178,  # grove
]


def build_coast_span(base, label, save, cont_lo, cont_hi):
    condition = build_climate_template(
        base=base,
        label=label,
        save=save,
        relative=SPAWN_RELATIVE,
    )
    condition.x1 = -COAST_HALF
    condition.z1 = -COAST_HALF
    condition.x2 = COAST_HALF
    condition.z2 = COAST_HALF
    condition.limok[NP_CONTINENTALNESS][0] = cont_lo
    condition.limok[NP_CONTINENTALNESS][1] = cont_hi
    return condition


def build_spawn_moat(base, label, save, x1, z1, x2, z2):
    condition = build_climate_template(
        base=base,
        label=label,
        save=save,
        relative=SPAWN_RELATIVE,
    )
    condition.x1 = x1
    condition.z1 = z1
    condition.x2 = x2
    condition.z2 = z2
    # limok = "ocean exists somewhere in this strip" (the strip's continentalness
    # range must reach at/below the waterline).
    condition.limok[NP_CONTINENTALNESS][0] = INT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = MOAT_OCEAN
    return condition


def build_balance_coverage(base, label, save, biome_ids, coverage):
    condition = build_biome_sample_template(
        base=base,
        label=label,
        save=save,
        relative=SPAWN_RELATIVE,
    )
    condition.x1 = -BALANCE_HALF
    condition.z1 = -BALANCE_HALF
    condition.x2 = BALANCE_HALF
    condition.z2 = BALANCE_HALF
    set_biome_mask(condition, biome_ids)
    condition.converage = coverage
    condition.confidence = COVERAGE_CONFIDENCE
    condition.count = 0
    return condition


def build_archipelago_conditions(base):
    return [
        # Cheap climate prefilters (fast pass): a shore at the base.
        build_coast_span(base, "Coast: water", SAVE_COAST_WATER, INT_MIN, CONT_OCEAN),
        build_coast_span(base, "Coast: land", SAVE_COAST_LAND, CONT_INLAND, INT_MAX),
        # Cheap climate gates (fast pass): water in every cardinal direction, so
        # spawn sits on an island within the field rather than on a continent.
        build_spawn_moat(base, "Spawn moat E", SAVE_MOAT_E, MOAT_INNER, -MOAT_HALF, MOAT_OUTER, MOAT_HALF),
        build_spawn_moat(base, "Spawn moat W", SAVE_MOAT_W, -MOAT_OUTER, -MOAT_HALF, -MOAT_INNER, MOAT_HALF),
        build_spawn_moat(base, "Spawn moat N", SAVE_MOAT_N, -MOAT_HALF, -MOAT_OUTER, MOAT_HALF, -MOAT_INNER),
        build_spawn_moat(base, "Spawn moat S", SAVE_MOAT_S, -MOAT_HALF, MOAT_INNER, MOAT_HALF, MOAT_OUTER),
        # Expensive coverage gates (full pass): a balanced, fragmented mix.
        build_balance_coverage(base, "Archipelago: sea", SAVE_SEA_COVERAGE, WATER_BIOMES, SEA_COVERAGE),
        build_balance_coverage(base, "Archipelago: land", SAVE_LAND_COVERAGE, LAND_BIOMES, LAND_COVERAGE),
    ]


def main() -> None:
    lines = build_snowy_lines()

    cond_indexes = [idx for idx, line in enumerate(lines) if line.startswith("#Cond:")]
    if not cond_indexes:
        raise ValueError("no conditions found in snowy session")

    # Seed the new conditions from the first (oceanic) condition, as the starter
    # does for every builder.
    base = decode_condition(lines[cond_indexes[0]])
    conditions = build_archipelago_conditions(base)

    # Append after the last existing condition. The new gates are spawn-relative,
    # so they belong with the spawn-anchored group at the tail; appending keeps
    # the cheap climate gates ahead of the expensive coverage scans in file order.
    insert_at = cond_indexes[-1] + 1
    for offset, condition in enumerate(conditions):
        lines.insert(insert_at + offset, encode_condition(condition))

    ARCHIPELAGO_SESSION.parent.mkdir(parents=True, exist_ok=True)
    ARCHIPELAGO_SESSION.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
