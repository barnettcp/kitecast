import os

import aiosqlite

from config import DB_PATH

# Seed data for locations table. Drano Lake has no NOAA station (freshwater lake;
# tides are not applicable). noaa_station_id is NULL for this location. Phase 2
# enrichment must check `noaa_station_id IS NULL` and skip NOAA calls for it.
_LOCATIONS = [
    ("Magnuson Park",       "Seattle",        47.6814, -122.2538, "9447130"),
    ("Cama Beach",          "Camano Island",  48.1304, -122.5076, "9448576"),
    ("Howarth Park",        "Everett",        47.9879, -122.2443, "9447130"),
    ("Point Hudson",        "Port Townsend",  48.1135, -122.7598, "9444900"),
    ("Titlow Beach",        "Tacoma",         47.2557, -122.5419, "9446484"),
    ("Kopachuck State Park","Gig Harbor",     47.3301, -122.6577, "9446484"),
    ("Larrabee State Park", "Bellingham",     48.6549, -122.4887, "9449880"),
    ("Drano Lake",          "Columbia Gorge", 45.7143, -121.7376, None),
]


async def init_db() -> None:
    """Initialise the SQLite database.

    Creates the ``sessions`` and ``locations`` tables if they do not already
    exist, and seeds the ``locations`` table with the approved spot list on
    the first run (detected by an empty table).  Safe to call on every
    startup — all DDL statements use ``CREATE TABLE IF NOT EXISTS``.

    The ``data/`` directory is created automatically if it does not exist.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id                    INTEGER PRIMARY KEY,
                discord_user_id       TEXT    NOT NULL,
                discord_username      TEXT    NOT NULL,
                location              TEXT    NOT NULL,
                session_date          TEXT    NOT NULL,
                session_time          TEXT,
                duration_minutes      INTEGER,
                kite_size_m           REAL,
                board_type            TEXT,
                wind_speed_estimate   TEXT,
                wind_direction        TEXT,
                tide_state            TEXT,
                beginner_friendly     TEXT,
                conditions_rating     INTEGER,
                notes                 TEXT,
                logged_at             TEXT    NOT NULL,
                wind_speed_actual     REAL,
                wind_direction_actual TEXT,
                tide_height_m         REAL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id              INTEGER PRIMARY KEY,
                name            TEXT    NOT NULL UNIQUE,
                region          TEXT,
                latitude        REAL    NOT NULL,
                longitude       REAL    NOT NULL,
                noaa_station_id TEXT
            )
        """)

        # Seed only on first run
        async with db.execute("SELECT COUNT(*) FROM locations") as cursor:
            (count,) = await cursor.fetchone()

        if count == 0:
            await db.executemany(
                """
                INSERT INTO locations (name, region, latitude, longitude, noaa_station_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                _LOCATIONS,
            )

        await db.commit()


async def insert_session(data: dict) -> int:
    """Insert a new session record and return its auto-assigned ID.

    Args:
        data: A dictionary whose keys match the Phase 1 column names of the
            ``sessions`` table.  The Phase 2 enrichment columns
            (``wind_speed_actual``, ``wind_direction_actual``,
            ``tide_height_m``) are intentionally omitted here and default to
            NULL; they are populated later via UPDATE.

    Returns:
        The ``rowid`` / ``id`` of the newly inserted row.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO sessions (
                discord_user_id, discord_username, location, session_date,
                session_time, duration_minutes, kite_size_m, board_type,
                wind_speed_estimate, wind_direction, tide_state,
                beginner_friendly, conditions_rating, notes, logged_at
            ) VALUES (
                :discord_user_id, :discord_username, :location, :session_date,
                :session_time, :duration_minutes, :kite_size_m, :board_type,
                :wind_speed_estimate, :wind_direction, :tide_state,
                :beginner_friendly, :conditions_rating, :notes, :logged_at
            )
            """,
            data,
        )
        await db.commit()
        return cursor.lastrowid


async def fetch_user_sessions(discord_user_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent sessions logged by a specific user.

    Results are ordered by ``session_date`` descending, then by
    ``logged_at`` descending as a tiebreaker, so the most recent session
    always appears first.

    Args:
        discord_user_id: The Discord snowflake ID (as a string) of the user.
        limit: Maximum number of rows to return.  Defaults to 5.

    Returns:
        A list of session rows as plain dictionaries, newest first.
        Returns an empty list if the user has no sessions.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM sessions
            WHERE discord_user_id = ?
            ORDER BY session_date DESC, logged_at DESC
            LIMIT ?
            """,
            (discord_user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def fetch_leaderboard(limit: int = 5) -> list[dict]:
    """Return the top-rated sessions in the current calendar month.

    Filters to sessions whose ``session_date`` falls in the current
    ``YYYY-MM`` period, then orders by ``conditions_rating`` descending
    with ``logged_at`` as a tiebreaker.

    Args:
        limit: Maximum number of rows to return.  Defaults to 5.

    Returns:
        A list of session rows as plain dictionaries, highest-rated first.
        Returns an empty list if no sessions have been logged this month.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM sessions
            WHERE strftime('%Y-%m', session_date) = strftime('%Y-%m', 'now')
            ORDER BY conditions_rating DESC, logged_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def fetch_locations() -> list[dict]:
    """Return all approved kite spots from the ``locations`` table.

    Results are ordered alphabetically by name, which is also the order
    they appear in the ``/logsession`` location dropdown.

    Returns:
        A list of location rows as plain dictionaries.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM locations ORDER BY name") as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]
