# `cogs/forecast.py`

**Purpose:** Contains the daily forecast scheduler and the `/forecast` slash command. Both are **Phase 3 stubs** — the infrastructure is in place and functional, but the content is placeholder until Phase 2 enrichment data is available.

---

## Phase Status

| Feature | Status |
|---|---|
| Daily scheduler (fires at 20:00 Pacific) | ✅ Active — posts placeholder embed |
| `/forecast` slash command | ✅ Active — returns placeholder embed |
| Real wind forecast logic | 🔲 Phase 3 |
| Spot ranking by historical conditions | 🔲 Phase 3 |

---

## Slash Command

### `/forecast`

Responds with an embed informing the user that automated forecasts are coming in Phase 3 and suggesting they log sessions in the meantime to build historical data.

The response is **public** (visible to the channel).

---

## Class: `ForecastCog`

The `commands.Cog` that owns the daily scheduler loop and the `/forecast` command. Loaded by `bot.py` at startup.

### `ForecastCog.__init__(bot)`

Stores the bot reference and starts the `daily_forecast` background task.

---

### `ForecastCog.cog_unload()`

Called automatically by discord.py when the cog is removed (e.g. during a hot-reload). Cancels the `daily_forecast` task to prevent it from running after the cog is gone.

---

### `ForecastCog.daily_forecast()`

A `@tasks.loop` that fires once per day at **20:00 US/Pacific** (handles daylight saving time automatically via `zoneinfo`). Posts a "Spots for Tomorrow" embed to `SESSION_CHANNEL_ID`.

**Phase 3 replacement plan** (documented in the source docstring):

1. Fetch the 3-day wind forecast from the [Open-Meteo Forecast API](https://open-meteo.com/) for each location in the `locations` table
2. Query `sessions` where `conditions_rating >= 4` and `wind_speed_actual` falls within the forecasted range
3. Rank locations by historical hit rate under similar wind conditions
4. Post a ranked embed titled "🪁 Spots for Tomorrow" with forecast wind and a confidence indicator

---

### `ForecastCog.before_forecast()`

A `@daily_forecast.before_loop` hook. Calls `await self.bot.wait_until_ready()` to ensure the bot is fully connected and its internal channel cache is populated before the task attempts to resolve `SESSION_CHANNEL_ID`.

---

### `ForecastCog.forecast(interaction)`

The `/forecast` slash command handler. Posts the Phase 3 placeholder embed.

---

## Scheduler Details

| Setting | Value |
|---|---|
| Fire time | 20:00 US/Pacific daily |
| Timezone handling | `zoneinfo.ZoneInfo("America/Los_Angeles")` — DST-aware |
| Target channel | `SESSION_CHANNEL_ID` from `config.py` |
| Graceful no-op | If the channel cannot be resolved, the task exits silently for that day |

---

## See Also

- [index.md](index.md) — Phase 3 roadmap summary
- [database.md](database.md) — `sessions` table columns that Phase 3 will query (`wind_speed_actual`, `conditions_rating`)
- [config.md](config.md) — `SESSION_CHANNEL_ID`
