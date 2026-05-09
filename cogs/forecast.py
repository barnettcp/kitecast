import zoneinfo
from datetime import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import SESSION_CHANNEL_ID

_PACIFIC = zoneinfo.ZoneInfo("America/Los_Angeles")
_POST_TIME = time(hour=20, minute=0, tzinfo=_PACIFIC)


class ForecastCog(commands.Cog):
    """Cog containing the daily forecast scheduler and on-demand forecast command.

    Phase 3 stub: the ``daily_forecast`` task fires at 20:00 US/Pacific
    each day and posts a placeholder embed to ``SESSION_CHANNEL_ID``.  The
    ``/forecast`` slash command also returns a placeholder response.

    Both will be replaced with real Open-Meteo + session-history logic
    in Phase 3.
    """

    def __init__(self, bot: commands.Bot):
        """Store the bot reference and start the daily scheduler loop."""
        self.bot = bot
        self.daily_forecast.start()

    def cog_unload(self):
        """Cancel the background task when the cog is unloaded."""
        self.daily_forecast.cancel()

    # -----------------------------------------------------------------------
    # Phase 3 stub — fires daily at 20:00 US/Pacific.
    # Replace the placeholder embed body with real forecast logic in Phase 3.
    # -----------------------------------------------------------------------

    @tasks.loop(time=_POST_TIME)
    async def daily_forecast(self):
        """Post the daily spots forecast embed to the session channel.

        **Phase 3 stub** — currently posts a placeholder message.
        In Phase 3, replace the embed body with:

        1. Fetch the 3-day wind forecast from the Open-Meteo Forecast API
           for each location in the ``locations`` table.
        2. Query historical sessions where ``conditions_rating >= 4`` and
           ``wind_speed_actual`` falls within the forecasted range.
        3. Rank locations by historical hit rate and post a summary embed.
        """
        channel = self.bot.get_channel(SESSION_CHANNEL_ID)
        if channel is None:
            return

        embed = discord.Embed(
            title="🪁 Spots for Tomorrow",
            description=(
                "Automated forecasts are coming in Phase 3!\n\n"
                "Once session history and wind/tide enrichment (Phase 2) are in place, "
                "this post will rank spots by predicted conditions."
            ),
            color=0x5DADE2,
        )
        embed.set_footer(text="PugetKite daily forecast — Phase 3 stub")
        await channel.send(embed=embed)

    @daily_forecast.before_loop
    async def before_forecast(self):
        """Wait until the bot is fully connected before starting the loop."""
        await self.bot.wait_until_ready()

    # -----------------------------------------------------------------------
    # /forecast — on-demand stub (Phase 3)
    # -----------------------------------------------------------------------

    @app_commands.command(
        name="forecast",
        description="On-demand spots outlook — coming in Phase 3.",
    )
    async def forecast(self, interaction: discord.Interaction):
        """Respond with a placeholder spots outlook embed.

        **Phase 3 stub** — will be replaced with a real on-demand forecast
        query once Phase 2 enrichment data is available.
        """
        embed = discord.Embed(
            title="🪁 Spots Outlook",
            description=(
                "Automated forecasts are not yet available — coming in Phase 3!\n\n"
                "In the meantime, check your local wind apps and log sessions "
                "with `/logsession` to help build the historical data."
            ),
            color=0x5DADE2,
        )
        embed.set_footer(text="PugetKite forecast — Phase 3 stub")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ForecastCog(bot))
