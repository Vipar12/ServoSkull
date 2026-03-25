"""
Main bot entrypoint for Warhammer 40k match tracker.
Run this file to start the bot.
"""
import os
from dotenv import load_dotenv
import logging
import discord
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
APP_ID = os.getenv("APPLICATION_ID")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in .env file")

# ensure application_id is int or None
APP_ID = int(APP_ID) if APP_ID else None

# enable logging so startup errors are visible
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True


class War40kBot(commands.Bot):
    """Custom Bot to perform async setup before connecting."""
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents, application_id=APP_ID)

    async def setup_hook(self) -> None:
        # Called before the bot connects to Discord. Create DB and load cogs here.
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
            # ensure any app_commands defined on the cog class are added to the tree
            try:
                from discord import app_commands as _app_commands
                import inspect
                dev_guild = os.getenv("DEV_GUILD_ID")
                guild_obj = discord.Object(id=int(dev_guild)) if dev_guild else None
                for name in dir(MatchCog):
                    attr = getattr(MatchCog, name)
                    if isinstance(attr, _app_commands.Command):
                        try:
                            # get bound command from instance
                            bound = getattr(cog, name)
                            if guild_obj:
                                self.tree.add_command(bound, guild=guild_obj)
                            else:
                                self.tree.add_command(bound)
                            logging.info("Added app command %s to tree", name)
                        except Exception:
                            logging.exception("Failed to add app command %s", name)
            except Exception:
                logging.exception("Failed to register cog app commands to tree")
            # Sync application commands to Discord
            try:
                dev_guild = os.getenv("DEV_GUILD_ID")
                if dev_guild:
                    # register commands instantly in a single development guild
                        synced = await self.tree.sync(guild=discord.Object(id=int(dev_guild)))
                        logging.info("Synced %d commands to dev guild %s", len(synced), dev_guild)
                        for c in synced:
                            logging.debug("  command: %s", getattr(c, 'name', repr(c)))
                else:
                    # global sync (can take up to an hour to propagate)
                        synced = await self.tree.sync()
                        logging.info("Globally synced %d commands", len(synced))
                        for c in synced:
                            logging.debug("  command: %s", getattr(c, 'name', repr(c)))
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
        # list global tree commands
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
