# PugetKite Bot — Developer Docs

This folder documents the Python modules that make up the PugetKite Discord bot. Each file below corresponds to a source file in the repo root or the `cogs/` package.

---

## Module Index

| File | Source | Purpose |
|---|---|---|
| [config.md](config.md) | `config.py` | Environment variable loading and validation |
| [database.md](database.md) | `database.py` | SQLite schema, initialisation, and all data access functions |
| [bot.md](bot.md) | `bot.py` | Bot entry point, cog loading, command sync |
| [session.md](session.md) | `cogs/session.py` | `/logsession`, `/mysessions`, `/leaderboard` — all session commands |
| [forecast.md](forecast.md) | `cogs/forecast.py` | Daily forecast scheduler and `/forecast` command (Phase 3 stub) |

---

## Architecture Overview

The bot is built with **discord.py 2.x** using slash commands only (no prefix commands). Logic is organised into *cogs* — self-contained modules that group related commands and event listeners. The bot loads each cog at startup, syncs slash commands to the Discord guild, then initialises the database.

```
bot.py
  └── loads cogs/session.py     → /logsession, /mysessions, /leaderboard
  └── loads cogs/forecast.py    → /forecast, daily scheduler
  └── calls database.init_db()  → creates tables, seeds locations
```

### Interaction Flow for `/logsession`

Discord modals only accept text inputs (max 5), so dropdown menus must be collected before the modal opens. The flow uses two sequential Views followed by a Modal:

```
/logsession
  │
  ├── SessionFlowView (Page 1)
  │     Location, Board Type, Wind Speed, Wind Direction
  │     [Next →]
  │
  ├── ConditionsView (Page 2)
  │     Tide State, Beginner Friendly, Conditions Rating
  │     [Open Session Form →]
  │
  └── SessionModal
        Date, Time, Duration, Kite Size, Notes
        [Submit]  →  saves to DB  →  posts embed to #session-log
```

Both Views time out after 3 minutes (Discord's default) and edit the ephemeral message to prompt the user to start over.

---

## Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Complete | Session logging, `/mysessions`, `/leaderboard` |
| Phase 2 | 🔲 Planned | Enrich sessions with real wind (Open-Meteo) and tide (NOAA) data |
| Phase 3 | 🔲 Planned | Daily automated forecast post ranking spots by predicted conditions |

Phase 2 enrichment columns (`wind_speed_actual`, `wind_direction_actual`, `tide_height_m`) are already present in the `sessions` table as nullable columns, ready to be populated without a schema migration.
