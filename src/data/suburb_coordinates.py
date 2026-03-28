# FILE: src/data/suburb_coordinates.py
# PURPOSE: Load and query AU suburb→coordinate mapping for DFS GMaps pipeline
# SOURCE: Elkfox Australian-Postcode-Data (public, MIT/open data)
#         https://github.com/Elkfox/Australian-Postcode-Data
# DIRECTIVE: #248

from __future__ import annotations

import csv
from pathlib import Path

# Default CSV path — bundled in repo
_DEFAULT_CSV = Path(__file__).parent / "au_suburbs.csv"


def format_dfs_coordinate(lat: float, lng: float, zoom: int = 14) -> str:
    """Return coordinate string in DataForSEO location_coordinate format.

    Example: format_dfs_coordinate(-33.8688, 151.2093) == "-33.8688,151.2093,14z"
    """
    return f"{lat},{lng},{zoom}z"


class SuburbCoordinateLoader:
    """Load and query Australian suburb coordinates from the bundled CSV.

    CSV source: Elkfox Australian-Postcode-Data
    Fields used: place_name (suburb), state_code, postcode, latitude, longitude

    Usage:
        loader = SuburbCoordinateLoader()
        loader.load()
        lat, lng = loader.get_coordinates("Sydney", "NSW")
        suburbs = loader.get_suburbs_by_state("NSW")
    """

    def __init__(self, csv_path: str | None = None) -> None:
        self._csv_path = Path(csv_path) if csv_path else _DEFAULT_CSV
        self._rows: list[dict] = []
        self._loaded = False
        # Index: (suburb_lower, state_lower) -> first matching row
        self._index: dict[tuple[str, str], dict] = {}
        # Index: state_upper (e.g. "NSW") -> list of rows
        self._state_index: dict[str, list[dict]] = {}
        # Index: postcode -> list of rows
        self._postcode_index: dict[str, list[dict]] = {}

    def load(self) -> None:
        """Read CSV into memory and build lookup indexes."""
        if self._loaded:
            return
        if not self._csv_path.exists():
            raise FileNotFoundError(f"Suburb CSV not found: {self._csv_path}")

        with open(self._csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                # Normalise to consistent internal schema
                row = {
                    "suburb": raw["place_name"].strip(),
                    "state": raw["state_code"].strip().upper(),
                    "postcode": raw["postcode"].strip(),
                    "lat": float(raw["latitude"]),
                    "lng": float(raw["longitude"]),
                    "accuracy": raw.get("accuracy", "").strip(),
                }
                self._rows.append(row)

                # Case-insensitive suburb+state lookup key
                key = (row["suburb"].lower(), row["state"].lower())
                if key not in self._index:
                    self._index[key] = row

                # State index keyed by UPPER (e.g. "NSW")
                state_key = row["state"]  # already .upper()
                self._state_index.setdefault(state_key, []).append(row)

                postcode_key = row["postcode"]
                self._postcode_index.setdefault(postcode_key, []).append(row)

        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def get_coordinates(self, suburb: str, state: str) -> tuple[float, float] | None:
        """Return (lat, lng) for a suburb+state, or None if not found.

        Case-insensitive match on both suburb and state.
        """
        self._ensure_loaded()
        key = (suburb.strip().lower(), state.strip().lower())
        row = self._index.get(key)
        if row is None:
            return None
        return (row["lat"], row["lng"])

    def get_suburbs_by_state(self, state: str) -> list[dict]:
        """Return all suburbs for a state, sorted by suburb name.

        Each dict has: suburb, state, postcode, lat, lng
        """
        self._ensure_loaded()
        rows = self._state_index.get(state.strip().upper(), [])
        return sorted(rows, key=lambda r: r["suburb"])

    def get_suburbs_by_postcode(self, postcode: str) -> list[dict]:
        """Return all suburbs for a postcode."""
        self._ensure_loaded()
        return self._postcode_index.get(postcode.strip(), [])

    @property
    def total_suburbs(self) -> int:
        """Total number of loaded suburb records."""
        self._ensure_loaded()
        return len(self._rows)

    @property
    def states(self) -> list[str]:
        """Sorted list of unique state codes in the dataset."""
        self._ensure_loaded()
        return sorted(self._state_index.keys())
