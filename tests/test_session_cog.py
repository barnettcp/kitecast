"""
Tests for SessionCog command handlers and the error dispatcher.

Discord gateway objects (Interaction, Bot) are replaced with MagicMock /
AsyncMock so no real connection is needed.  Database calls are patched at
the `database` module level so the handlers never touch the filesystem.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import app_commands

from cogs.session import SessionCog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cog():
    """Return a SessionCog bound to a mock bot."""
    return SessionCog(MagicMock())


# ---------------------------------------------------------------------------
# /mysessions
# ---------------------------------------------------------------------------

async def test_mysessions_no_sessions_sends_helpful_message(cog, mock_interaction):
    with patch("database.fetch_user_sessions", new=AsyncMock(return_value=[])):
        await cog.mysessions.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    content, kwargs = (
        mock_interaction.response.send_message.call_args.args[0],
        mock_interaction.response.send_message.call_args.kwargs,
    )
    assert "haven't logged any sessions" in content
    assert kwargs.get("ephemeral") is True


async def test_mysessions_with_sessions_sends_embed(cog, mock_interaction):
    sessions = [
        {
            "conditions_rating": 4,
            "session_date": "2026-05-14",
            "location": "Magnuson Park",
            "board_type": "twin_tip",
            "wind_speed_estimate": "15-20",
        }
    ]
    with patch("database.fetch_user_sessions", new=AsyncMock(return_value=sessions)):
        await cog.mysessions.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    kwargs = mock_interaction.response.send_message.call_args.kwargs
    assert kwargs.get("ephemeral") is True
    embed = kwargs.get("embed")
    assert embed is not None
    assert embed.title == "Your Last Sessions"


async def test_mysessions_uses_caller_user_id(cog, mock_interaction):
    """fetch_user_sessions must be called with the interaction user's ID as a string."""
    mock_interaction.user.id = 100000000000000001
    with patch("database.fetch_user_sessions", new=AsyncMock(return_value=[])) as mock_fetch:
        await cog.mysessions.callback(cog, mock_interaction)
    mock_fetch.assert_called_once_with(str(mock_interaction.user.id))


# ---------------------------------------------------------------------------
# /leaderboard
# ---------------------------------------------------------------------------

async def test_leaderboard_empty_sends_message(cog, mock_interaction):
    with patch("database.fetch_leaderboard", new=AsyncMock(return_value=[])):
        await cog.leaderboard.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    content = mock_interaction.response.send_message.call_args.args[0]
    assert "No sessions" in content


async def test_leaderboard_with_sessions_sends_embed(cog, mock_interaction):
    sessions = [
        {
            "conditions_rating": 5,
            "session_date": "2026-05-14",
            "location": "Point Hudson",
            "board_type": "foil",
            "wind_speed_estimate": "20-25",
            "discord_username": "TestUser",
        }
    ]
    with patch("database.fetch_leaderboard", new=AsyncMock(return_value=sessions)):
        await cog.leaderboard.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_called_once()
    embed = mock_interaction.response.send_message.call_args.kwargs.get("embed")
    assert embed is not None
    assert "Top Sessions" in embed.title


async def test_leaderboard_embed_is_public(cog, mock_interaction):
    """The leaderboard embed should NOT be ephemeral."""
    sessions = [
        {
            "conditions_rating": 3,
            "session_date": "2026-05-14",
            "location": "Titlow Beach",
            "board_type": "twin_tip",
            "wind_speed_estimate": "10-15",
            "discord_username": "Bob",
        }
    ]
    with patch("database.fetch_leaderboard", new=AsyncMock(return_value=sessions)):
        await cog.leaderboard.callback(cog, mock_interaction)

    kwargs = mock_interaction.response.send_message.call_args.kwargs
    assert not kwargs.get("ephemeral", False)


# ---------------------------------------------------------------------------
# cog_app_command_error
# ---------------------------------------------------------------------------

async def test_error_handler_cooldown_message(cog, mock_interaction):
    error = app_commands.CommandOnCooldown(
        cooldown=app_commands.Cooldown(rate=1, per=60.0),
        retry_after=45.0,
    )
    await cog.cog_app_command_error(mock_interaction, error)

    mock_interaction.response.send_message.assert_called_once()
    call = mock_interaction.response.send_message.call_args
    assert "45s" in call.args[0]
    assert call.kwargs.get("ephemeral") is True


async def test_error_handler_cooldown_rounds_retry_after(cog, mock_interaction):
    """retry_after should be formatted as a whole number of seconds."""
    error = app_commands.CommandOnCooldown(
        cooldown=app_commands.Cooldown(rate=1, per=60.0),
        retry_after=7.8,
    )
    await cog.cog_app_command_error(mock_interaction, error)
    content = mock_interaction.response.send_message.call_args.args[0]
    assert "8s" in content


async def test_error_handler_check_failure_message(cog, mock_interaction):
    error = app_commands.CheckFailure()
    await cog.cog_app_command_error(mock_interaction, error)

    mock_interaction.response.send_message.assert_called_once()
    call = mock_interaction.response.send_message.call_args
    assert "not available here" in call.args[0]
    assert call.kwargs.get("ephemeral") is True


async def test_error_handler_ignores_unhandled_error_types(cog, mock_interaction):
    """Errors other than CommandOnCooldown / CheckFailure should be silently ignored."""
    error = app_commands.AppCommandError("unexpected")
    await cog.cog_app_command_error(mock_interaction, error)
    mock_interaction.response.send_message.assert_not_called()
