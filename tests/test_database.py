"""
Tests for database.py — all SQL functions exercised against an in-memory
SQLite database via the `db` fixture from conftest.py.
"""
from datetime import datetime

import aiosqlite
import pytest

import database


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

async def test_init_db_creates_sessions_table(db):
    async with aiosqlite.connect(db) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None


async def test_init_db_creates_locations_table(db):
    async with aiosqlite.connect(db) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='locations'"
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None


async def test_init_db_seeds_all_locations(db):
    """All 8 hardcoded locations should be present after init."""
    locations = await database.fetch_locations()
    assert len(locations) == 8


async def test_init_db_is_idempotent(db):
    """Calling init_db a second time must not duplicate the seed data."""
    await database.init_db()
    locations = await database.fetch_locations()
    assert len(locations) == 8


# ---------------------------------------------------------------------------
# insert_session
# ---------------------------------------------------------------------------

async def test_insert_session_returns_positive_int(db, sample_session):
    row_id = await database.insert_session(sample_session)
    assert isinstance(row_id, int)
    assert row_id > 0


async def test_insert_session_persists_data(db, sample_session):
    await database.insert_session(sample_session)
    rows = await database.fetch_user_sessions(sample_session["discord_user_id"])
    assert len(rows) == 1
    assert rows[0]["location"] == "Magnuson Park"
    assert rows[0]["conditions_rating"] == 4
    assert rows[0]["board_type"] == "twin_tip"


async def test_insert_session_ids_increment(db, sample_session):
    id1 = await database.insert_session(sample_session)
    id2 = await database.insert_session(sample_session)
    assert id2 > id1


async def test_insert_session_optional_fields_nullable(db, sample_session):
    """Optional columns should accept None without error."""
    sample_session["session_time"] = None
    sample_session["duration_minutes"] = None
    sample_session["kite_size_m"] = None
    sample_session["notes"] = None
    row_id = await database.insert_session(sample_session)
    assert row_id > 0


# ---------------------------------------------------------------------------
# fetch_user_sessions
# ---------------------------------------------------------------------------

async def test_fetch_user_sessions_empty_for_unknown_user(db):
    rows = await database.fetch_user_sessions("nonexistent")
    assert rows == []


async def test_fetch_user_sessions_returns_only_own_sessions(db, sample_session):
    await database.insert_session(sample_session)

    other = dict(sample_session)
    other["discord_user_id"] = "999999999999999999"
    await database.insert_session(other)

    rows = await database.fetch_user_sessions(sample_session["discord_user_id"])
    assert len(rows) == 1
    assert all(r["discord_user_id"] == sample_session["discord_user_id"] for r in rows)


async def test_fetch_user_sessions_ordered_newest_first(db, sample_session):
    older = dict(sample_session)
    older["session_date"] = "2026-04-01"
    older["logged_at"] = "2026-04-01 10:00:00"

    newer = dict(sample_session)
    newer["session_date"] = "2026-05-14"
    newer["logged_at"] = "2026-05-14 14:00:00"

    await database.insert_session(older)
    await database.insert_session(newer)

    rows = await database.fetch_user_sessions(sample_session["discord_user_id"])
    assert rows[0]["session_date"] == "2026-05-14"
    assert rows[1]["session_date"] == "2026-04-01"


async def test_fetch_user_sessions_default_limit_is_five(db, sample_session):
    for _ in range(7):
        await database.insert_session(sample_session)
    rows = await database.fetch_user_sessions(sample_session["discord_user_id"])
    assert len(rows) == 5


async def test_fetch_user_sessions_custom_limit(db, sample_session):
    for _ in range(7):
        await database.insert_session(sample_session)
    rows = await database.fetch_user_sessions(sample_session["discord_user_id"], limit=3)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# fetch_leaderboard
# ---------------------------------------------------------------------------

async def test_fetch_leaderboard_empty_when_no_sessions(db):
    rows = await database.fetch_leaderboard()
    assert rows == []


async def test_fetch_leaderboard_excludes_old_sessions(db, sample_session):
    old = dict(sample_session)
    old["session_date"] = "2024-01-15"
    await database.insert_session(old)
    rows = await database.fetch_leaderboard()
    assert rows == []


async def test_fetch_leaderboard_ordered_by_rating_descending(db, sample_session):
    today = datetime.now().strftime("%Y-%m-%d")

    low = dict(sample_session)
    low["conditions_rating"] = 2
    low["session_date"] = today
    low["logged_at"] = "2026-05-14 10:00:00"

    high = dict(sample_session)
    high["conditions_rating"] = 5
    high["session_date"] = today
    high["logged_at"] = "2026-05-14 11:00:00"

    await database.insert_session(low)
    await database.insert_session(high)

    rows = await database.fetch_leaderboard()
    assert rows[0]["conditions_rating"] == 5
    assert rows[1]["conditions_rating"] == 2


async def test_fetch_leaderboard_respects_limit(db, sample_session):
    today = datetime.now().strftime("%Y-%m-%d")
    session = dict(sample_session)
    session["session_date"] = today
    for _ in range(7):
        await database.insert_session(session)
    rows = await database.fetch_leaderboard(limit=3)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# fetch_locations
# ---------------------------------------------------------------------------

async def test_fetch_locations_returns_all_spots(db):
    locations = await database.fetch_locations()
    assert len(locations) == 8


async def test_fetch_locations_ordered_alphabetically(db):
    locations = await database.fetch_locations()
    names = [loc["name"] for loc in locations]
    assert names == sorted(names)


async def test_fetch_locations_drano_lake_has_no_noaa_station(db):
    """Drano Lake is a freshwater lake and should have a NULL noaa_station_id."""
    locations = await database.fetch_locations()
    drano = next((loc for loc in locations if loc["name"] == "Drano Lake"), None)
    assert drano is not None
    assert drano["noaa_station_id"] is None


async def test_fetch_locations_required_fields_present(db):
    locations = await database.fetch_locations()
    for loc in locations:
        assert loc.get("name")
        assert loc.get("latitude") is not None
        assert loc.get("longitude") is not None
