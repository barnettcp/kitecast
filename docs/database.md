# `database.py`

**Purpose:** All SQLite interaction lives here. Provides async functions for initialising the schema, seeding reference data, inserting session records, and querying sessions for the bot's slash commands. No other module talks to the database directly.

Uses [aiosqlite](https://aiosqlite.omnilib.dev/) — a thin async wrapper around the standard `sqlite3` library — so all queries are compatible with discord.py's async event loop.

---

## Schema

### `sessions` Table

Stores every logged kiteboarding session. The schema avoids SQLite-specific types so it can be migrated to Postgres/Supabase without changes.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY | Yes | Auto-increment session ID |
| `discord_user_id` | TEXT | Yes | Discord snowflake ID — stable even if the username changes |
| `discord_username` | TEXT | Yes | Display name at time of logging |
| `location` | TEXT | Yes | Spot name, selected from the `locations` table |
| `session_date` | TEXT | Yes | ISO 8601 date: `YYYY-MM-DD` |
| `session_time` | TEXT | No | Session start time, e.g. `14:30` |
| `duration_minutes` | INTEGER | No | Estimated session length in minutes |
| `kite_size_m` | REAL | No | Kite size in square metres, e.g. `12.0` |
| `board_type` | TEXT | No | One of: `twin_tip`, `directional`, `foil` |
| `wind_speed_estimate` | TEXT | No | Knot range reported by the rider: `10-15`, `15-20`, `20-25`, `25+` |
| `wind_direction` | TEXT | No | Cardinal direction: `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW` |
| `tide_state` | TEXT | No | One of: `incoming`, `outgoing`, `high`, `low`, `slack` |
| `beginner_friendly` | TEXT | No | One of: `yes`, `with_supervision`, `no` |
| `conditions_rating` | INTEGER | No | 1 (poor) to 5 (excellent) |
| `notes` | TEXT | No | Free-text observations |
| `logged_at` | TEXT | Yes | UTC timestamp of when the record was inserted (`YYYY-MM-DD HH:MM:SS`) |
| `wind_speed_actual` | REAL | No | **Phase 2:** filled from Open-Meteo API (knots) |
| `wind_direction_actual` | TEXT | No | **Phase 2:** filled from Open-Meteo API |
| `tide_height_m` | REAL | No | **Phase 2:** filled from NOAA Tides API (metres) |

> The three Phase 2 columns are nullable in Phase 1. They exist now so Phase 2 enrichment can populate them with `UPDATE` statements — no schema migration required.

---

### `locations` Table

Approved kite spots. Seeded automatically on first run. New spots can be added with a direct `INSERT`.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY | Yes | Auto-increment |
| `name` | TEXT UNIQUE | Yes | Display name shown in the `/logsession` dropdown |
| `region` | TEXT | No | Sub-region label (e.g. `Seattle`, `Bellingham`) |
| `latitude` | REAL | Yes | Used for Open-Meteo API calls in Phase 2 |
| `longitude` | REAL | Yes | Used for Open-Meteo API calls in Phase 2 |
| `noaa_station_id` | TEXT | No | Nearest NOAA tide station ID; `NULL` for locations without one |

#### Seeded Locations

| Name | Region | NOAA Station |
|---|---|---|
| Magnuson Park | Seattle | 9447130 |
| Cama Beach | Camano Island | 9448576 |
| Howarth Park | Everett | 9447130 |
| Point Hudson | Port Townsend | 9444900 |
| Titlow Beach | Tacoma | 9446484 |
| Kopachuck State Park | Gig Harbor | 9446484 |
| Larrabee State Park | Bellingham | 9449880 |
| Drano Lake | Columbia Gorge | `NULL` |

> **Drano Lake note:** Drano Lake is a freshwater lake on the Columbia River — tides are not applicable and `tide_height_m` will always be `NULL` for this location. Phase 2 enrichment must skip the NOAA API call when `noaa_station_id IS NULL`. See `noaa_station_id` column description above.

---

## Functions

### `init_db()`

| | |
|---|---|
| **Signature** | `async init_db() -> None` |
| **Called from** | `bot.py` → `KiteBot.on_ready()` |

Creates the `sessions` and `locations` tables if they do not already exist (`CREATE TABLE IF NOT EXISTS`), then seeds the locations table on first run. Detects first run by checking `COUNT(*) = 0` on the locations table before inserting. Creates the `data/` directory automatically if it is missing. Safe to call on every startup.

---

### `insert_session(data)`

| | |
|---|---|
| **Signature** | `async insert_session(data: dict) -> int` |
| **Called from** | `cogs/session.py` → `SessionModal.on_submit()` |

Inserts one row into the `sessions` table. The `data` dictionary keys must match the Phase 1 column names. Phase 2 enrichment columns (`wind_speed_actual`, `wind_direction_actual`, `tide_height_m`) are not included — they default to `NULL` and will be populated later via `UPDATE`.

**Returns:** The auto-assigned integer `id` of the new row.

---

### `fetch_user_sessions(discord_user_id, limit=5)`

| | |
|---|---|
| **Signature** | `async fetch_user_sessions(discord_user_id: str, limit: int = 5) -> list[dict]` |
| **Called from** | `cogs/session.py` → `SessionCog.mysessions()` |

Returns up to `limit` sessions for the given user, ordered by `session_date DESC`, then `logged_at DESC`. Returns an empty list if the user has no sessions.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `discord_user_id` | `str` | required | Discord snowflake ID as a string |
| `limit` | `int` | `5` | Maximum rows to return |

---

### `fetch_leaderboard(limit=5)`

| | |
|---|---|
| **Signature** | `async fetch_leaderboard(limit: int = 5) -> list[dict]` |
| **Called from** | `cogs/session.py` → `SessionCog.leaderboard()` |

Returns the top sessions in the current calendar month, filtered using SQLite's `strftime('%Y-%m', session_date) = strftime('%Y-%m', 'now')`. Ordered by `conditions_rating DESC`, with `logged_at DESC` as a tiebreaker. Returns an empty list if no sessions have been logged this month.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `limit` | `int` | `5` | Maximum rows to return |

---

### `fetch_locations()`

| | |
|---|---|
| **Signature** | `async fetch_locations() -> list[dict]` |
| **Called from** | `cogs/session.py` → `SessionCog.logsession()` |

Returns all rows from the `locations` table, ordered alphabetically by name. This is the same order in which locations appear in the `/logsession` dropdown. Adding a new location via `INSERT` will make it appear in the dropdown automatically on the next command invocation — no code change required.

---

## Supabase / Postgres Migration

The schema is intentionally written to be portable. When ready to migrate:

1. Export: `sqlite3 data/kitebot.db .dump > dump.sql`
2. Replace `aiosqlite` with `asyncpg` in this file
3. Update `DB_PATH` in `.env` to a Postgres connection string
4. No schema changes needed
