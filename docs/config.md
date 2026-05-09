# `config.py`

**Purpose:** Loads all required environment variables at import time and exposes them as typed module-level constants. Any missing variable raises an error immediately at startup rather than failing silently later.

---

## How It Works

On import, `config.py` calls `load_dotenv()` to read values from the `.env` file in the project root into `os.environ`. It then calls `_require()` for each expected variable. If any variable is absent or empty, the bot will not start and a clear error message is printed.

---

## Functions

### `_require(name)`

| | |
|---|---|
| **Signature** | `_require(name: str) -> str` |
| **Access** | Private (prefixed `_`; not intended to be called from other modules) |

Reads `name` from `os.environ`. If the value is missing or an empty string, raises a `ValueError` with a message telling the user to copy `.env.example` to `.env` and fill in the missing value.

---

## Module-Level Constants

These are set once at import time. All other modules import from here rather than reading `os.environ` directly.

| Constant | Type | Source Variable | Description |
|---|---|---|---|
| `DISCORD_TOKEN` | `str` | `DISCORD_TOKEN` | Bot authentication token from the Discord Developer Portal |
| `SESSION_CHANNEL_ID` | `int` | `SESSION_CHANNEL_ID` | Channel ID for `#session-log`; cast to `int` because discord.py expects integer snowflake IDs |
| `GUILD_ID` | `int` | `GUILD_ID` | Server (guild) ID; used to sync slash commands instantly during development |
| `DB_PATH` | `str` | `DB_PATH` | Filesystem path to the SQLite database file (e.g. `data/kitebot.db`) |

---

## Environment Variable Reference

See `.env.example` in the repo root for a ready-to-copy template.

| Variable | Example Value | Notes |
|---|---|---|
| `DISCORD_TOKEN` | `MTExxx...` | From Discord Developer Portal → Bot → Token |
| `SESSION_CHANNEL_ID` | `1234567890123456789` | Right-click `#session-log` → Copy Channel ID |
| `GUILD_ID` | `9876543210987654321` | Right-click server icon → Copy Server ID |
| `DB_PATH` | `data/kitebot.db` | Use a relative path for local dev; absolute path on the server |

---

## See Also

- [bot.md](bot.md) — imports `DISCORD_TOKEN` and `GUILD_ID`
- [database.md](database.md) — imports `DB_PATH`
- [session.md](session.md) — imports `SESSION_CHANNEL_ID`
- [forecast.md](forecast.md) — imports `SESSION_CHANNEL_ID`
