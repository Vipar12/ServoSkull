"""
Main bot entrypoint
Run this file to start the bot.
"""
from pathlib import Path
import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
from typing import Optional

import discord
from aiohttp import web
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
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_BRANCH = os.getenv("WEBHOOK_BRANCH", "main")
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
        self.web_app = web.Application()
        self.web_runner: Optional[web.AppRunner] = None
        self.web_site: Optional[web.TCPSite] = None
        self.update_lock = asyncio.Lock()
        self.web_app.router.add_post("/webhook/update", self.handle_update_webhook)

    def _verify_signature(self, payload: bytes, signature_header: str | None) -> bool:
        if not WEBHOOK_SECRET:
            return False
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected = hmac.new(
            WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        provided = signature_header.split("=", 1)[1]
        return hmac.compare_digest(expected, provided)

    async def _start_webhook_server(self) -> None:
        if not WEBHOOK_SECRET:
            logging.warning("WEBHOOK_SECRET is not set; webhook listener is disabled")
            return

        if self.web_runner:
            return

        self.web_runner = web.AppRunner(self.web_app)
        await self.web_runner.setup()
        self.web_site = web.TCPSite(self.web_runner, WEBHOOK_HOST, WEBHOOK_PORT)
        await self.web_site.start()
        logging.info("Webhook listener started on %s:%s", WEBHOOK_HOST, WEBHOOK_PORT)

    async def _perform_update(self) -> None:
        async with self.update_lock:
            repo_dir = Path(__file__).resolve().parent
            command = (
                f'cd "{repo_dir}" && '
                f'git pull && '
                f'"{sys.executable}" -m pip install -r requirements.txt'
            )
            logging.info("Starting self-update from webhook")
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            if output:
                logging.info("Webhook update output:\n%s", output)

            if process.returncode != 0:
                logging.error("Webhook update failed with exit code %s", process.returncode)
                return

            logging.info("Update succeeded; restarting bot process")
            os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])

    async def handle_update_webhook(self, request: web.Request) -> web.Response:
        if not WEBHOOK_SECRET:
            return web.Response(status=503, text="Webhook listener is disabled")

        payload = await request.read()
        signature = request.headers.get("X-Hub-Signature-256")
        if not self._verify_signature(payload, signature):
            return web.Response(status=403, text="Invalid signature")

        event = request.headers.get("X-GitHub-Event", "")
        if event != "push":
            return web.Response(text="Ignored")

        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            return web.Response(status=400, text="Invalid JSON")

        ref = data.get("ref", "")
        if ref != f"refs/heads/{WEBHOOK_BRANCH}":
            return web.Response(text="Ignored branch")

        asyncio.create_task(self._perform_update())
        return web.Response(text="Update scheduled")

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
            await self._start_webhook_server()

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

    async def close(self) -> None:
        if self.web_runner:
            await self.web_runner.cleanup()
            self.web_runner = None
            self.web_site = None
        await super().close()


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
