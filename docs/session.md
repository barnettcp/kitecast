# `cogs/session.py`

**Purpose:** Implements all three Phase 1 session-related slash commands: `/logsession`, `/mysessions`, and `/leaderboard`. Also contains the Views, Modal, and helper functions that support the logging flow.

---

## Slash Commands

### `/logsession`

Opens a two-step ephemeral flow for logging a kiteboarding session. The response is only visible to the user who ran the command.

**Flow:**

```
Step 1 — SessionFlowView (ephemeral message)
  Dropdowns: Location, Board Type, Wind Speed, Wind Direction
  Button: [Next →]

Step 2 — ConditionsView (same ephemeral message, edited in place)
  Dropdowns: Tide State, Beginner Friendly, Conditions Rating
  Button: [Open Session Form →]

Step 3 — SessionModal (Discord modal overlay)
  Text inputs: Date, Time, Duration, Kite Size, Notes
  Button: [Submit]
      ↓
  Saves to database
  Posts embed to #session-log
  Sends ephemeral "Session logged! ✅" confirmation
```

Both Views expire after 3 minutes. If the user takes too long, the ephemeral message is edited to explain the timeout and prompt them to run `/logsession` again.

---

### `/mysessions`

Returns an ephemeral embed showing the calling user's last 5 sessions, ordered by date (most recent first). If the user has no sessions, an ephemeral prompt to use `/logsession` is shown instead.

**Embed format (one field per session):**
```
🟢 2026-05-09 — Magnuson Park
15-20 kts | 5⭐ | Twin Tip
```

---

### `/leaderboard`

Posts a **public** embed listing the 5 highest-rated sessions in the current calendar month, ordered by `conditions_rating` descending. Visible to everyone in the channel.

**Embed format (one field per session):**
```
#1 chris — Magnuson Park on 2026-05-09
5⭐ | 15-20 kts | Twin Tip
```

---

## Classes

### `TrackingSelect`

Inherits from `discord.ui.Select`. A reusable dropdown that writes the user's selection back to the parent View as an attribute.

**Why it exists:** Discord limits a View to 5 ActionRows. With 7 dropdowns needed across the logging flow, the selects are split across two Views (4 on page 1, 3 on page 2). Each `TrackingSelect` knows the name of the attribute it should update on the parent View (`attr_name`), keeping the callback logic generic and avoiding seven separate subclasses.

| Method | Description |
|---|---|
| `__init__(attr_name, **kwargs)` | Stores `attr_name`; passes remaining kwargs to `discord.ui.Select` |
| `callback(interaction)` | Calls `setattr(self.view, self.attr_name, self.values[0])` and defers the interaction |

---

### `SessionModal`

Inherits from `discord.ui.Modal`. Presents the five text-input fields of the logging flow. Receives all dropdown selections from the preceding Views via the `select_data` dictionary passed to `__init__`.

**Text inputs:**

| Field | Required | Validation |
|---|---|---|
| Session Date | Yes | Must match `YYYY-MM-DD`; pre-filled with today's UTC date |
| Session Start Time | No | Free text; stored as-is |
| Duration (minutes) | No | Must be a whole number if provided |
| Kite Size (m²) | No | Must be a decimal number if provided |
| Notes | No | Up to 1,000 characters; paragraph style |

| Method | Description |
|---|---|
| `__init__(select_data)` | Pre-fills today's date; stores `select_data` for use at submit time |
| `on_submit(interaction)` | Validates inputs, builds the data dict, calls `database.insert_session()`, builds and posts the session embed, sends ephemeral confirmation |
| `on_error(interaction, error)` | Catches unexpected exceptions and sends an ephemeral error message |

---

### `ConditionsView`

Page 2 of the `/logsession` flow. Presents three dropdowns (tide state, beginner-friendly, conditions rating) and the "Open Session Form →" button.

| Method | Description |
|---|---|
| `__init__(page1_data)` | Stores page 1 selections; adds the three `TrackingSelect` items and the submit button |
| `open_form(interaction, button)` | Validates all three dropdowns are selected, merges with `page1_data`, opens `SessionModal` |
| `on_timeout()` | Edits the ephemeral message to inform the user the form has expired |

---

### `SessionFlowView`

Page 1 of the `/logsession` flow. Presents four dropdowns (location, board type, wind speed, wind direction) and the "Next →" button.

Location options are loaded dynamically from the `locations` table at command invocation time, so adding a new spot via database `INSERT` will make it appear in the dropdown without any code change.

| Method | Description |
|---|---|
| `__init__(locations)` | Builds location `SelectOption` list from the database rows; adds four `TrackingSelect` items and the Next button |
| `next_page(interaction, button)` | Validates all four dropdowns are selected; edits the ephemeral message in place to show `ConditionsView` |
| `on_timeout()` | Edits the ephemeral message to inform the user the form has expired |

---

### `SessionCog`

The `commands.Cog` that registers all three slash commands with the bot's command tree. Loaded by `bot.py` at startup.

| Method | Description |
|---|---|
| `__init__(bot)` | Stores the bot reference |
| `logsession(interaction)` | Fetches locations, creates `SessionFlowView`, sends ephemeral page 1 |
| `mysessions(interaction)` | Fetches user's last 5 sessions, renders ephemeral embed or empty-state message |
| `leaderboard(interaction)` | Fetches top 5 sessions this month, renders public embed or empty-state message |

---

## Helper Functions

### `_rating_emoji(rating)`

Returns a coloured circle emoji for a given `conditions_rating` integer:
- 🟢 for 4–5 (good/excellent)
- 🟡 for 3 (average)
- 🔴 for 1–2 (poor/below average)

Used in the session embed title and in `/mysessions` field names.

---

### `_rating_color(rating)`

Returns the Discord embed hex colour for a given rating:
- `0x2ECC71` (green) for 4–5
- `0xF1C40F` (yellow) for 3
- `0xE74C3C` (red) for 1–2

---

### `_fmt(value, fallback="—")`

Returns `value` if truthy, otherwise `fallback`. Used to display optional session fields as an em-dash when the user left them blank.

---

## Session Embed Format

Posted publicly to `SESSION_CHANNEL_ID` after a successful submission.

| Element | Content |
|---|---|
| Title | `🟢/🟡/🔴 Session at [Location] — logged by [username]` |
| Color | Green / Yellow / Red based on rating |
| Inline fields (row 1) | Date, Time, Duration |
| Inline fields (row 2) | Rating, Wind Speed, Wind Direction |
| Inline fields (row 3) | Tide State, Board Type, Kite Size |
| Inline fields (row 4) | Beginner Friendly |
| Notes field (full-width) | Only included if the user provided notes |
| Footer | `Logged at YYYY-MM-DD HH:MM UTC` |

---

## See Also

- [database.md](database.md) — `insert_session`, `fetch_user_sessions`, `fetch_leaderboard`, `fetch_locations`
- [config.md](config.md) — `SESSION_CHANNEL_ID`
- [index.md](index.md) — overview of the full interaction flow diagram
