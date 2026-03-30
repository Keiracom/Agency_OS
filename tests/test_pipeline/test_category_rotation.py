"""Tests for CategoryRotation — Directive #294."""
import pytest
from src.pipeline.category_rotation import CategoryRotation, MASTER_CATEGORIES


class TestCategoryRotation:
    def test_master_list_has_15_categories(self):
        r = CategoryRotation()
        assert len(r.get_all_categories()) == 15

    def test_dental_is_first_category(self):
        r = CategoryRotation()
        assert r.get_all_categories()[0] == "10514"

    def test_month1_returns_5_categories(self):
        r = CategoryRotation(categories_per_month=5)
        cats = r.get_categories_for_month(1)
        assert len(cats) == 5

    def test_month1_different_from_month2(self):
        r = CategoryRotation(categories_per_month=5)
        m1 = r.get_categories_for_month(1)
        m2 = r.get_categories_for_month(2)
        assert m1 != m2
        assert set(m1).isdisjoint(set(m2))  # no overlap

    def test_month3_last_slice(self):
        r = CategoryRotation(categories_per_month=5)
        m3 = r.get_categories_for_month(3)
        assert len(m3) == 5
        all_cats = r.get_all_categories()
        assert m3 == all_cats[10:15]

    def test_rotation_wraps_month4_equals_month1(self):
        r = CategoryRotation(categories_per_month=5)
        m1 = r.get_categories_for_month(1)
        m4 = r.get_categories_for_month(4)
        assert m1 == m4

    def test_rotation_wraps_month5_equals_month2(self):
        r = CategoryRotation(categories_per_month=5)
        m2 = r.get_categories_for_month(2)
        m5 = r.get_categories_for_month(5)
        assert m2 == m5

    def test_get_all_categories_returns_all(self):
        r = CategoryRotation()
        all_cats = r.get_all_categories()
        assert len(all_cats) == 15
        assert "10514" in all_cats
        assert "10668" in all_cats

    def test_month_less_than_1_raises(self):
        r = CategoryRotation()
        with pytest.raises(ValueError):
            r.get_categories_for_month(0)

    def test_custom_category_list(self):
        r = CategoryRotation(categories=["10514", "13462", "11143"], categories_per_month=2)
        m1 = r.get_categories_for_month(1)
        assert len(m1) == 2
        assert m1 == ["10514", "13462"]

    def test_single_category_per_month(self):
        r = CategoryRotation(categories_per_month=1)
        assert r.get_categories_for_month(1) == ["10514"]
        assert r.get_categories_for_month(2) == ["10091"]

    def test_current_month_number_is_valid(self):
        month = CategoryRotation.current_month_number()
        assert 1 <= month <= 12
