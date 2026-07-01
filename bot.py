"""
Main bot entrypoint for Warhammer 40k match tracker.
Run this file to start the bot.
"""
from pathlib import Path
import os
import logging
import discord
from discord.ext import commands


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()
TOKEN = os.getenv("DISCORD_TOKEN")
APP_ID = os.getenv("APPLICATION_ID")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in environment or .env file")

APP_ID = int(APP_ID) if APP_ID else None

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True


class War40kBot(commands.Bot):
    """Custom Bot to perform async setup before connecting."""

    def __init__(self):
        super().__init__(command_prefix="/", intents=intents, application_id=APP_ID)

    async def setup_hook(self) -> None:
        try:
            from database import Database
        except Exception:
            logging.exception("Failed to import Database in setup_hook")
            raise

        try:
            import importlib

            mod = importlib.import_module("cogs.commands")
            logging.info("Imported cogs.commands: %s", mod)
            if not hasattr(mod, "MatchCog"):
                available = [k for k in dir(mod) if not k.startswith("__")]
                logging.error("cogs.commands missing MatchCog; available: %s", available)
                raise ImportError("MatchCog not found in cogs.commands")
            MatchCog = getattr(mod, "MatchCog")
        except Exception:
            logging.exception("Failed to import MatchCog from cogs.commands")
            raise

        try:
            self.db = Database()
            await self.db.connect()
            cog = MatchCog(self, self.db)
            await self.add_cog(cog)

            try:
                dev_guild = os.getenv("DEV_GUILD_ID")
                if dev_guild:
                    synced = await self.tree.sync(guild=discord.Object(id=int(dev_guild)))
                    logging.info("Synced %d commands to dev guild %s", len(synced), dev_guild)
                    for c in synced:
                        logging.debug("  command: %s", getattr(c, "name", repr(c)))
                else:
                    synced = await self.tree.sync()
                    logging.info("Globally synced %d commands", len(synced))
                    for c in synced:
                        logging.debug("  command: %s", getattr(c, "name", repr(c)))
            except Exception:
                logging.exception("Failed to sync commands")
        except Exception:
            logging.exception("Error during setup_hook")


bot = War40kBot()


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logging.info("------")
    try:
        cmds = [c.name for c in bot.tree.get_commands()]
        logging.info("Tree commands: %s", cmds)
        dev_guild = os.getenv("DEV_GUILD_ID")
        if dev_guild:
            guild_cmds = await bot.tree.fetch_commands(guild=discord.Object(id=int(dev_guild)))
            logging.info("Guild (%s) commands: %s", dev_guild, [c.name for c in guild_cmds])
    except Exception:
        logging.exception("Failed to list commands on_ready")


if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception:
        logging.exception("Bot failed to start")