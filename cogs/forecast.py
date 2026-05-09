import zoneinfo
from datetime import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import SESSION_CHANNEL_ID

_PACIFIC = zoneinfo.ZoneInfo("America/Los_Angeles")
_POST_TIME = time(hour=20, minute=0, tzinfo=_PACIFIC)


class ForecastCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_forecast.start()

    def cog_unload(self):
        self.daily_forecast.cancel()

    # -----------------------------------------------------------------------
    # Phase 3 stub — fires daily at 20:00 US/Pacific.
    # Replace the placeholder embed body with real forecast logic in Phase 3.
    # -----------------------------------------------------------------------

    @tasks.loop(time=_POST_TIME)
    async def daily_forecast(self):
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
        await self.bot.wait_until_ready()

    # -----------------------------------------------------------------------
    # /forecast — on-demand stub (Phase 3)
    # -----------------------------------------------------------------------

    @app_commands.command(
        name="forecast",
        description="On-demand spots outlook — coming in Phase 3.",
    )
    async def forecast(self, interaction: discord.Interaction):
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
