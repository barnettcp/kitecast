"""
Tests for the pure helper functions and the guild check in cogs/session.py.
No Discord gateway connection is required — all tests are synchronous.
"""
from unittest.mock import MagicMock

import pytest

from cogs.session import _fmt, _guild_check, _rating_color, _rating_emoji
from conftest import GUILD_ID_INT


# ---------------------------------------------------------------------------
# _rating_emoji
# ---------------------------------------------------------------------------

class TestRatingEmoji:
    def test_rating_1_is_red(self):
        assert _rating_emoji(1) == "🔴"

    def test_rating_2_is_red(self):
        assert _rating_emoji(2) == "🔴"

    def test_rating_3_is_yellow(self):
        assert _rating_emoji(3) == "🟡"

    def test_rating_4_is_green(self):
        assert _rating_emoji(4) == "🟢"

    def test_rating_5_is_green(self):
        assert _rating_emoji(5) == "🟢"


# ---------------------------------------------------------------------------
# _rating_color
# ---------------------------------------------------------------------------

class TestRatingColor:
    def test_rating_1_is_red(self):
        assert _rating_color(1) == 0xE74C3C

    def test_rating_2_is_red(self):
        assert _rating_color(2) == 0xE74C3C

    def test_rating_3_is_yellow(self):
        assert _rating_color(3) == 0xF1C40F

    def test_rating_4_is_green(self):
        assert _rating_color(4) == 0x2ECC71

    def test_rating_5_is_green(self):
        assert _rating_color(5) == 0x2ECC71

    def test_boundary_3_and_4_differ(self):
        assert _rating_color(3) != _rating_color(4)


# ---------------------------------------------------------------------------
# _fmt
# ---------------------------------------------------------------------------

class TestFmt:
    def test_returns_value_when_truthy(self):
        assert _fmt("Magnuson Park") == "Magnuson Park"

    def test_returns_em_dash_for_none(self):
        assert _fmt(None) == "\u2014"

    def test_returns_em_dash_for_empty_string(self):
        assert _fmt("") == "\u2014"

    def test_uses_custom_fallback_for_none(self):
        assert _fmt(None, fallback="N/A") == "N/A"

    def test_uses_custom_fallback_for_empty_string(self):
        assert _fmt("", fallback="unknown") == "unknown"

    def test_does_not_alter_truthy_value_when_fallback_given(self):
        assert _fmt("hello", fallback="N/A") == "hello"


# ---------------------------------------------------------------------------
# _guild_check
# ---------------------------------------------------------------------------

class TestGuildCheck:
    def _interaction(self, guild_id):
        interaction = MagicMock()
        interaction.guild_id = guild_id
        return interaction

    def test_returns_true_for_home_guild(self):
        assert _guild_check(self._interaction(GUILD_ID_INT)) is True

    def test_returns_false_for_different_guild(self):
        assert _guild_check(self._interaction(GUILD_ID_INT + 1)) is False

    def test_returns_false_for_none_guild_id(self):
        """DM interactions have guild_id == None and must be rejected."""
        assert _guild_check(self._interaction(None)) is False

    def test_returns_false_for_zero(self):
        assert _guild_check(self._interaction(0)) is False
