"""
Contract: src/pipeline/category_rotation.py
Purpose: Monthly category rotation for multi-category discovery.
         Rotates through all AU local-service-business DFS category codes
         so each month sweeps a different slice of the market.
Layer: pipeline
Directive: #294

Rotation logic:
  Month 1: codes[0:5]  (dental, medical, legal, accounting, construction)
  Month 2: codes[5:10] (plumbing, electrical, HVAC, real estate, restaurants)
  Month 3: codes[10:]  (hair salons, auto repair, car dealers, vet, gyms)
  Month 4: wraps to codes[0:5] (same as Month 1)

Category codes sourced from DFS taxonomy, validated against AU domain volumes
(spike Mar 2026).
"""
from __future__ import annotations

import datetime


# DFS category codes for AU local service businesses.
# Ordered by estimated AU domain volume (largest pools first within each tier).
MASTER_CATEGORIES: list[str] = [
    "10514",  # Dental practices
    "10091",  # General medical / GP clinics
    "13686",  # Legal services / law firms
    "11093",  # Accounting / bookkeeping
    "10282",  # Construction / building
    "13462",  # Plumbing services
    "11143",  # Electrical services
    "11147",  # HVAC / air conditioning
    "10040",  # Real estate agencies
    "10169",  # Restaurants / cafes
    "10333",  # Hair salons / barbers
    "10193",  # Auto repair / mechanics
    "13656",  # Car dealerships
    "11979",  # Veterinary clinics
    "10668",  # Gyms / fitness studios
]


class CategoryRotation:
    """
    Monthly rotation manager for multi-category discovery.

    Usage:
        rotation = CategoryRotation()
        this_month = rotation.get_categories_for_month(1)   # ["10514", "10091", ...]
        next_month  = rotation.get_categories_for_month(2)  # ["13462", "11143", ...]
    """

    def __init__(
        self,
        categories: list[str] | None = None,
        categories_per_month: int = 5,
    ) -> None:
        """
        Args:
            categories: Override the master list (useful for testing or
                        agency-specific subsets). Defaults to MASTER_CATEGORIES.
            categories_per_month: How many categories to sweep per month.
        """
        self._categories = categories or MASTER_CATEGORIES
        self._per_month = categories_per_month

    def get_categories_for_month(self, month: int) -> list[str]:
        """
        Return the slice of categories for a given 1-based month number.

        Month 1 → slice 0, Month 2 → slice 1, etc.
        Wraps around when the list is exhausted.

        Args:
            month: 1-based month number (1 = January or first month of service).

        Returns:
            List of DFS category code strings (up to categories_per_month).
        """
        if month < 1:
            raise ValueError(f"month must be >= 1, got {month}")
        n = len(self._categories)
        if n == 0:
            return []
        slice_index = (month - 1) % ((n + self._per_month - 1) // self._per_month)
        start = slice_index * self._per_month
        end = min(start + self._per_month, n)
        return self._categories[start:end]

    def get_all_categories(self) -> list[str]:
        """Return the complete category list (all slices)."""
        return list(self._categories)

    @staticmethod
    def current_month_number() -> int:
        """Return the current month-of-year (1–12) for calendar-based rotation."""
        return datetime.date.today().month
