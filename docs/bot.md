# `bot.py`

**Purpose:** Entry point for the bot. Defines the `KiteBot` class, loads all cogs, syncs slash commands to the Discord guild, and initialises the database on startup.

Run with:

```bash
python bot.py
```

---

## Class: `KiteBot`

Subclasses `discord.ext.commands.Bot`. Uses slash commands only — `command_prefix` is set to `None` so no prefix-based commands are registered.

### `KiteBot.__init__()`

Configures `discord.Intents.default()` and calls the parent `Bot.__init__`. No privileged intents (e.g. message content, server members) are required for Phase 1 slash command operation.

---

### `KiteBot.setup_hook()`

Called automatically by discord.py before the bot connects to the gateway. Responsible for two things:

1. **Loading cogs** — iterates over the `COGS` list and calls `load_extension()` for each. Cogs register their slash commands with the global command tree at load time.
2. **Syncing commands to the guild** — copies global commands to the development guild and calls `tree.sync(guild=...)` for instant registration. Guild-scoped syncs take effect immediately; global syncs can take up to one hour.

> **Production note:** Before going fully public, remove the `copy_global_to` and guild-scoped `sync` calls and replace with a single `await self.tree.sync()` (no guild argument) to register commands globally.

---

### `KiteBot.on_ready()`

Fired by discord.py once the bot is fully connected and its internal cache is populated. Calls `init_db()` to create tables and seed locations if this is the first run. Prints startup info to stdout (picked up by systemd's journal in production).

---

## Function: `main()`

The async entry point. Creates a `KiteBot` instance using `async with` to ensure aiohttp sessions and other internal resources are cleaned up on shutdown. Calls `bot.start(DISCORD_TOKEN)` to connect to Discord.

Called by the `if __name__ == "__main__"` guard via `asyncio.run(main())`.

---

## Module-Level: `COGS`

```python
COGS = [
    "cogs.session",
    "cogs.forecast",
]
```

The list of cog module paths loaded at startup. To add a new cog, create the file under `cogs/` and append its dotted module path here.

---

## See Also

- [session.md](session.md) — `cogs.session` cog
- [forecast.md](forecast.md) — `cogs.forecast` cog
- [database.md](database.md) — `init_db()` called from `on_ready`
- [config.md](config.md) — `DISCORD_TOKEN` and `GUILD_ID` used here
