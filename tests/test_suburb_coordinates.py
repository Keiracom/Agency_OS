# FILE: tests/test_suburb_coordinates.py
# PURPOSE: Tests for SuburbCoordinateLoader and format_dfs_coordinate
# DIRECTIVE: #248

import pytest

from src.data.suburb_coordinates import SuburbCoordinateLoader, format_dfs_coordinate


# ============================================================
# format_dfs_coordinate (module-level function)
# ============================================================


def test_format_dfs_coordinate():
    """Default zoom=14 produces correct DFS coordinate string."""
    result = format_dfs_coordinate(-33.8688, 151.2093)
    assert result == "-33.8688,151.2093,14z"


def test_format_dfs_coordinate_custom_zoom():
    """Custom zoom value is respected."""
    result = format_dfs_coordinate(-33.8688, 151.2093, zoom=10)
    assert result == "-33.8688,151.2093,10z"


# ============================================================
# SuburbCoordinateLoader
# ============================================================


@pytest.fixture(scope="module")
def loader() -> SuburbCoordinateLoader:
    """Shared loaded instance across tests in this module."""
    s = SuburbCoordinateLoader()
    s.load()
    return s


def test_load_csv(loader):
    """load() completes without error and populates rows."""
    assert loader._loaded is True
    assert len(loader._rows) > 0


def test_get_coordinates_sydney(loader):
    """Sydney NSW returns lat near -33.87."""
    coords = loader.get_coordinates("Sydney", "NSW")
    assert coords is not None
    lat, lng = coords
    assert abs(lat - (-33.87)) < 0.1


def test_get_coordinates_case_insensitive(loader):
    """Case-insensitive lookup returns same result."""
    coords_canonical = loader.get_coordinates("Sydney", "NSW")
    coords_upper = loader.get_coordinates("SYDNEY", "nsw")
    assert coords_canonical is not None
    assert coords_upper is not None
    assert coords_canonical == coords_upper


def test_get_coordinates_not_found(loader):
    """Non-existent suburb returns None."""
    result = loader.get_coordinates("Neverland", "NSW")
    assert result is None


def test_get_suburbs_by_state_nsw(loader):
    """NSW suburb list has more than 500 entries."""
    suburbs = loader.get_suburbs_by_state("NSW")
    assert len(suburbs) > 500


def test_get_suburbs_by_state_vic(loader):
    """VIC suburb list has more than 400 entries."""
    suburbs = loader.get_suburbs_by_state("VIC")
    assert len(suburbs) > 400


def test_total_suburbs(loader):
    """Total suburb count is greater than 15000."""
    assert loader.total_suburbs > 15000
