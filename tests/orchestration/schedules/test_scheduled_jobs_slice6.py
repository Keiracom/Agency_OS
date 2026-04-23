"""
Tests that PHASE-2-SLICE-6 flows are registered in SCHEDULE_REGISTRY with
the correct cron + timezone. Slice 7 Track B.
"""
from __future__ import annotations

from prefect.client.schemas.schedules import CronSchedule

from src.orchestration.schedules.scheduled_jobs import (
    SCHEDULE_REGISTRY,
    get_daily_warming_schedule,
    get_monthly_cycle_close_schedule,
    get_schedule_config,
    get_weekly_linkedin_reset_schedule,
    list_all_schedules,
)


# -- schedule helper re-exports --------------------------------------------

def test_daily_warming_schedule_cron_and_tz():
    s = get_daily_warming_schedule()
    assert isinstance(s, CronSchedule)
    assert s.cron == "0 2 * * *"
    assert str(s.timezone) == "Australia/Sydney"


def test_weekly_linkedin_reset_schedule_cron_and_tz():
    s = get_weekly_linkedin_reset_schedule()
    assert isinstance(s, CronSchedule)
    assert s.cron == "0 0 * * 1"
    assert str(s.timezone) == "Australia/Sydney"


def test_monthly_cycle_close_schedule_cron_and_tz():
    s = get_monthly_cycle_close_schedule()
    assert isinstance(s, CronSchedule)
    assert s.cron == "30 0 1 * *"
    assert str(s.timezone) == "Australia/Sydney"


# -- registry entries present ----------------------------------------------

def test_daily_warming_registered():
    assert "daily_warming" in SCHEDULE_REGISTRY
    entry = SCHEDULE_REGISTRY["daily_warming"]
    assert isinstance(entry["schedule"], CronSchedule)
    assert entry["work_queue"] == "agency-os-queue"
    assert "warming" in entry["tags"]


def test_weekly_linkedin_reset_registered():
    assert "weekly_linkedin_reset" in SCHEDULE_REGISTRY
    entry = SCHEDULE_REGISTRY["weekly_linkedin_reset"]
    assert isinstance(entry["schedule"], CronSchedule)
    assert "linkedin" in entry["tags"]
    assert "rate-limit" in entry["tags"]


def test_monthly_cycle_close_registered():
    assert "monthly_cycle_close" in SCHEDULE_REGISTRY
    entry = SCHEDULE_REGISTRY["monthly_cycle_close"]
    assert isinstance(entry["schedule"], CronSchedule)
    assert "cycle" in entry["tags"]
    assert "monthly" in entry["tags"]


# -- public API surface ----------------------------------------------------

def test_get_schedule_config_returns_daily_warming():
    cfg = get_schedule_config("daily_warming")
    assert cfg["description"].startswith("Daily mailbox warming advance")


def test_list_all_schedules_includes_new_entries():
    names = list_all_schedules()
    assert "daily_warming" in names
    assert "weekly_linkedin_reset" in names
    assert "monthly_cycle_close" in names


# -- idempotent registration (re-import side-effect-free) -------------------

def test_registry_is_idempotent_on_reimport():
    import importlib

    from src.orchestration.schedules import scheduled_jobs

    first_keys = set(scheduled_jobs.SCHEDULE_REGISTRY.keys())
    reloaded = importlib.reload(scheduled_jobs)
    second_keys = set(reloaded.SCHEDULE_REGISTRY.keys())
    assert first_keys == second_keys
    # No duplicates — the dict literal is declared once per module load
    assert len(second_keys) == len(first_keys)
