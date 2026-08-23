#!/usr/bin/env python3
"""Retuned Dappled Forest search: corrected criteria, cost-ordered conditions.

Fifth link in the chain. Same goal as the structures variant -- an archipelago
survival seed with a village and stronghold near likely Dappled Forest -- but
with four corrections, each backed by a measurement recorded in notes.md:

  1. The Dappled Forest box is rebuilt from the biome's own description rather
     than the plains-replacement theory. The erosion floor is gone.
  2. The condition list is ordered by measured cost/selectivity instead of by
     "climate is cheap, biomes are expensive", which is not true here.
  3. Four conditions that filter nothing are dropped. Two of them are provably
     redundant, not merely weak.
  4. "Open terrain" uses limex for the intent it states.

It is a separate link rather than an edit to narrow_dappled_forest_structures.py
so both remain reproducible: the structures sessions still regenerate byte for
byte with the criteria their committed run results were produced under.

Run: python3 searches/dappled-forest/scripts/narrow_dappled_forest_tuned.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STARTER_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(STARTER_SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narrow_dappled_forest_archipelago import build_archipelago_lines  # noqa: E402

from narrow_dappled_forest_structures import (  # noqa: E402
    build_structure_conditions,
    write_session,
    SAVE_DAPPLED_NEAR,
    SEARCH_BLOCKS,
    SEARCH_LIST,
    SESSIONS_DIR,
    DATA_DIR,
    FAVOURITE_SEEDS,
)

from update_starter_session import (  # noqa: E402
    build_biome_sample_template,
    set_biome_mask,
    decode_condition,
    encode_condition,
    INT_MIN,
    INT_MAX,
    NP_TEMPERATURE,
    NP_HUMIDITY,
    NP_CONTINENTALNESS,
    NP_EROSION,
    NP_WEIRDNESS,
)

REVIEW_SESSION = SESSIONS_DIR / "dappled-forest-tuned.session"
HUNT_SESSION = SESSIONS_DIR / "dappled-forest-tuned-hunt.session"
KNOWN_SEEDS = DATA_DIR / "known-seeds-tuned.txt"

# ---------------------------------------------------------------------------
# 1. Dappled Forest climate box, derived from the biome description
# ---------------------------------------------------------------------------
# "Dappled forests generate in cold regions of very little humidity and high
#  weirdness values. This makes them border plains, sunflower plains, ice spikes,
#  and cherry grove biomes, but never any other woodland biomes. They can
#  generate in any type of terrain, on flatland near windswept gravelly hills,
#  near cold oceans, or in mountains near frozen peaks."
#
# The neighbour list is the useful part: it pins the box far better than the
# adjectives do, because a biome's neighbours are the cells adjacent to it in
# parameter space.
#
#   temperature -4500..-1500 : ice_spikes is temperature level 0 (<= -4500),
#                              sunflower_plains is level 2 (-1500..2000).
#                              Bordering both puts Dappled Forest in level 1 --
#                              the band between them. This is now derived rather
#                              than guessed from the word "cold".
#   humidity        ..-3500  : sunflower_plains and ice_spikes both require
#                              humidity <= -3500, and every woodland biome
#                              (forest, birch, dark forest, taiga, grove) sits at
#                              humidity >= -1000. Level 0 is what makes "never any
#                              other woodland biomes" true, so this is the one
#                              bound that must NOT be relaxed -- the old note
#                              suggesting -1000 as a recall dial was wrong.
#   continentalness -1899..  : land. -1899 is the ocean/coast edge, so "near cold
#                              oceans" means sitting just inland of it.
#   erosion         ..5499   : the floor is GONE. "Any type of terrain" is
#                              explicit, and the named adjacencies span the whole
#                              erosion axis: windswept gravelly hills at 4500..5500
#                              and frozen peaks below -3750. The old floor of 1000
#                              was excluding the mountain half of the biome's own
#                              description. Measured: dropping it takes seeds with
#                              a co-located column from 32.0% to 61.8%.
#                              The cap sits just under 5500, the swamp edge --
#                              swamp is the only biome the box otherwise reaches
#                              that the description forbids. Costs 0.3% recall.
#   weirdness       2666..   : a real band edge, and the one cherry_grove uses.
#                              The old 3333 sat mid-band between 2666 and 4000, so
#                              it selected nothing 2666 does not; it only shrank
#                              the qualifying area. (The old note claiming
#                              weirdness has no bands above 0 was wrong: the edges
#                              are 500, 2666, 4000 and 9333.)
#
# Verification: sampled over 400 seeds, columns satisfying this box resolve to
# plains 80%, cherry_grove 13%, windswept_gravelly_hills 3%, snowy_slopes 2%,
# frozen_peaks 1% -- 96.8% of them are biomes the description names, and 0% are
# the woodland biomes it rules out. Since cubiomes has no dappled_forest id, its
# climate cells must currently resolve to whatever would border it, so matching
# the neighbour list is the strongest check available.
DAPPLED_TEMP = (-4500, -1500)
DAPPLED_HUMID = (INT_MIN, -3500)
DAPPLED_CONT = (-1899, INT_MAX)
DAPPLED_EROS = (INT_MIN, 5499)
DAPPLED_WEIRD = (2666, INT_MAX)

DAPPLED_LABELS = {"Dappled Forest climate", "Dappled near village"}

# ---------------------------------------------------------------------------
# 2. Conditions that filter nothing
# ---------------------------------------------------------------------------
# Measured over 400 random seeds. The two climate prefilters are redundant by
# construction, not just empirically: if a cherry grove generates anywhere in the
# +/-1792 box then that column's climate lies inside the cherry_grove parameter
# row, so every marginal range check in "Cherry Grove climate" -- the same row
# over the same box -- must pass. The presence check strictly implies its own
# prefilter. Same argument for Pale Garden. Dropping them cannot change which
# seeds match; it only stops paying ~39 ms/seed for the privilege.
DROP_LABELS = {
    "Oceanic climate",       # 100.0% pass, 14.4 ms -- most expensive no-op here
    "Cherry Grove climate",  #  99.5% pass, 19.8 ms -- implied by its presence check
    "Pale Garden climate",   #  98.5% pass, 19.6 ms -- implied by its presence check
    "Coast: land",           # 100.0% pass,  4.8 ms
    # Replaced by the biome-sample gates below -- see section 6.
    "Hot/wet climate",
    "Hot/dry climate",
    "Taiga climate",
}

# ---------------------------------------------------------------------------
# 3. Order, by measured cost / selectivity
# ---------------------------------------------------------------------------
# The assumption this search was built on -- climate gates are cheap, biome gates
# are expensive -- is false as configured. F_CLIMATE_NOISE calls getParaRange,
# a full min/max search over the whole box for every constrained parameter, and
# it pays the same price whether the seed passes or fails; continentalness alone
# costs 12 ms over a +/-1792 box. F_BIOME_SAMPLE runs a Monte-Carlo estimate that
# aborts as soon as a Wilson interval clears the threshold, so a failing seed --
# the common case -- costs almost nothing. Measured, per seed:
#
#   Central sea coverage (biome sample)   0.35 ms   passes  2.5%
#   Open terrain         (climate, +/-64) 0.18 ms   passes 30.5%
#   Archipelago: sea     (biome sample)   0.28 ms   passes 15.5%
#   Dappled Forest climate (+/-1792)     18.63 ms   passes 93.5%
#   Cherry Grove present (biome center)  59.12 ms   passes 62.5%
#   Mushroom island      (biome center)  81.97 ms   passes 20.0%
#
# The cheapest gate in the stack is a biome check, and it is also the most
# selective. It was running ninth. Root siblings are evaluated in file order, so
# ordering is purely a speed change -- the set of matching seeds is identical.
#
# Spawn-relative conditions are children of the spawn anchor and only run once it
# does, so the anchor is placed early to unlock the four cheap, selective gates
# hanging off it.
ROOT_ORDER = [
    "Central sea coverage",     # 0.35 ms,  2.5% -- by far the best value
    "Spawn anchor",             # 2.34 ms, unlocks the spawn-relative group
    "Swamp present",            # 2.80 ms, 54.0% -- the gate that actually gets swamps
    "Taiga biomes",             # 1.28 ms, 82.5%
    "Hot/dry biomes",           # 1.25 ms, 84.5%
    "Hot/wet biomes",           # 1.09 ms, 89.5%
    "Snowy biomes",             # 8.43 ms, 63.0%
    "Dappled Forest climate",   # 18.63 ms, 93.5% -- states the intent, filters little
    "Pale Garden present",      # 30.15 ms, 41.5%
    "Mushroom island",          # 81.97 ms, 20.0%
    "Village",                  # 41.76 ms, 49.5% for the whole group
    "Cherry Grove present",     # 59.12 ms, 62.5% -- worst ratio, so it runs last
]

SPAWN_ORDER = [
    "Open terrain",     # 0.20 ms, 18.5%
    "Archipelago: sea", # 0.28 ms, 15.5%
    "Archipelago: land",# 0.39 ms, 71.0%
    "Warm sea",         # 1.09 ms, 25.5%
    "Coastal",          # 1.75 ms, 64.0%
    "Spawn moat N",     # ~3.4 ms each, ~80% each
    "Spawn moat W",
    "Spawn moat S",
    "Spawn moat E",
    "Coast: water",     # 4.80 ms, 91.5%
]

VILLAGE_ORDER = ["Dappled near village", "Stronghold near village"]

# ---------------------------------------------------------------------------
# 4. "Open terrain" -- limex for the intent it states
# ---------------------------------------------------------------------------
# limok means "the area's range must OVERLAP this band" (an existence check);
# limex means "the area's range must be CONTAINED in it" (a universal one). The
# condition's stated intent is to *avoid* extreme weirdness near spawn, which is
# universal, but it was written with limok -- so it passed whenever weirdness
# touched the band anywhere in the box, which is essentially always.
#
# The band could not simply be moved to limex: weirdness spans a mean of 5664
# units over a 128x128 patch, so requiring containment in +/-2000 passes 0.5% of
# seeds and would have made the search return nothing. Measured containment
# rates: +/-2000 0.5%, +/-3000 7.2%, +/-4000 23.5%, +/-6000 61.8%.
#
# 4000 is tempting because it is a real weirdness band edge, but band edges matter
# for biome *assignment* and this gate is about terrain comfort at spawn, so the
# edge carries no special meaning here -- the same reasoning the notes already
# apply to mid-band erosion values. What settled it was checking the seeds already
# validated by hand: at +/-4000 only 2 of the 8 known-good seeds survive, at
# +/-6000 five do, and with no weirdness clause at all seven do. +/-4000 would
# have thrown away most of the collection to enforce a constraint that was never
# actually applied when those seeds were chosen.
#
# So the gate goes from 41.0% (erosion only, weirdness doing nothing) to 24.5%.
# Dials: 4000 tightens it to 10.5%; deleting the limex line restores the old
# behaviour exactly.
#
# Erosion keeps limok: its intent ("prefer moderate-to-high erosion") is an
# existence claim. Moving it to limex as well is a supported dial -- it takes the
# gate to 24.5% on its own -- but it tightens a search that is already tight, so
# it is left off by default.
OPEN_TERRAIN_WEIRD = 6000

# ---------------------------------------------------------------------------
# 5. Swamps -- an actual check instead of a marginal one
# ---------------------------------------------------------------------------
# "Hot/wet climate" is the gate that was supposed to deliver swamps. It does not:
# it passes 76.0% of seeds while only 30.0% have a column satisfying all four of
# its constraints simultaneously, and 66.5% of all seeds have a swamp or mangrove
# cluster regardless -- so it barely beats chance. (Where its box *does* co-locate
# it lands correctly: mangrove_swamp 55%, swamp 19%, jungle_edge 9%, jungle 8%,
# bamboo_jungle 4%. The box is aimed right; it just is not binding.)
#
# F_BIOME_SAMPLE is the tool for this. It takes a biome *set*, so one condition
# covers swamp and mangrove together -- F_BIOME_CENTER matches a single id and
# would need an F_LOGIC_OR node for the pair -- and its Monte-Carlo estimate
# aborts early, so it costs 2.5 ms against 48.4 ms for the equivalent centre scan.
#
# Measured over 200 seeds, against ground truth (a swamp or mangrove cluster of
# >= 128 cells somewhere in the box):
#
#   coverage >= 0.2%   passes 54.0%   2.80 ms   agrees with ground truth 87.5%
#   coverage >= 0.3%   passes 49.5%   2.62 ms   agrees 83.0%
#   coverage >= 0.5%   passes 43.5%   2.50 ms   agrees 77.0%
#   coverage >= 1.0%   passes 30.5%   2.12 ms   agrees 64.0%
#
# 0.2% is used because it tracks "a real swamp cluster exists" most closely.
# Higher thresholds drift away from that: they start rejecting worlds that do have
# a good swamp, just not a large *share* of the region. Note the gate measures a
# share of the area, not one contiguous patch. If you specifically want one large
# swamp, F_BIOME_CENTER on swamp (id 6) with biomeSize 128 passes 53.5% at
# 48.4 ms -- 19x the cost, and it cannot cover mangrove in the same condition.
#
# "Hot/wet climate" is kept: with this gate carrying the swamps, what it still
# contributes is the jungle half of its box. Dropping it saves 12.6 ms/seed.
SWAMP_BIOMES = [
    6,    # swamp
    184,  # mangrove_swamp
]
SWAMP_COVERAGE = 0.002
SWAMP_CONFIDENCE = 0.90
SWAMP_HALF = 1792
SAVE_SWAMP = 29

# ---------------------------------------------------------------------------
# 6. The three regional-variety gates, as biome checks
# ---------------------------------------------------------------------------
# Hot/wet, Hot/dry and Taiga are diversity gates: they ask that the region
# contain a climate family, not one biome. Written as climate boxes they have the
# same marginal-independence problem as everything else -- and for a diversity
# requirement that failure mode is worse than weak, it is *lossy*. Measured over
# 200 seeds, "gate rejects" counts seeds where the biomes are demonstrably
# present but the climate gate says no:
#
#            climate gate (limok)     biome sample (>=0.2%)   gate rejects
#   Hot/wet   76.0%   12.41 ms         89.5%    1.09 ms          20.5%
#   Hot/dry   90.0%    2.46 ms         84.5%    1.25 ms           2.5%
#   Taiga     93.5%   13.44 ms         82.5%    1.28 ms           0.0%
#
# Hot/wet was discarding one world in five that actually had the jungles and
# swamps. Replacing all three with F_BIOME_SAMPLE over the corresponding biome
# set makes each gate mean what its label says, stops the false rejections, and
# costs a tenth as much for Hot/wet and Taiga.
#
# Swamp present stays separate: the Hot/wet family gate is satisfied by jungle
# alone, so it does not guarantee a swamp.
VARIETY_COVERAGE = 0.002
VARIETY_CONFIDENCE = 0.90
VARIETY_HALF = 1792

# Verified ids (cubiomes biomes.h at e61f905). The mutated ids are base+128:
# bamboo_jungle 168, mangrove_swamp 184, windswept_savanna 163, eroded_badlands
# 165, old_growth_pine_taiga 32, old_growth_spruce_taiga 160.
#
# Every id here was checked against getAvailableBiomes(MC_1_21_WD): having an id
# in biomes.h is not the same as generating. badlands_plateau (39) was in this set
# and had to come out -- it is a pre-1.18 biome that still has an id but no longer
# generates, and the viewer refuses to run a condition containing one
# ("Biome condition with ID [31] includes 1 biome that does not generate").
# Note also that id 38 is wooded_badlands in 1.18+; wooded_badlands_plateau is
# just the legacy alias for the same id, and it does generate.
VARIETY_SETS = {
    "Hot/wet biomes": (30, [
        6,    # swamp
        184,  # mangrove_swamp
        21,   # jungle
        23,   # sparse_jungle (jungle_edge)
        168,  # bamboo_jungle
    ]),
    "Hot/dry biomes": (31, [
        35,   # savanna
        36,   # savanna_plateau
        163,  # windswept_savanna
        37,   # badlands
        38,   # wooded_badlands
        165,  # eroded_badlands
        2,    # desert
    ]),
    "Taiga biomes": (32, [
        5,    # taiga
        32,   # old_growth_pine_taiga (giant_tree_taiga)
        160,  # old_growth_spruce_taiga (giant_spruce_taiga)
    ]),
}

# Seeds already collected, including the five that survived the structures review.
KNOWN_SEED_SOURCES = [
    SESSIONS_DIR / "dappled-forest-structures-hunt.session",
    SESSIONS_DIR / "dappled-forest-structures.session",
    SESSIONS_DIR / "dappled-forest-archipelago.session",
    SESSIONS_DIR / "dappled-forest-snowy.session",
    SESSIONS_DIR / "dappled-forest.session",
]


def label_of(condition) -> str:
    return condition.text.split(b"\0", 1)[0].decode("utf-8", "ignore")


def retune_dappled(condition) -> None:
    for para, (lo, hi) in [
        (NP_TEMPERATURE, DAPPLED_TEMP),
        (NP_HUMIDITY, DAPPLED_HUMID),
        (NP_CONTINENTALNESS, DAPPLED_CONT),
        (NP_EROSION, DAPPLED_EROS),
        (NP_WEIRDNESS, DAPPLED_WEIRD),
    ]:
        condition.limok[para][0] = lo
        condition.limok[para][1] = hi


def retune_open_terrain(condition) -> None:
    # Erosion stays an existence check; weirdness becomes a containment check.
    condition.limok[NP_WEIRDNESS][0] = INT_MIN
    condition.limok[NP_WEIRDNESS][1] = INT_MAX
    condition.limex[NP_WEIRDNESS][0] = -OPEN_TERRAIN_WEIRD
    condition.limex[NP_WEIRDNESS][1] = OPEN_TERRAIN_WEIRD


def build_swamp_presence(base):
    condition = build_biome_sample_template(
        base=base,
        label="Swamp present",
        save=SAVE_SWAMP,
        relative=0,
    )
    condition.x1 = -SWAMP_HALF
    condition.z1 = -SWAMP_HALF
    condition.x2 = SWAMP_HALF
    condition.z2 = SWAMP_HALF
    set_biome_mask(condition, SWAMP_BIOMES)
    condition.converage = SWAMP_COVERAGE
    condition.confidence = SWAMP_CONFIDENCE
    condition.count = 0
    return condition


def build_variety_presence(base, label, save, biome_ids):
    condition = build_biome_sample_template(
        base=base,
        label=label,
        save=save,
        relative=0,
    )
    condition.x1 = -VARIETY_HALF
    condition.z1 = -VARIETY_HALF
    condition.x2 = VARIETY_HALF
    condition.z2 = VARIETY_HALF
    set_biome_mask(condition, biome_ids)
    condition.converage = VARIETY_COVERAGE
    condition.confidence = VARIETY_CONFIDENCE
    condition.count = 0
    return condition


def build_tuned_lines() -> list[str]:
    lines = build_archipelago_lines()

    cond_indexes = [idx for idx, line in enumerate(lines) if line.startswith("#Cond:")]
    if not cond_indexes:
        raise ValueError("no conditions found in archipelago session")

    base = decode_condition(lines[cond_indexes[0]])
    conditions = [decode_condition(lines[idx]) for idx in cond_indexes]
    conditions.extend(build_structure_conditions(base))
    conditions.append(build_swamp_presence(base))
    for label, (save, biome_ids) in VARIETY_SETS.items():
        conditions.append(build_variety_presence(base, label, save, biome_ids))

    conditions = [c for c in conditions if label_of(c) not in DROP_LABELS]

    for condition in conditions:
        label = label_of(condition)
        if label in DAPPLED_LABELS:
            retune_dappled(condition)
        elif label == "Open terrain":
            retune_open_terrain(condition)

    by_label = {label_of(c): c for c in conditions}
    if len(by_label) != len(conditions):
        raise ValueError("duplicate condition labels; ordering would be ambiguous")

    # Root siblings are evaluated in file order, and so are the children of each
    # parent, so emitting the groups in the orders above is what actually applies
    # the cost ordering. Children follow their parent for readability.
    order: list[str] = []
    for label in ROOT_ORDER:
        order.append(label)
        if label == "Spawn anchor":
            order.extend(SPAWN_ORDER)
        elif label == "Village":
            order.extend(VILLAGE_ORDER)

    missing = set(by_label) - set(order)
    unknown = set(order) - set(by_label)
    if missing or unknown:
        raise ValueError(f"ordering mismatch: unplaced={sorted(missing)} unknown={sorted(unknown)}")

    header = [line for line in lines if not line.startswith("#Cond:")]
    return header + [encode_condition(by_label[label]) for label in order]


def collect_known_seeds() -> list[int]:
    seeds: list[int] = []
    seen: set[int] = set()

    def add(value: int) -> None:
        if value not in seen:
            seen.add(value)
            seeds.append(value)

    for seed in FAVOURITE_SEEDS:
        add(seed)
    for path in KNOWN_SEED_SOURCES:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                add(int(line))
            except ValueError:
                continue
    return seeds


def main() -> None:
    lines = build_tuned_lines()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_SEEDS.write_text("\n".join(str(s) for s in collect_known_seeds()) + "\n")

    write_session(REVIEW_SESSION, lines, SEARCH_LIST, KNOWN_SEEDS)
    write_session(HUNT_SESSION, lines, SEARCH_BLOCKS, None)


if __name__ == "__main__":
    main()
