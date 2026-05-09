import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill in all values."
        )
    return value


DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
SESSION_CHANNEL_ID: int = int(_require("SESSION_CHANNEL_ID"))
GUILD_ID: int = int(_require("GUILD_ID"))
DB_PATH: str = _require("DB_PATH")
