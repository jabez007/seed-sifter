#!/usr/bin/env python3
"""Derive a Dappled Forest focused session from the shared starter session.

Dappled Forest is a Minecraft 26.3 biome (first snapshot June 2026). cubiomes
and cubiomes-viewer (4.1.2, 1.21 Winter Drop) do not know about it: there is no
biome id to target and no verified cubiomes parameter row. This session
therefore narrows the *climate box* only, as a proxy. It filters the raw 6D
noise for the traits the biome is described with -- cold, very little humidity,
high weirdness -- rather than for the biome itself.

Caveat: the tools generate 1.21 worlds, not 26.3, so this is a forward-looking
proxy. It assumes the underlying noise field is stable between versions, as it
has been when past biomes (Cherry Grove, Pale Garden) were carved out of
existing parameter space without regenerating the field. That assumption is not
guaranteed.

The script reads the current starter session and rewrites only the
"Dappled Forest climate" condition, so re-running it picks up any later starter
changes and re-applies the narrowing on top.

Run: python3 searches/dappled-forest/scripts/narrow_dappled_forest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STARTER_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(STARTER_SCRIPTS))

from update_starter_session import (  # noqa: E402
    Condition,
    decode_condition,
    encode_condition,
    INT_MIN,
    INT_MAX,
    NP_TEMPERATURE,
    NP_HUMIDITY,
    NP_CONTINENTALNESS,
    NP_EROSION,
    NP_WEIRDNESS,
    SESSION_PATH as STARTER_SESSION,
)

DAPPLED_SESSION = (
    Path(__file__).resolve().parents[1] / "sessions" / "dappled-forest.session"
)

DAPPLED_LABEL = "Dappled Forest climate"

# Narrowed climate box (cubiomes scaled integers; game noise value * 10000).
# Only the two traits the biome is actually described by are tightened. The
# starter's continentalness and weirdness bounds are kept verbatim because the
# description does not constrain them, and erosion is left unconstrained.
#
#   temperature -4500..-1500 : "cold" (level 1). Drops the milder level-2 band
#                              the starter estimate still allowed, and keeps the
#                              -4500 floor so frozen/snowy terrain (level 0) is
#                              excluded -- it is a grassy forest, not snowy.
#   humidity        ..-3500  : "very little humidity" (driest level 0). Tighter
#                              than the starter's level 0-1 (..-1000).
#   continentalness -1899..  : unchanged from the starter estimate (inland).
#   erosion          1000..  : flat/plains bias (plains-replacement theory: plains
#                              are flat, flat terrain is high erosion / low erosion
#                              is jagged). Started at the band edge 500 (level 3/4,
#                              which drops the jagged levels 0-3), then nudged a bit
#                              into level 4 for a stronger flat bias. Mid-band has
#                              no biome-assignment meaning, but terrain flatness
#                              responds to raw erosion continuously, so a higher
#                              floor still selects flatter ground. The next actual
#                              band edge up is 4500 (level 5+), a large jump.
#                              Orthogonal to weirdness; unverified hypothesis, A/B it.
#   weirdness        3333..  : the variant lever, eased back from 3667 now that
#                              erosion carries some of the discrimination.
TEMP_MIN, TEMP_MAX = -4500, -1500
HUMID_MIN, HUMID_MAX = INT_MIN, -3500
CONT_MIN, CONT_MAX = -1899, INT_MAX
EROS_MIN, EROS_MAX = 1000, INT_MAX
WEIRD_MIN, WEIRD_MAX = 3333, INT_MAX


def narrow_dappled_forest(condition: Condition) -> None:
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


def main() -> None:
    lines = STARTER_SESSION.read_text().splitlines()
    found = False
    for idx, line in enumerate(lines):
        if not line.startswith("#Cond:"):
            continue
        condition = decode_condition(line)
        label = condition.text.split(b"\0", 1)[0].decode("utf-8", "ignore")
        if label != DAPPLED_LABEL:
            continue
        narrow_dappled_forest(condition)
        lines[idx] = encode_condition(condition)
        found = True

    if not found:
        raise ValueError(f"{DAPPLED_LABEL!r} condition not found in starter session")

    DAPPLED_SESSION.parent.mkdir(parents=True, exist_ok=True)
    DAPPLED_SESSION.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
