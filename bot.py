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
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)

        # Sync slash commands to the dev guild for instant registration.
        # Remove copy_global_to / guild sync before production if you want
        # global commands (they take up to 1 hour to propagate).
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        await init_db()
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Commands synced to guild {GUILD_ID}")
        print("Database initialised.")


async def main():
    async with KiteBot() as bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
