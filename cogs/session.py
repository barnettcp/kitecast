from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import database
from config import GUILD_ID, SESSION_CHANNEL_ID


def _guild_check(interaction: discord.Interaction) -> bool:
    """Restrict commands to the configured home guild."""
    return interaction.guild_id == GUILD_ID


# ---------------------------------------------------------------------------
# Static select options
# ---------------------------------------------------------------------------

_BOARD_TYPES = [
    discord.SelectOption(label="Twin Tip",    value="twin_tip"),
    discord.SelectOption(label="Directional", value="directional"),
    discord.SelectOption(label="Foil",        value="foil"),
]

_WIND_SPEEDS = [
    discord.SelectOption(label="10-15 knots", value="10-15"),
    discord.SelectOption(label="15-20 knots", value="15-20"),
    discord.SelectOption(label="20-25 knots", value="20-25"),
    discord.SelectOption(label="25+ knots",   value="25+"),
]

_WIND_DIRECTIONS = [
    discord.SelectOption(label=d, value=d)
    for d in ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
]

_TIDE_STATES = [
    discord.SelectOption(label="Incoming", value="incoming"),
    discord.SelectOption(label="Outgoing", value="outgoing"),
    discord.SelectOption(label="High",     value="high"),
    discord.SelectOption(label="Low",      value="low"),
    discord.SelectOption(label="Slack",    value="slack"),
]

_BEGINNER_OPTIONS = [
    discord.SelectOption(label="Yes",             value="yes"),
    discord.SelectOption(label="With Supervision",value="with_supervision"),
    discord.SelectOption(label="No",              value="no"),
]

_RATING_OPTIONS = [
    discord.SelectOption(label="⭐ 1 — Poor",          value="1"),
    discord.SelectOption(label="⭐⭐ 2 — Below Average", value="2"),
    discord.SelectOption(label="⭐⭐⭐ 3 — Average",      value="3"),
    discord.SelectOption(label="⭐⭐⭐⭐ 4 — Good",        value="4"),
    discord.SelectOption(label="⭐⭐⭐⭐⭐ 5 — Excellent",  value="5"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rating_emoji(rating: int) -> str:
    """Return a coloured circle emoji corresponding to a conditions rating.

    - 🟢 for 4-5 (good to excellent)
    - 🟡 for 3 (average)
    - 🔴 for 1-2 (poor to below average)
    """
    if rating >= 4:
        return "🟢"
    if rating == 3:
        return "🟡"
    return "🔴"


def _rating_color(rating: int) -> int:
    """Return the Discord embed hex colour corresponding to a conditions rating.

    - Green  (``0x2ECC71``) for 4-5
    - Yellow (``0xF1C40F``) for 3
    - Red    (``0xE74C3C``) for 1-2
    """
    if rating >= 4:
        return 0x2ECC71
    if rating == 3:
        return 0xF1C40F
    return 0xE74C3C


def _fmt(value: str | None, fallback: str = "\u2014") -> str:
    """Return ``value`` if truthy, otherwise ``fallback``.

    Used to display optional session fields as an em-dash when absent.
    """
    return value if value else fallback


# ---------------------------------------------------------------------------
# Generic tracking select
#
# Discord limits a View to 5 ActionRows; each Select occupies one row.
# With 7 selects we split across two pages (4 + 3) to stay within limits.
# Each TrackingSelect stores its chosen value on the parent View via setattr.
# ---------------------------------------------------------------------------

class TrackingSelect(discord.ui.Select):
    """A Select menu that writes the chosen value back to its parent View.

    Discord limits a View to 5 ActionRows (one per Select or Button).
    With 7 fields to collect, the ``/logsession`` flow is split across two
    Views (pages).  Each ``TrackingSelect`` stores its selection on the
    parent View as an attribute named ``attr_name``, which the Submit/Next
    button reads before proceeding.
    """

    def __init__(self, attr_name: str, **kwargs):
        """Initialise the select and record which View attribute to update.

        Args:
            attr_name: Name of the attribute on the parent View that will
                receive the selected value.
            **kwargs: Forwarded to ``discord.ui.Select``.
        """
        super().__init__(**kwargs)
        self.attr_name = attr_name

    async def callback(self, interaction: discord.Interaction):
        """Store the selected value on the parent View and defer the interaction."""
        setattr(self.view, self.attr_name, self.values[0])
        await interaction.response.defer()


# ---------------------------------------------------------------------------
# Modal (text fields)
# ---------------------------------------------------------------------------

class SessionModal(discord.ui.Modal, title="Log Your Session"):
    """Modal presented in step 2 of the ``/logsession`` flow.

    Collects the five text-based session fields: date, time, duration,
    kite size, and free-text notes.  Dropdown selections from the two
    preceding Views are passed in via ``select_data`` and merged with the
    modal's text inputs before the record is written to the database.

    Discord modals support a maximum of 5 ``TextInput`` components.
    """
    session_date = discord.ui.TextInput(
        label="Session Date (YYYY-MM-DD)",
        placeholder="e.g. 2026-05-09",
        max_length=10,
    )
    session_time = discord.ui.TextInput(
        label="Session Start Time (HH:MM, 24-hour)",
        placeholder="e.g. 14:30",
        required=False,
        max_length=5,
    )
    duration_minutes = discord.ui.TextInput(
        label="Duration (minutes)",
        placeholder="e.g. 90",
        required=False,
        max_length=4,
    )
    kite_size_m = discord.ui.TextInput(
        label="Kite Size (square meters)",
        placeholder="e.g. 12.0",
        required=False,
        max_length=5,
    )
    notes = discord.ui.TextInput(
        label="Notes (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(self, select_data: dict):
        """Initialise the modal and pre-fill today's date.

        Args:
            select_data: Dictionary of values collected from the two
                preceding Select Menu Views (location, board type, wind
                speed/direction, tide state, beginner-friendly, rating).
        """
        super().__init__()
        # Pre-fill today's date
        self.session_date.default = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.select_data = select_data

    async def on_submit(self, interaction: discord.Interaction):
        """Validate inputs, persist the session, and post the public embed.

        Validates the date format and optional numeric fields before writing.
        On success, sends a formatted embed to ``SESSION_CHANNEL_ID`` and
        responds to the user with an ephemeral confirmation.  On any DB
        failure the user receives an ephemeral error message.
        """
        # Validate date
        try:
            datetime.strptime(self.session_date.value, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message(
                "Invalid date — please use YYYY-MM-DD (e.g. 2026-05-09).",
                ephemeral=True,
            )
            return

        # Parse optional numeric fields
        duration: int | None = None
        if self.duration_minutes.value.strip():
            try:
                duration = int(self.duration_minutes.value.strip())
            except ValueError:
                await interaction.response.send_message(
                    "Duration must be a whole number (e.g. 90).",
                    ephemeral=True,
                )
                return

        kite_size: float | None = None
        if self.kite_size_m.value.strip():
            try:
                kite_size = float(self.kite_size_m.value.strip())
            except ValueError:
                await interaction.response.send_message(
                    "Kite size must be a number (e.g. 12.0).",
                    ephemeral=True,
                )
                return

        if duration is not None and not (1 <= duration <= 720):
            await interaction.response.send_message(
                "Duration must be between 1 and 720 minutes.",
                ephemeral=True,
            )
            return

        if kite_size is not None and not (1.0 <= kite_size <= 30.0):
            await interaction.response.send_message(
                "Kite size must be between 1.0 and 30.0 m².",
                ephemeral=True,
            )
            return

        now_utc = datetime.now(timezone.utc)
        data = {
            "discord_user_id":    str(interaction.user.id),
            "discord_username":   interaction.user.display_name,
            "location":           self.select_data["location"],
            "session_date":       self.session_date.value,
            "session_time":       self.session_time.value.strip() or None,
            "duration_minutes":   duration,
            "kite_size_m":        kite_size,
            "board_type":         self.select_data["board_type"],
            "wind_speed_estimate":self.select_data["wind_speed_estimate"],
            "wind_direction":     self.select_data["wind_direction"],
            "tide_state":         self.select_data["tide_state"],
            "beginner_friendly":  self.select_data["beginner_friendly"],
            "conditions_rating":  int(self.select_data["conditions_rating"]),
            "notes":              self.notes.value.strip() or None,
            "logged_at":          now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            await database.insert_session(data)
        except Exception:
            await interaction.response.send_message(
                "Failed to save your session. Please try again.",
                ephemeral=True,
            )
            return

        # Build embed
        rating = data["conditions_rating"]
        embed = discord.Embed(
            title=(
                f"{_rating_emoji(rating)} Session at {data['location']}"
                f" — logged by {interaction.user.display_name}"
            ),
            color=_rating_color(rating),
        )
        embed.add_field(name="Date",             value=data["session_date"],                                          inline=True)
        embed.add_field(name="Time",             value=_fmt(data["session_time"]),                                    inline=True)
        embed.add_field(name="Duration",         value=f"{duration} min" if duration else "—",                        inline=True)
        embed.add_field(name="Rating",           value=f"{'⭐' * rating} ({rating}/5)",                               inline=True)
        embed.add_field(name="Wind Speed",       value=f"{data['wind_speed_estimate']} kts",                          inline=True)
        embed.add_field(name="Wind Direction",   value=data["wind_direction"],                                         inline=True)
        embed.add_field(name="Tide State",       value=data["tide_state"].replace("_", " ").title(),                  inline=True)
        embed.add_field(name="Board Type",       value=data["board_type"].replace("_", " ").title(),                  inline=True)
        embed.add_field(name="Kite Size",        value=f"{kite_size} m²" if kite_size else "—",                      inline=True)
        embed.add_field(name="Beginner Friendly",value=data["beginner_friendly"].replace("_", " ").title(),           inline=True)

        if data["notes"]:
            embed.add_field(name="Notes", value=data["notes"], inline=False)

        embed.set_footer(text=f"Logged at {now_utc.strftime('%Y-%m-%d %H:%M')} UTC")

        channel = interaction.client.get_channel(SESSION_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

        await interaction.response.send_message("Session logged! ✅", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle unexpected exceptions raised inside ``on_submit``."""
        await interaction.response.send_message(
            "Something went wrong saving your session. Please try again.",
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# Page 2 View — Tide state, Beginner friendly, Conditions rating
# ---------------------------------------------------------------------------

class ConditionsView(discord.ui.View):
    """Page 2 of the ``/logsession`` flow.

    Presents three Select menus (tide state, beginner-friendly,
    conditions rating) and a button that opens the ``SessionModal``.
    Selected values are merged with the data carried forward from page 1
    before the modal is shown.
    """

    def __init__(self, page1_data: dict):
        """Initialise the View with selections carried over from page 1.

        Args:
            page1_data: Dictionary containing the selections made on
                ``SessionFlowView`` (location, board type, wind speed,
                wind direction).
        """
        super().__init__(timeout=180)
        self.page1_data = page1_data
        self.message: discord.Message | None = None

        # Tracked values (populated by TrackingSelect callbacks)
        self.tide_state: str | None = None
        self.beginner_friendly: str | None = None
        self.conditions_rating: str | None = None

        self.add_item(TrackingSelect("tide_state",        placeholder="Select tide state...",    options=_TIDE_STATES,     row=0))
        self.add_item(TrackingSelect("beginner_friendly", placeholder="Beginner friendly?",       options=_BEGINNER_OPTIONS, row=1))
        self.add_item(TrackingSelect("conditions_rating", placeholder="Conditions rating (1–5)…", options=_RATING_OPTIONS,   row=2))

    @discord.ui.button(label="Open Session Form →", style=discord.ButtonStyle.green, row=3)
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Validate page 2 selections and open the ``SessionModal``.

        Sends an ephemeral error listing any unselected fields if the user
        clicks the button before completing all three dropdowns.
        """
        missing = [
            name for name, val in (
                ("Tide State",        self.tide_state),
                ("Beginner Friendly", self.beginner_friendly),
                ("Conditions Rating", self.conditions_rating),
            )
            if val is None
        ]
        if missing:
            await interaction.response.send_message(
                f"Please select: {', '.join(missing)}",
                ephemeral=True,
            )
            return

        select_data = {
            **self.page1_data,
            "tide_state":        self.tide_state,
            "beginner_friendly": self.beginner_friendly,
            "conditions_rating": self.conditions_rating,
        }
        await interaction.response.send_modal(SessionModal(select_data))

    async def on_timeout(self):
        """Edit the ephemeral message to inform the user the form has expired."""
        if self.message:
            try:
                await self.message.edit(
                    content="This session form expired. Please run `/logsession` again.",
                    view=None,
                )
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------------
# Page 1 View — Location, Board type, Wind speed, Wind direction
# ---------------------------------------------------------------------------

class SessionFlowView(discord.ui.View):
    """Page 1 of the ``/logsession`` flow.

    Presents four Select menus (location, board type, wind speed, wind
    direction) and a Next button that transitions to ``ConditionsView``.
    Location options are loaded dynamically from the ``locations`` table
    so new spots can be added without a code change.
    """

    def __init__(self, locations: list[dict]):
        """Build the View with dynamically loaded location options.

        Args:
            locations: List of location rows from the database, each a
                plain dictionary containing at minimum a ``name`` key.
        """
        super().__init__(timeout=180)
        self.message: discord.Message | None = None

        # Tracked values
        self.location: str | None = None
        self.board_type: str | None = None
        self.wind_speed_estimate: str | None = None
        self.wind_direction: str | None = None

        location_options = [
            discord.SelectOption(label=loc["name"], value=loc["name"])
            for loc in locations
        ]
        self.add_item(TrackingSelect("location",           placeholder="Select a location…",  options=location_options, row=0))
        self.add_item(TrackingSelect("board_type",         placeholder="Select board type…",   options=_BOARD_TYPES,     row=1))
        self.add_item(TrackingSelect("wind_speed_estimate",placeholder="Wind speed…",          options=_WIND_SPEEDS,     row=2))
        self.add_item(TrackingSelect("wind_direction",     placeholder="Wind direction…",       options=_WIND_DIRECTIONS, row=3))

    @discord.ui.button(label="Next →", style=discord.ButtonStyle.blurple, row=4)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Validate page 1 selections and transition to ``ConditionsView``.

        Sends an ephemeral error listing any unselected fields if the user
        clicks Next before completing all four dropdowns.  On success,
        edits the existing ephemeral message in place to show page 2.
        """
        missing = [
            name for name, val in (
                ("Location",       self.location),
                ("Board Type",     self.board_type),
                ("Wind Speed",     self.wind_speed_estimate),
                ("Wind Direction", self.wind_direction),
            )
            if val is None
        ]
        if missing:
            await interaction.response.send_message(
                f"Please select: {', '.join(missing)}",
                ephemeral=True,
            )
            return

        page1_data = {
            "location":            self.location,
            "board_type":          self.board_type,
            "wind_speed_estimate": self.wind_speed_estimate,
            "wind_direction":      self.wind_direction,
        }
        conditions_view = ConditionsView(page1_data)
        await interaction.response.edit_message(
            content="**Step 2 of 2** — Select conditions:",
            view=conditions_view,
        )
        # Store message ref so on_timeout can edit it
        conditions_view.message = interaction.message

    async def on_timeout(self):
        """Edit the ephemeral message to inform the user the form has expired."""
        if self.message:
            try:
                await self.message.edit(
                    content="This session form expired. Please run `/logsession` again.",
                    view=None,
                )
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class SessionCog(commands.Cog):
    """Cog containing all session-related slash commands.

    Commands:
        /logsession  — two-step Select Menu flow followed by a Modal.
        /mysessions  — ephemeral list of the caller's last 5 sessions.
        /leaderboard — public list of the top 5 sessions this month.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle cooldown and guild-check failures for all commands in this cog."""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Please wait {error.retry_after:.0f}s before logging another session.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "This command is not available here.",
                ephemeral=True,
            )

    @app_commands.command(name="logsession", description="Log a kiteboarding session.")
    @app_commands.checks.cooldown(rate=1, per=60.0)
    @app_commands.check(_guild_check)
    async def logsession(self, interaction: discord.Interaction):
        """Open the two-step session logging flow.

        Sends an ephemeral message containing ``SessionFlowView`` (page 1).
        The user progresses through page 2 and a Modal before the session
        is saved and a public embed is posted to ``#session-log``.
        """
        locations = await database.fetch_locations()
        view = SessionFlowView(locations)
        await interaction.response.send_message(
            "**Step 1 of 2** — Select your location and board setup:",
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

    @app_commands.command(name="mysessions", description="View your last 5 logged sessions.")
    @app_commands.check(_guild_check)
    async def mysessions(self, interaction: discord.Interaction):
        """Display the calling user's last 5 sessions as an ephemeral embed."""
        sessions = await database.fetch_user_sessions(str(interaction.user.id))
        if not sessions:
            await interaction.response.send_message(
                "You haven't logged any sessions yet. Use `/logsession` to add one.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(title="Your Last Sessions", color=0x3498DB)
        for s in sessions:
            rating = s["conditions_rating"]
            board = s["board_type"].replace("_", " ").title() if s["board_type"] else "—"
            embed.add_field(
                name=f"{_rating_emoji(rating)} {s['session_date']} — {s['location']}",
                value=f"{_fmt(s['wind_speed_estimate'])} kts | {rating}⭐ | {board}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top-rated sessions this month.")
    @app_commands.check(_guild_check)
    async def leaderboard(self, interaction: discord.Interaction):
        """Post a public embed of the top 5 sessions this calendar month."""
        sessions = await database.fetch_leaderboard()
        if not sessions:
            await interaction.response.send_message("No sessions logged this month yet.")
            return

        embed = discord.Embed(title="🏆 Top Sessions This Month", color=0xF39C12)
        for i, s in enumerate(sessions, start=1):
            rating = s["conditions_rating"]
            board = s["board_type"].replace("_", " ").title() if s["board_type"] else "—"
            embed.add_field(
                name=f"#{i} {s['discord_username']} — {s['location']} on {s['session_date']}",
                value=f"{rating}⭐ | {_fmt(s['wind_speed_estimate'])} kts | {board}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SessionCog(bot))
