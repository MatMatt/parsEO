"""Data helpers and static resources for parseo."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class LandsatSceneKey:
    """Hashable identifier for a WRS-2 path/row pair."""

    path: int
    row: int

    def __post_init__(self) -> None:
        if not (1 <= self.path <= 233):
            raise ValueError(f"path must be between 1 and 233; got {self.path}")
        if not (1 <= self.row <= 248):
            raise ValueError(f"row must be between 1 and 248; got {self.row}")

    @classmethod
    def from_strings(cls, path: str, row: str) -> "LandsatSceneKey":
        return cls(int(path), int(row))

    def as_id(self) -> str:
        return f"{self.path:03d}{self.row:03d}"


def load_landsat_epsg_lookup() -> dict[str, str]:
    """Return the static Landsat path/row -> EPSG lookup table."""

    with resources.files(__package__).joinpath("landsat_epsg_lookup.json").open("r", encoding="utf-8") as fp:
        data: dict[str, str] = json.load(fp)
    return data
