#!/usr/bin/env python3
"""Structure variant of the Dappled Forest archipelago session.

Fourth link in the chain. It takes the archipelago coastal-survival session and
adds the settlement half of the goal: a *village* that has Dappled-Forest-like
climate nearby, and a *stronghold* within reach of that same village.

    viewer-search.session                       (hand-maintained starter)
      -> update_starter_session.py              -> regenerates the starter
      -> narrow_dappled_forest.py               -> dappled-forest.session
      -> narrow_dappled_forest_snowy.py         -> dappled-forest-snowy.session
      -> narrow_dappled_forest_archipelago.py   -> dappled-forest-archipelago.session
      -> THIS script                            -> dappled-forest-structures.session
                                                -> dappled-forest-structures-hunt.session
                                                -> data/analysis-inputs/known-seeds.txt

Like the other links it derives everything in memory (via build_archipelago_lines)
and writes only its own files, so upstream run results are never clobbered and
starter / Dappled / snowy / archipelago changes all flow through on each run.

Two sessions are written from the same condition list:

  dappled-forest-structures.session       #Search: SEARCH_LIST -- re-tests the
      seeds already collected (known-seeds.txt) against the new criteria.
  dappled-forest-structures-hunt.session  #Search: SEARCH_BLOCKS -- the same
      criteria against fresh seed space, to keep finding new candidates.

Run the review first, then the hunt. They are separate files because a seed-list
search and a full-space search need different headers (the list search needs
#List64 pointing at the seed file, the hunt must *not* have a seed list -- in
SEARCH_INC / SEARCH_BLOCKS a non-empty list is reinterpreted as a 48-bit
candidate list, which would silently confine the hunt to the low 48 bits of the
seeds we already have; see preSearch() in searchthread.cpp).

How proximity is expressed (verified against cubiomes-viewer search.cpp, 4.1.2):

  - F_CLIMATE_NOISE reports the *center of its own search box* as its position
    (cent = midpoint of x1..x2, z1..z2), not the place where the climate actually
    matched. So a climate gate cannot be used as the anchor for "something near
    the Dappled Forest" -- anything hung off it would just be near the box center.
  - Structure filters do report real positions, and _testTreeAt splits a
    BR_CLUST filter with count == 1 into one subbranch per instance: each village
    found is tried in turn, its dependent conditions are tested relative to that
    village, and the instances are combined with OR.

So the anchor is inverted: the village is the parent, and both "Dappled Forest
climate nearby" and "stronghold within reach" hang off it. The whole group reads
as: there exists a village in the central area that has Dappled-Forest-like
climate within DAPPLED_NEAR_HALF blocks and a stronghold within
STRONGHOLD_RADIUS blocks.

Run: python3 searches/dappled-forest/scripts/narrow_dappled_forest_structures.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

STARTER_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(STARTER_SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narrow_dappled_forest_archipelago import build_archipelago_lines  # noqa: E402

# The near-village climate box is imported from the base proxy rather than
# restated, so tuning the Dappled Forest box in one place retunes this too.
from narrow_dappled_forest import (  # noqa: E402
    TEMP_MIN,
    TEMP_MAX,
    HUMID_MIN,
    HUMID_MAX,
    CONT_MIN,
    CONT_MAX,
    EROS_MIN,
    EROS_MAX,
    WEIRD_MIN,
    WEIRD_MAX,
)

from update_starter_session import (  # noqa: E402
    Condition,
    build_climate_template,
    set_label,
    set_full_climate_ranges,
    decode_condition,
    encode_condition,
    F_VILLAGE,
    F_STRONGHOLD,
    NP_TEMPERATURE,
    NP_HUMIDITY,
    NP_CONTINENTALNESS,
    NP_EROSION,
    NP_WEIRDNESS,
)

SESSIONS_DIR = Path(__file__).resolve().parents[1] / "sessions"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "analysis-inputs"

REVIEW_SESSION = SESSIONS_DIR / "dappled-forest-structures.session"
HUNT_SESSION = SESSIONS_DIR / "dappled-forest-structures-hunt.session"
KNOWN_SEEDS = DATA_DIR / "known-seeds.txt"

# Search types, from the combobox enum in cubiomes-viewer src/config.h:
#   enum { SEARCH_INC = 0, SEARCH_BLOCKS = 1, SEARCH_LIST = 2, SEARCH_48ONLY = 3 };
SEARCH_BLOCKS = 1
SEARCH_LIST = 2

# Save slots. Unique within the session; the starter spans 1..16, the snowy gate
# uses 17 and the archipelago gates use 18..25, so the structure group takes
# 26..28. (readHex rejects any slot outside 0..99.)
SAVE_VILLAGE = 26
SAVE_DAPPLED_NEAR = 27
SAVE_STRONGHOLD = 28

# Village search area, matching the central region the root climate gates use, so
# "the village is in the play area" means the same thing everywhere.
VILLAGE_HALF = 1792

# Half-width of the Dappled Forest climate window centred on each village.
#
# 384 puts the required climate within ~540 blocks (box corner) of the village --
# walkable, but far enough that the biome does not have to be underneath the
# village itself. Note the known F_CLIMATE_NOISE caveat: each parameter's range
# over the window is checked *independently*, so in principle the temperature
# could hit its band in one corner and the weirdness in another. That is the same
# trick the "Coast: water"/"Coast: land" gates rely on deliberately -- here it is
# a precision cost instead, and it shrinks as the window shrinks, because nearby
# columns have correlated noise. Tighten toward 192 for a stronger guarantee that
# the whole climate signature lands in one place; widen for more hits and a
# looser reading of "near".
DAPPLED_NEAR_HALF = 384

# Stronghold radius around the village, in blocks (F_STRONGHOLD applies rmax as a
# true circular distance, not a box).
#
# Worth knowing before tuning: for MC 1.9+ strongholds generate at
# r = 1408 + 3072*n + 1280*[0,1] (+/-112) from the world origin, so the entire
# first ring -- 3 strongholds -- sits between ~1300 and ~2800 blocks out, and the
# second ring does not start until ~4480. Nothing generates closer than ~1300
# blocks to (0,0). A village near spawn therefore *cannot* have a stronghold a few
# hundred blocks away, no matter how many seeds are searched; this gate implicitly
# pushes the qualifying village outward, toward the first ring. 1280 is about the
# smallest radius that still leaves a workable hit rate. Raising it toward 2048
# loosens the search considerably; dropping it below ~768 makes the combination
# very rare.
STRONGHOLD_RADIUS = 1280

# Seeds already collected, newest search first. Their run results are the input to
# the review pass.
KNOWN_SEED_SOURCES = [
    SESSIONS_DIR / "dappled-forest-archipelago.session",
    SESSIONS_DIR / "dappled-forest-snowy.session",
    SESSIONS_DIR / "dappled-forest.session",
]

# Seeds to place at the head of the review list, so the run reports on them first.
FAVOURITE_SEEDS = [
    -3876754854235865083,
]


def build_structure_template(base: Condition, label: str, save: int, relative: int, ftype: int) -> Condition:
    """A structure filter with every biome / climate / variant field cleared.

    Structure filters ignore biomeToFind and the climate limits, but the fields
    are still serialized, so they are zeroed to keep the condition readable in the
    viewer and to avoid inheriting anything from the condition used as the base.
    """
    condition = copy.copy(base)
    set_label(condition, label)
    condition.type = ftype
    condition.save = save
    condition.relative = relative
    condition.hash = 0
    for idx in range(16):
        condition.deps[idx] = 0
    condition.biomeToFind = 0
    condition.biomeToFindM = 0
    condition.biomeToExcl = 0
    condition.biomeToExclM = 0
    condition.biomeId = 0
    condition.biomeSize = 0
    condition.tol = 0
    condition.minmax = 0
    condition.para = 0
    condition.octave = 0
    condition.step = 0
    condition.y = 256
    condition.flags = 0
    condition.rmax = 0
    # varflags = 0 means "any variant": no zombie-village / start-piece / village
    # biome restriction. Setting VAR_WITH_START here would be the way to demand a
    # specifically snowy or taiga village, but that pins a *single* biome per
    # condition, so a set would need an F_LOGIC_OR node.
    condition.varflags = 0
    condition.varbiome = 0
    condition.varstart = 0
    set_full_climate_ranges(condition)
    condition.vmin = 0.0
    condition.vmax = 0.0
    condition.converage = 0.0
    condition.confidence = 0.0
    # At least one instance. count == 1 is also what makes this branch per
    # instance instead of averaging the positions together (see BR_CLUST in
    # _testTreeAt) -- with any other count the children would be tested against
    # the centroid of several villages, which is not a real place.
    condition.count = 1
    return condition


def build_village(base: Condition) -> Condition:
    condition = build_structure_template(
        base=base,
        label="Village",
        save=SAVE_VILLAGE,
        relative=0,
        ftype=F_VILLAGE,
    )
    condition.x1 = -VILLAGE_HALF
    condition.z1 = -VILLAGE_HALF
    condition.x2 = VILLAGE_HALF
    condition.z2 = VILLAGE_HALF
    return condition


def build_dappled_near_village(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Dappled near village",
        save=SAVE_DAPPLED_NEAR,
        relative=SAVE_VILLAGE,
    )
    condition.x1 = -DAPPLED_NEAR_HALF
    condition.z1 = -DAPPLED_NEAR_HALF
    condition.x2 = DAPPLED_NEAR_HALF
    condition.z2 = DAPPLED_NEAR_HALF
    # The same box as the root Dappled Forest gate, re-checked in a small window
    # around this particular village. The root gate only says the climate exists
    # somewhere in the central 3584x3584 area; this says it exists next door.
    condition.limok[NP_TEMPERATURE][0] = TEMP_MIN
    condition.limok[NP_TEMPERATURE][1] = TEMP_MAX
    condition.limok[NP_HUMIDITY][0] = HUMID_MIN
    condition.limok[NP_HUMIDITY][1] = HUMID_MAX
    condition.limok[NP_CONTINENTALNESS][0] = CONT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = CONT_MAX
    condition.limok[NP_EROSION][0] = EROS_MIN
    condition.limok[NP_EROSION][1] = EROS_MAX
    condition.limok[NP_WEIRDNESS][0] = WEIRD_MIN
    condition.limok[NP_WEIRDNESS][1] = WEIRD_MAX
    return condition


def build_stronghold_near_village(base: Condition) -> Condition:
    condition = build_structure_template(
        base=base,
        label="Stronghold near village",
        save=SAVE_STRONGHOLD,
        relative=SAVE_VILLAGE,
        ftype=F_STRONGHOLD,
    )
    # rmax > 0 replaces the x1..z2 box with a circle of this radius around the
    # parent position. The box fields are ignored in that case, but are set to the
    # bounding square so the condition still reads sensibly in the viewer.
    condition.rmax = STRONGHOLD_RADIUS
    condition.x1 = -STRONGHOLD_RADIUS
    condition.z1 = -STRONGHOLD_RADIUS
    condition.x2 = STRONGHOLD_RADIUS
    condition.z2 = STRONGHOLD_RADIUS
    return condition


def build_structure_conditions(base: Condition) -> list[Condition]:
    return [
        # Parent: branches over every village in the central area.
        build_village(base),
        # Children, tested per village and ANDed. Cheapest discriminator first:
        # the climate window rejects most villages before the stronghold scan,
        # which has to walk the stronghold ring generator.
        build_dappled_near_village(base),
        build_stronghold_near_village(base),
    ]


def build_structure_lines() -> list[str]:
    """Return the archipelago lines with the village / stronghold group appended."""
    lines = build_archipelago_lines()

    cond_indexes = [idx for idx, line in enumerate(lines) if line.startswith("#Cond:")]
    if not cond_indexes:
        raise ValueError("no conditions found in archipelago session")

    base = decode_condition(lines[cond_indexes[0]])
    conditions = build_structure_conditions(base)

    # Append after the last existing condition. Sibling conditions are evaluated
    # in file order (ConditionTree::set pushes references in the order it reads
    # them), so putting the structure group last keeps every cheap climate gate
    # and the coverage scans ahead of the per-village work.
    insert_at = cond_indexes[-1] + 1
    for offset, condition in enumerate(conditions):
        lines.insert(insert_at + offset, encode_condition(condition))

    return lines


def collect_known_seeds() -> list[int]:
    """Every seed found by the earlier runs, favourites first, de-duplicated."""
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


def write_session(path: Path, lines: list[str], searchtype: int, seed_list: Path | None) -> None:
    """Write a session with the given search type, dropping any inherited results.

    Only header and condition lines are carried over: a session's trailing seed
    numbers are its *results* list, which is meaningless for a freshly generated
    session and, in a SEARCH_BLOCKS run, would be misread as a 48-bit candidate
    list.
    """
    out: list[str] = []
    for line in lines:
        if line.startswith("#Cond:"):
            out.append(line)
            continue
        if not line.startswith("#"):
            continue
        if line.startswith("#List64:"):
            continue
        if line.startswith("#Progress:"):
            # Where the run resumes. In a list search this is matched against the
            # seed list and falls back to the first entry when absent, so 0 means
            # "start at the beginning" in both search types.
            out.append("#Progress: 0")
            continue
        if line.startswith("#ResStop:"):
            # Never stop on the first hit: both sessions are batch runs -- the
            # review wants a verdict on every known seed, the hunt wants a list.
            out.append("#ResStop:  0")
            continue
        if line.startswith("#Search:"):
            out.append(f"#Search:   {searchtype}")
            if seed_list is not None:
                out.append(f"#List64:   {seed_list}")
            continue
        out.append(line)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")


def main() -> None:
    lines = build_structure_lines()

    seeds = collect_known_seeds()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_SEEDS.write_text("\n".join(str(seed) for seed in seeds) + "\n")

    # The viewer resolves #List64 relative to its own working directory, which is
    # wherever the app happened to be launched from, so an absolute path is the
    # only reliable form. It is machine-specific by nature -- re-run this script
    # after cloning elsewhere, or repoint the list in the viewer's search tab.
    write_session(REVIEW_SESSION, lines, SEARCH_LIST, KNOWN_SEEDS)
    write_session(HUNT_SESSION, lines, SEARCH_BLOCKS, None)


if __name__ == "__main__":
    main()
