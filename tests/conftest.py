"""
Shared fixtures for the kitecast test suite.

Environment variables are set at module level — before any project module is
imported — so that config._require() does not raise on missing .env values.
"""
import os

# Must precede all project imports so config._require() succeeds.
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("SESSION_CHANNEL_ID", "111111111111111111")
os.environ.setdefault("GUILD_ID", "222222222222222222")
os.environ.setdefault("DB_PATH", "data/test.db")  # overridden per-test by the db fixture

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import database

# The integer form of the test guild ID, used in guild-check assertions.
GUILD_ID_INT = int(os.environ["GUILD_ID"])

# ---------------------------------------------------------------------------
# Canonical session dict — copy this in tests that need to tweak fields.
# ---------------------------------------------------------------------------
_SAMPLE_SESSION: dict = {
    "discord_user_id":     "100000000000000001",
    "discord_username":    "TestUser",
    "location":            "Magnuson Park",
    "session_date":        "2026-05-14",
    "session_time":        "14:00",
    "duration_minutes":    90,
    "kite_size_m":         12.0,
    "board_type":          "twin_tip",
    "wind_speed_estimate": "15-20",
    "wind_direction":      "SW",
    "tide_state":          "incoming",
    "beginner_friendly":   "yes",
    "conditions_rating":   4,
    "notes":               "Great session",
    "logged_at":           "2026-05-14 14:00:00",
}


@pytest_asyncio.fixture
async def db(tmp_path, monkeypatch):
    """Initialise a fresh in-directory database for each test, then tear it down."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", db_path)
    await database.init_db()
    return db_path


@pytest.fixture
def sample_session() -> dict:
    """Return a mutable copy of the canonical session dict."""
    return dict(_SAMPLE_SESSION)


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Return a MagicMock shaped like a discord.Interaction."""
    interaction = MagicMock()
    interaction.user.id = 100000000000000001
    interaction.user.display_name = "TestUser"
    interaction.guild_id = GUILD_ID_INT
    interaction.response.send_message = AsyncMock()
    interaction.original_response = AsyncMock()
    interaction.client.get_channel = MagicMock()
    return interaction
