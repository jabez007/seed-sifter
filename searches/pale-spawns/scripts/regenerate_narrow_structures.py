#!/usr/bin/env python3

"""Regenerate the narrowed structure export for the pale-spawns search."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_BROAD_STRUCTURES = Path("../data/raw/structures-broad-window.csv")
DEFAULT_NARROW_BIOMES = Path("../data/refined/biomes-narrow-window.csv")
DEFAULT_OUTPUT = Path("../data/refined/structures-narrow-window.csv")

X_MIN = -2382
X_MAX_EXCLUSIVE = 2382
Z_MIN = -2467
Z_MAX_INCLUSIVE = 2467


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broad-structures",
        type=Path,
        default=DEFAULT_BROAD_STRUCTURES,
        help="Path to the broad structure export CSV.",
    )
    parser.add_argument(
        "--narrow-biomes",
        type=Path,
        default=DEFAULT_NARROW_BIOMES,
        help="Path to the narrow biome summary CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the regenerated narrow structure CSV.",
    )
    return parser.parse_args()


def resolve_from_script_dir(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parent / path).resolve()


def load_seed_set(narrow_biomes_path: Path) -> set[str]:
    seeds: set[str] = set()
    with narrow_biomes_path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        for row in reader:
            if not row:
                continue
            first = row[0]
            if first == "Sep=" or first.startswith("#") or first == "seed":
                continue
            seeds.add(first)
    return seeds


def regenerate(
    broad_structures_path: Path,
    narrow_biomes_path: Path,
    output_path: Path,
) -> tuple[int, int]:
    seed_set = load_seed_set(narrow_biomes_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with broad_structures_path.open(newline="") as source, output_path.open(
        "w", newline=""
    ) as destination:
        reader = csv.reader(source, delimiter=";")
        writer = csv.writer(destination, delimiter=";", lineterminator="\n")

        writer.writerow(["Sep=", ""])
        writer.writerow(["#X1", str(X_MIN)])
        writer.writerow(["#Z1", str(Z_MIN)])
        writer.writerow(["#X2", str(X_MAX_EXCLUSIVE)])
        writer.writerow(["#Z2", str(Z_MAX_INCLUSIVE)])
        writer.writerow(["seed", "structure", "x", "z", "details"])

        for row in reader:
            if not row:
                continue
            first = row[0]
            if first == "Sep=" or first.startswith("#") or first == "seed":
                continue
            if first in seed_set:
                x = int(row[2])
                z = int(row[3])
                if not (X_MIN <= x < X_MAX_EXCLUSIVE and Z_MIN <= z <= Z_MAX_INCLUSIVE):
                    continue
                writer.writerow(row)
                rows_written += 1

    return len(seed_set), rows_written


def main() -> None:
    args = parse_args()
    broad_structures_path = resolve_from_script_dir(args.broad_structures)
    narrow_biomes_path = resolve_from_script_dir(args.narrow_biomes)
    output_path = resolve_from_script_dir(args.output)

    seed_count, row_count = regenerate(
        broad_structures_path=broad_structures_path,
        narrow_biomes_path=narrow_biomes_path,
        output_path=output_path,
    )
    print(f"wrote {row_count} rows for {seed_count} seeds to {output_path}")


if __name__ == "__main__":
    main()
