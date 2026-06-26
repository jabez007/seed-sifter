#!/usr/bin/env python3

from __future__ import annotations

import ctypes as C
import copy
from pathlib import Path


SESSION_PATH = Path(__file__).resolve().parents[1] / "viewer-search.session"

F_CLIMATE_NOISE = 56
F_BIOME_SAMPLE = 66
F_BIOME_CENTER = 19
F_SPAWN = 15

FLG_IN_RANGE = 0x20

NP_TEMPERATURE = 0
NP_HUMIDITY = 1
NP_CONTINENTALNESS = 2
NP_EROSION = 3
NP_DEPTH = 4
NP_WEIRDNESS = 5

BIOME_MUSHROOM_FIELDS = 14
BIOME_OCEAN = 0
BIOME_DEEP_OCEAN = 24
BIOME_COLD_OCEAN = 46
BIOME_WARM_OCEAN = 44
BIOME_LUKEWARM_OCEAN = 45
BIOME_DEEP_COLD_OCEAN = 49
BIOME_DEEP_LUKEWARM_OCEAN = 48

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1


class Condition(C.Structure):
    _fields_ = [
        ("type", C.c_int16),
        ("meta", C.c_uint16),
        ("x1", C.c_int32),
        ("z1", C.c_int32),
        ("x2", C.c_int32),
        ("z2", C.c_int32),
        ("save", C.c_int32),
        ("relative", C.c_int32),
        ("skipref", C.c_uint8),
        ("pad0", C.c_uint8 * 3),
        ("text", C.c_char * 28),
        ("pad1", C.c_uint8 * 12),
        ("hash", C.c_uint64),
        ("deps", C.c_int8 * 16),
        ("biomeToFind", C.c_uint64),
        ("biomeToFindM", C.c_uint64),
        ("biomeId", C.c_int32),
        ("biomeSize", C.c_uint32),
        ("tol", C.c_uint8),
        ("minmax", C.c_uint8),
        ("para", C.c_uint8),
        ("octave", C.c_uint8),
        ("step", C.c_uint16),
        ("version", C.c_uint16),
        ("biomeToExcl", C.c_uint64),
        ("biomeToExclM", C.c_uint64),
        ("temps", C.c_int32 * 9),
        ("count", C.c_int32),
        ("y", C.c_int32),
        ("flags", C.c_uint32),
        ("rmax", C.c_int32),
        ("varflags", C.c_uint16),
        ("varbiome", C.c_int16),
        ("varstart", C.c_uint64),
        ("limok", (C.c_int32 * 2) * 6),
        ("limex", (C.c_int32 * 2) * 6),
        ("vmin", C.c_float),
        ("vmax", C.c_float),
        ("converage", C.c_float),
        ("confidence", C.c_float),
    ]


def decode_condition(line: str) -> Condition:
    return Condition.from_buffer_copy(bytes.fromhex(line.split(":", 1)[1].strip()))


def encode_condition(condition: Condition) -> str:
    return "#Cond: " + bytes(condition).hex()


def set_label(condition: Condition, label: str) -> None:
    encoded = label.encode("utf-8")
    if len(encoded) >= 28:
        raise ValueError("label too long for session format")
    condition.text = encoded


def set_full_climate_ranges(condition: Condition) -> None:
    for idx in range(6):
        condition.limok[idx][0] = INT_MIN
        condition.limok[idx][1] = INT_MAX
        condition.limex[idx][0] = INT_MIN
        condition.limex[idx][1] = INT_MAX


def set_biome_mask(condition: Condition, biome_ids: list[int]) -> None:
    low = 0
    mutated = 0
    for biome_id in biome_ids:
        if 0 <= biome_id < 64:
            low |= 1 << biome_id
        elif 128 <= biome_id < 192:
            mutated |= 1 << (biome_id - 128)
        else:
            raise ValueError(f"unsupported biome id for session bitmask: {biome_id}")
    condition.biomeToFind = low
    condition.biomeToFindM = mutated


def update_waterworld(condition: Condition) -> None:
    set_label(condition, "Waterworld climate")
    if condition.type == F_BIOME_SAMPLE:
        condition.type = F_CLIMATE_NOISE
        condition.biomeToFind = 0
        condition.biomeToFindM = 0
        condition.biomeToExcl = 0
        condition.biomeToExclM = 0
        condition.count = 0
        condition.converage = 0.0
        condition.confidence = 0.0
    elif condition.type != F_CLIMATE_NOISE:
        raise ValueError("expected first condition to be biome-sample or climate-noise")

    set_full_climate_ranges(condition)

    # Coarse prefilter:
    # require some strongly oceanic continentalness somewhere in the sampled area.
    condition.limok[NP_CONTINENTALNESS][0] = INT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = -4550


def update_spawn_anchor(condition: Condition) -> None:
    if condition.type != F_SPAWN:
        raise ValueError("expected second condition to be a spawn condition")
    condition.save = 2
    set_label(condition, "Spawn anchor")


def build_climate_template(base: Condition, label: str, save: int, relative: int) -> Condition:
    condition = copy.copy(base)
    set_label(condition, label)
    condition.type = F_CLIMATE_NOISE
    condition.save = save
    condition.relative = relative
    condition.biomeToFind = 0
    condition.biomeToFindM = 0
    condition.biomeToExcl = 0
    condition.biomeToExclM = 0
    condition.count = 0
    condition.converage = 0.0
    condition.confidence = 0.0
    set_full_climate_ranges(condition)
    return condition


def build_biome_sample_template(
    base: Condition,
    label: str,
    save: int,
    relative: int,
) -> Condition:
    condition = copy.copy(base)
    set_label(condition, label)
    condition.type = F_BIOME_SAMPLE
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
    condition.temps = (C.c_int32 * 9)()
    condition.count = 0
    condition.y = 256
    condition.flags = FLG_IN_RANGE
    condition.rmax = 0
    condition.varflags = 0
    condition.varbiome = 0
    condition.varstart = 0
    set_full_climate_ranges(condition)
    condition.vmin = 0.0
    condition.vmax = 0.0
    condition.converage = 0.0
    condition.confidence = 0.0
    return condition


def build_biome_center_template(
    base: Condition,
    label: str,
    save: int,
    relative: int,
) -> Condition:
    condition = copy.copy(base)
    set_label(condition, label)
    condition.type = F_BIOME_CENTER
    condition.save = save
    condition.relative = relative
    condition.hash = 0
    for idx in range(16):
        condition.deps[idx] = 0
    condition.biomeToFind = 0
    condition.biomeToFindM = 0
    condition.biomeToExcl = 0
    condition.biomeToExclM = 0
    condition.biomeId = BIOME_MUSHROOM_FIELDS
    condition.biomeSize = 0
    condition.tol = 0
    condition.minmax = 0
    condition.para = 0
    condition.octave = 0
    condition.step = 0
    condition.temps = (C.c_int32 * 9)()
    condition.count = 1
    condition.y = 256
    condition.flags = 0
    condition.rmax = 0
    condition.varflags = 0
    condition.varbiome = 0
    condition.varstart = 0
    set_full_climate_ranges(condition)
    condition.vmin = 0.0
    condition.vmax = 0.0
    condition.converage = 0.0
    condition.confidence = 0.0
    return condition


def build_coastalness_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Coastal",
        save=3,
        relative=2,
    )
    condition.x1 = -128
    condition.z1 = -128
    condition.x2 = 128
    condition.z2 = 128
    # Require at least some coastal or ocean-adjacent continentalness near spawn.
    condition.limok[NP_CONTINENTALNESS][0] = INT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = -1100
    return condition


def build_open_terrain_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Open terrain",
        save=5,
        relative=2,
    )
    condition.x1 = -64
    condition.z1 = -64
    condition.x2 = 64
    condition.z2 = 64
    # Heuristic prefilter for flatter terrain:
    # prefer moderate-to-high erosion and avoid extreme weirdness.
    condition.limok[NP_EROSION][0] = 1500
    condition.limok[NP_EROSION][1] = INT_MAX
    condition.limok[NP_WEIRDNESS][0] = -2000
    condition.limok[NP_WEIRDNESS][1] = 2000
    return condition


def build_warm_sea_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Warm sea",
        save=4,
        relative=2,
    )
    condition.x1 = -192
    condition.z1 = -192
    condition.x2 = 192
    condition.z2 = 192
    # Use the cubiomes lukewarm/warm-ocean temperature boundary so this is
    # less often satisfied by neutral ocean near spawn.
    condition.limok[NP_TEMPERATURE][0] = 2001
    condition.limok[NP_TEMPERATURE][1] = INT_MAX
    condition.limok[NP_CONTINENTALNESS][0] = INT_MIN
    condition.limok[NP_CONTINENTALNESS][1] = -1900
    return condition


def build_central_sea_coverage(base: Condition) -> Condition:
    condition = build_biome_sample_template(
        base=base,
        label="Central sea coverage",
        save=10,
        relative=0,
    )
    condition.x1 = -1536
    condition.z1 = -1536
    condition.x2 = 1536
    condition.z2 = 1536
    # Require the central map area to be dominantly navigable sea while
    # favoring neutral-to-warm ocean families over cold or frozen water.
    set_biome_mask(
        condition,
        [
            BIOME_OCEAN,
            BIOME_DEEP_OCEAN,
            BIOME_COLD_OCEAN,
            BIOME_WARM_OCEAN,
            BIOME_LUKEWARM_OCEAN,
            BIOME_DEEP_COLD_OCEAN,
            BIOME_DEEP_LUKEWARM_OCEAN,
        ],
    )
    condition.converage = 0.53
    condition.confidence = 0.95
    return condition


def build_mushroom_island(base: Condition) -> Condition:
    condition = build_biome_center_template(
        base=base,
        label="Mushroom island",
        save=11,
        relative=0,
    )
    condition.x1 = -1536
    condition.z1 = -1536
    condition.x2 = 1536
    condition.z2 = 1536
    # Require one meaningfully sized mushroom-fields island in the same
    # broad central-ocean area as the coverage gate.
    condition.biomeSize = 256
    # Allow slight edge irregularity without relaxing the size check much.
    condition.tol = 2
    return condition


def build_hot_wet_diversity_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Hot/wet climate",
        save=6,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Approximate a useful overlap between swamp / mangrove-swamp and the
    # sparser jungle variants. A single climate box cannot isolate exactly
    # those four biomes, so this leans swampy with very high erosion while
    # keeping enough heat and humidity for sparse/bamboo jungle terrain too.
    condition.limok[NP_TEMPERATURE][0] = 1000
    condition.limok[NP_TEMPERATURE][1] = 5500
    condition.limok[NP_HUMIDITY][0] = 1000
    condition.limok[NP_HUMIDITY][1] = INT_MAX
    condition.limok[NP_CONTINENTALNESS][0] = -1100
    condition.limok[NP_CONTINENTALNESS][1] = INT_MAX
    condition.limok[NP_EROSION][0] = 5500
    condition.limok[NP_EROSION][1] = INT_MAX
    return condition


def build_hot_dry_diversity_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Hot/dry climate",
        save=7,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Lean toward savanna / badlands terrain rather than generic hot-dry space.
    condition.limok[NP_TEMPERATURE][0] = 2000
    condition.limok[NP_TEMPERATURE][1] = INT_MAX
    condition.limok[NP_HUMIDITY][0] = INT_MIN
    condition.limok[NP_HUMIDITY][1] = -1000
    condition.limok[NP_EROSION][0] = INT_MIN
    condition.limok[NP_EROSION][1] = 500
    return condition


def build_taiga_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Taiga climate",
        save=8,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Target regular taiga plus the two old-growth taiga variants while
    # excluding snowy taiga. Cubiomes puts snowy_taiga at temperature <= -4500,
    # so keeping the lower bound just above that cuts it out cleanly.
    condition.limok[NP_TEMPERATURE][0] = -4499
    condition.limok[NP_TEMPERATURE][1] = -1500
    condition.limok[NP_HUMIDITY][0] = 1000
    condition.limok[NP_HUMIDITY][1] = INT_MAX
    condition.limok[NP_CONTINENTALNESS][0] = -1900
    condition.limok[NP_CONTINENTALNESS][1] = INT_MAX
    return condition


def build_cherry_grove_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Cherry Grove climate",
        save=13,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Use the cubiomes Cherry Grove biome row directly. Unlike the Pale Garden
    # helper, this condition keeps the full climate box because the colder,
    # drier band is part of what distinguishes Cherry Grove from the other
    # high-weirdness inland terrain targets.
    condition.limok[NP_TEMPERATURE][0] = -4500
    condition.limok[NP_TEMPERATURE][1] = 2000
    condition.limok[NP_HUMIDITY][0] = INT_MIN
    condition.limok[NP_HUMIDITY][1] = -1000
    condition.limok[NP_CONTINENTALNESS][0] = 300
    condition.limok[NP_CONTINENTALNESS][1] = INT_MAX
    condition.limok[NP_EROSION][0] = -7799
    condition.limok[NP_EROSION][1] = 500
    condition.limok[NP_WEIRDNESS][0] = 2666
    condition.limok[NP_WEIRDNESS][1] = INT_MAX
    return condition


def build_pale_garden_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Pale Garden climate",
        save=12,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Use the full cubiomes Pale Garden biome row so this condition stays
    # distinct from Cherry Grove instead of only matching the shared inland /
    # low-erosion / high-weirdness terrain shape.
    condition.limok[NP_TEMPERATURE][0] = -1500
    condition.limok[NP_TEMPERATURE][1] = 2000
    condition.limok[NP_HUMIDITY][0] = 3000
    condition.limok[NP_HUMIDITY][1] = INT_MAX
    condition.limok[NP_CONTINENTALNESS][0] = 300
    condition.limok[NP_CONTINENTALNESS][1] = INT_MAX
    condition.limok[NP_EROSION][0] = -7799
    condition.limok[NP_EROSION][1] = 500
    condition.limok[NP_WEIRDNESS][0] = 2666
    condition.limok[NP_WEIRDNESS][1] = INT_MAX
    return condition


def build_dappled_forest_climate(base: Condition) -> Condition:
    condition = build_climate_template(
        base=base,
        label="Dappled Forest climate",
        save=14,
        relative=0,
    )
    condition.x1 = -2048
    condition.z1 = -2048
    condition.x2 = 2048
    condition.z2 = 2048
    # Estimated from current snapshot descriptions, not a verified cubiomes row.
    # The intent is cold, very dry, high-weirdness land that can still appear
    # across a broad range of terrain and relatively near colder coasts.
    condition.limok[NP_TEMPERATURE][0] = -4500
    condition.limok[NP_TEMPERATURE][1] = 2000
    condition.limok[NP_HUMIDITY][0] = INT_MIN
    condition.limok[NP_HUMIDITY][1] = -1000
    condition.limok[NP_CONTINENTALNESS][0] = -1899
    condition.limok[NP_CONTINENTALNESS][1] = INT_MAX
    condition.limok[NP_WEIRDNESS][0] = 2666
    condition.limok[NP_WEIRDNESS][1] = INT_MAX
    return condition


def main() -> None:
    original_lines = SESSION_PATH.read_text().splitlines()
    lines = []
    removable_labels = {
        "Coastal",
        "Coastalness climate",
        "Open terrain climate",
        "Open terrain",
        "Warm sea",
        "Warm sea climate",
        "Central sea coverage",
        "Mushroom island",
        "Warm sea coverage",
        "Hot/wet diversity climate",
        "Hot/dry diversity climate",
        "Hot/wet climate",
        "Hot/dry climate",
        "Taiga climate",
        "Cherry Grove climate",
        "Pale Garden climate",
        "Dappled Forest climate",
        "Relief diversity climate",
        "Relief diversity",
        "Open terrain",
        "11% Ocean",
        "3% Pale Garden",
        "2% River or Ocean",
    }
    for line in original_lines:
        if not line.startswith("#Cond:"):
            lines.append(line)
            continue
        condition = decode_condition(line)
        label = condition.text.split(b"\0", 1)[0].decode("utf-8", "ignore")
        if label in removable_labels:
            continue
        lines.append(line)

    cond_indexes = [idx for idx, line in enumerate(lines) if line.startswith("#Cond:")]
    if not cond_indexes:
        raise ValueError("no conditions found in starter session")

    first_index = cond_indexes[0]
    first_condition = decode_condition(lines[first_index])
    update_waterworld(first_condition)
    lines[first_index] = encode_condition(first_condition)

    if len(cond_indexes) < 2:
        raise ValueError("expected a spawn anchor condition in starter session")
    second_index = cond_indexes[1]
    second_condition = decode_condition(lines[second_index])
    update_spawn_anchor(second_condition)
    lines[second_index] = encode_condition(second_condition)

    root_insert_at = second_index
    lines.insert(root_insert_at, encode_condition(build_hot_wet_diversity_climate(first_condition)))
    lines.insert(root_insert_at + 1, encode_condition(build_hot_dry_diversity_climate(first_condition)))
    lines.insert(root_insert_at + 2, encode_condition(build_taiga_climate(first_condition)))
    lines.insert(root_insert_at + 3, encode_condition(build_cherry_grove_climate(first_condition)))
    lines.insert(root_insert_at + 4, encode_condition(build_pale_garden_climate(first_condition)))
    lines.insert(root_insert_at + 5, encode_condition(build_dappled_forest_climate(first_condition)))

    spawn_insert_at = second_index + 7
    lines.insert(spawn_insert_at, encode_condition(build_coastalness_climate(first_condition)))
    lines.insert(spawn_insert_at + 1, encode_condition(build_warm_sea_climate(first_condition)))
    lines.insert(spawn_insert_at + 2, encode_condition(build_open_terrain_climate(first_condition)))
    lines.insert(spawn_insert_at + 3, encode_condition(build_central_sea_coverage(first_condition)))
    lines.insert(spawn_insert_at + 4, encode_condition(build_mushroom_island(first_condition)))

    SESSION_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
