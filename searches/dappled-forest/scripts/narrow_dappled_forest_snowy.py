#!/usr/bin/env python3
"""Snowy-adjacent variant of the Dappled Forest proxy session.

This is a *second version* of the Dappled Forest search aimed at a varied
coastal-survival seed: archipelago geography, strong biome transitions, and a
"home base plus expeditions" feel. It takes everything the base Dappled Forest
proxy already requires and adds one more root-level climate gate that demands a
genuinely snowy region somewhere in the central map.

Why snowy: the Dappled Forest box floors temperature at -4500 specifically to
exclude frozen/snowy land (it is a grassy forest, level 1). Snowy biomes sit in
the band *directly below* that floor (temperature level 0, <= -4500). Requiring
both in the same area forces the two bands to coexist -- a cold grassy forest
abutting frozen terrain -- which is exactly the strong-transition adjacency the
survival goal wants.

The chain is:

    viewer-search.session            (hand-maintained starter)
      -> update_starter_session.py   -> regenerates the starter
      -> narrow_dappled_forest.py    -> dappled-forest.session
      -> THIS script                 -> dappled-forest-snowy.session

This script derives the base Dappled Forest narrowing *in memory* (via
build_dappled_lines, reading the current starter) and layers the snowy gate on
top. It never writes dappled-forest.session, because that file accumulates
search results from actual viewer runs -- regenerating it would discard them.
Starter and Dappled Forest changes still flow through automatically, since both
sessions are built from the same starter on each run.

Run: python3 searches/dappled-forest/scripts/narrow_dappled_forest_snowy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STARTER_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(STARTER_SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from narrow_dappled_forest import build_dappled_lines, DAPPLED_LABEL  # noqa: E402

from update_starter_session import (  # noqa: E402
    build_climate_template,
    decode_condition,
    encode_condition,
    INT_MIN,
    INT_MAX,
    NP_TEMPERATURE,
    NP_CONTINENTALNESS,
)

DAPPLED_SNOWY_SESSION = (
    Path(__file__).resolve().parents[1] / "sessions" / "dappled-forest-snowy.session"
)

SNOWY_LABEL = "Snowy biomes"

# Save slot for the new condition. Must be unique within the session; 9 and 17+
# are unused by the starter (which spans 1..16), so 17 stays clear of any future
# starter additions in the low range.
SNOWY_SAVE = 17

# Snowy climate box (cubiomes scaled integers; game noise value * 10000).
#
#   temperature      ..-4500 : "snowy" is purely temperature level 0. Cubiomes
#                              puts every snowy land biome (snowy plains, snowy
#                              taiga, ice spikes, grove, snowy slopes, frozen
#                              peaks) below this edge -- it is the same -4500
#                              line the Dappled Forest box floors at, so the two
#                              gates select adjacent bands.
#   continentalness -1100..  : coast-or-inland bias. The defining snowy trait is
#                              temperature alone, but at full continentalness this
#                              gate is also satisfied by frozen *ocean*, which is
#                              just cold water near spawn -- not the explorable
#                              snowy land the survival goal wants. -1100 is the
#                              same near-coast threshold the starter's Coastal
#                              gate uses. Relax this first if hits are too sparse.
TEMP_MIN, TEMP_MAX = INT_MIN, -4500
CONT_MIN, CONT_MAX = -1100, INT_MAX


def build_snowy_climate(base):
    condition = build_climate_template(
        base=base,
        label=SNOWY_LABEL,
        save=SNOWY_SAVE,
        relative=0,
    )
    condition.x1 = -1792
    condition.z1 = -1792
    condition.x2 = 1792
    condition.z2 = 1792
    condition.limok[NP_TEMPERATURE][0] = TEMP_MIN
    condition.limok[NP_TEMPERATURE][1] = TEMP_MAX
    condition.limok[NP_CONTINENTALNESS][0] = CONT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = CONT_MAX
    return condition


def build_snowy_lines() -> list[str]:
    """Return the base Dappled Forest lines with the snowy gate inserted.

    Built entirely in memory (from build_dappled_lines, which reads the current
    starter) and returns the lines, so callers layering further conditions on top
    -- e.g. the archipelago variant -- can derive from this without writing, and
    without clobbering dappled-forest.session, which accumulates run results.
    """
    lines = build_dappled_lines()

    first_cond_index = None
    dappled_index = None
    for idx, line in enumerate(lines):
        if not line.startswith("#Cond:"):
            continue
        if first_cond_index is None:
            first_cond_index = idx
        condition = decode_condition(line)
        label = condition.text.split(b"\0", 1)[0].decode("utf-8", "ignore")
        if label == DAPPLED_LABEL:
            dappled_index = idx

    if first_cond_index is None:
        raise ValueError("no conditions found in base Dappled Forest session")
    if dappled_index is None:
        raise ValueError(f"{DAPPLED_LABEL!r} condition not found in base session")

    # Build from the first (oceanic) condition, matching how the starter seeds
    # every climate builder from a single base condition.
    base = decode_condition(lines[first_cond_index])
    snowy = build_snowy_climate(base)

    # Insert as a root climate gate right after the Dappled Forest gate -- cheap
    # climate noise check, so it sits among the other climate gates and ahead of
    # the expensive biome-presence scans.
    lines.insert(dappled_index + 1, encode_condition(snowy))
    return lines


def main() -> None:
    DAPPLED_SNOWY_SESSION.parent.mkdir(parents=True, exist_ok=True)
    DAPPLED_SNOWY_SESSION.write_text("\n".join(build_snowy_lines()) + "\n")


if __name__ == "__main__":
    main()
