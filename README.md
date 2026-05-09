# PugetKite Discord Bot

A Discord bot for the Puget Sound kiteboarding community. Members log sessions via slash commands, building a structured dataset of conditions, locations, and ratings. Future phases will use that history to generate automated daily spot forecasts.

---

## Features (Phase 1)

- **`/logsession`** — two-step flow (dropdowns → text form) to log a session with location, wind, tide, board setup, and a conditions rating. Posts a formatted embed to `#session-log`.
- **`/mysessions`** — shows your last 5 logged sessions (visible only to you).
- **`/leaderboard`** — shows the top 5 highest-rated sessions this calendar month.
- **`/forecast`** — placeholder for the Phase 3 automated forecast.

## Planned Phases

| Phase | Description |
|---|---|
| **Phase 2** | Enrich sessions with historical wind (Open-Meteo) and tide (NOAA) data at log time |
| **Phase 3** | Daily automated forecast post ranking spots by predicted conditions |

---

## Stack

- **Python 3.12** / [discord.py 2.x](https://discordpy.readthedocs.io/)
- **SQLite** via [aiosqlite](https://aiosqlite.omnilib.dev/) — zero-infrastructure, Postgres-compatible schema for easy future migration
- **uv** for dependency and virtual environment management
- **systemd** on a DigitalOcean Ubuntu droplet for production deployment

---

## Local Development Setup

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/) installed.

```bash
git clone https://github.com/barnettcp/kitecast.git
cd kitecast

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Configure secrets
cp .env.example .env
# Edit .env and fill in DISCORD_TOKEN, SESSION_CHANNEL_ID, GUILD_ID, DB_PATH
```

Set `DB_PATH=data/kitebot.db` in `.env` for local development.

```bash
python bot.py
```

On first run, the bot creates the SQLite database and seeds the locations table automatically.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Bot token from the Discord Developer Portal |
| `SESSION_CHANNEL_ID` | Channel ID for `#session-log` |
| `GUILD_ID` | Server ID — used to sync slash commands instantly during development |
| `DB_PATH` | Path to the SQLite file, e.g. `data/kitebot.db` |

---

## Project Structure

```
kitecast/
  bot.py              # Entry point: loads cogs, initialises DB, connects to Discord
  config.py           # Loads and validates environment variables
  database.py         # Async SQLite helpers (init, insert, fetch)
  cogs/
    session.py        # /logsession, /mysessions, /leaderboard
    forecast.py       # /forecast and daily scheduler (Phase 3 stub)
  data/               # SQLite database lives here (gitignored)
  deploy/
    kitebot.service   # systemd unit file for production
  requirements.txt
  .env.example
```

---

## Deployment

See [`deploy/kitebot.service`](deploy/kitebot.service) for the systemd unit file. The bot is designed to run on a $6/mo DigitalOcean Ubuntu droplet under a non-root user with systemd managing restarts.

**Discord Developer Portal setup:**
1. Create a new application at <https://discord.com/developers/applications>
2. Under **Bot**, add a bot and copy the token → `DISCORD_TOKEN` in `.env`
3. Enable **Server Members Intent** and **Message Content Intent**
4. Under **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`; permissions: Send Messages, Embed Links, Use Slash Commands, Read Message History
5. Add the bot to your server using the generated URL
6. Copy the `#session-log` channel ID → `SESSION_CHANNEL_ID`; copy the server ID → `GUILD_ID`

**Supabase migration path (when ready):**
1. Export: `sqlite3 data/kitebot.db .dump > dump.sql`
2. Replace `aiosqlite` with `asyncpg` in `database.py`
3. Update `DB_PATH` to a Supabase/Postgres connection string — no schema changes needed

---

## AI Disclaimer on Development Approach

This project was built with significant assistance from GitHub Copilot (AI pair programming). The architecture, data model, and implementation decisions were designed and reviewed by the author; AI tooling was used to accelerate code generation and catch issues early. The intent is a bot that works correctly and is maintainable — AI assistance was a means to that end, not a shortcut around understanding the code.
