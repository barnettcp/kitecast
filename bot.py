import asyncio

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID
from database import init_db

COGS = [
    "cogs.session",
    "cogs.forecast",
]


class KiteBot(commands.Bot):
    """The PugetKite Discord bot.

    Subclasses ``commands.Bot`` to use slash commands only (no prefix
    commands).  Cogs are loaded in ``setup_hook`` so they are registered
    before the bot connects to the gateway.
    """

    def __init__(self):
        """Configure intents and initialise the base Bot."""
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)

    async def setup_hook(self):
        """Load all cogs and sync slash commands to the development guild.

        Guild-scoped sync is used during development because it takes effect
        instantly.  For production with global commands, remove the
        ``copy_global_to`` and guild-scoped ``sync`` calls and run a single
        global sync instead (propagation takes up to one hour).
        """
        for cog in COGS:
            await self.load_extension(cog)

        # Sync slash commands to the dev guild for instant registration.
        # Remove copy_global_to / guild sync before production if you want
        # global commands (they take up to 1 hour to propagate).
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        """Initialise the database and log startup information to stdout.

        Called by discord.py once the bot has connected and its internal
        cache is populated.  ``init_db()`` is safe to call here on every
        startup — it is idempotent.
        """
        await init_db()
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Commands synced to guild {GUILD_ID}")
        print("Database initialised.")


async def main():
    """Entry point: create and run the bot within an async context manager.

    Using ``async with KiteBot()`` ensures the aiohttp session and other
    internal resources are properly cleaned up on shutdown.
    """
    async with KiteBot() as bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
