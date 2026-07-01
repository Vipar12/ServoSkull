"""
Cog with slash commands for match recording and stats.
"""
from discord import app_commands, Embed
from discord.ext import commands
import discord
import logging
import os
from typing import Optional
import datetime

from database import Database


class MatchCog(commands.Cog):
    ALLOWED_ARMIES = [
        "Adepta Sororitas",
        "Adeptus Custodes",
        "Adeptus Mechanicus",
        "Astra Militarum",
        "Imperial Agents",
        "Imperial Knights",
        "Space Marines",
        "Grey Knights",
        "Black Templars",
        "Blood Angels",
        "Dark Angels",
        "Chaos Daemons",
        "Chaos Knights",
        "Chaos Space Marines",
        "Death Guard",
        "Emperor's Children",
        "Thousand Sons",
        "World Eaters",
        "Aeldari",
        "Eldar",
        "Drukhari",
        "Genestealer Cults",
        "Tyranids",
        "Leagues of Votann",
        "Necrons",
        "Orks",
        "T'au Empire",
    ]

    DISPOSITIONS = [
        "Take and Hold",
        "Purge the Foe",
        "Disruption",
        "Reconnaissance",
        "Priority assets",
    ]

    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    async def cog_load(self) -> None:
        """Ensure app commands from this cog are registered to the dev guild if provided.
        This helps when global sync is slow or when auto-registration doesn't occur.
        """
        dev_guild = os.getenv("DEV_GUILD_ID")
        if not dev_guild:
            return

        guild_obj = discord.Object(id=int(dev_guild))
        cmds = [
            self.record,
            self.playerstats,
            self.armystats,
            self.recent,
            self.leaderboard,
            self.headtohead,
            self.delete_match,
        ]

        for cmd in cmds:
            try:
                self.bot.tree.add_command(cmd, guild=guild_obj)
                logging.info(
                    "Added command %s to dev guild %s",
                    getattr(cmd, "__name__", repr(cmd)),
                    dev_guild,
                )
            except Exception:
                logging.exception(
                    "Failed to add command %s to dev guild %s",
                    getattr(cmd, "__name__", repr(cmd)),
                    dev_guild,
                )

    # Helper to format user id
    def _user_to_str(self, user: discord.User) -> str:
        return str(user.id)

    @classmethod
    def _normalize_army(cls, value: str) -> str:
        return " ".join(value.strip().lower().split())

    @classmethod
    def _army_lookup(cls) -> dict[str, str]:
        return {cls._normalize_army(name): name for name in cls.ALLOWED_ARMIES}

    def _validate_army_name(self, army: str) -> Optional[str]:
        lookup = self._army_lookup()
        return lookup.get(self._normalize_army(army))

    @classmethod
    def _normalize_disposition(cls, value: str) -> str:
        return " ".join(value.strip().lower().split())

    @classmethod
    def _disposition_lookup(cls) -> dict[str, str]:
        return {cls._normalize_disposition(name): name for name in cls.DISPOSITIONS}

    def _validate_disposition(self, disp: str) -> Optional[str]:
        lookup = self._disposition_lookup()
        return lookup.get(self._normalize_disposition(disp))

    @classmethod
    def _parse_date_input(cls, value: str) -> datetime.date:
        return datetime.datetime.strptime(value.strip(), "%d/%m/%Y").date()

    @classmethod
    def _format_date_display(cls, value: str) -> str:
        try:
            return datetime.datetime.fromisoformat(value).strftime("%d/%m/%Y")
        except Exception:
            try:
                return datetime.datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return value

    async def army_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_norm = self._normalize_army(current)

        starts_with = []
        contains = []

        for army in self.ALLOWED_ARMIES:
            army_norm = self._normalize_army(army)

            if not current_norm:
                starts_with.append(army)
            elif army_norm.startswith(current_norm):
                starts_with.append(army)
            elif current_norm in army_norm:
                contains.append(army)

        matches = (starts_with + contains)[:25]
        return [app_commands.Choice(name=army, value=army) for army in matches]

    @app_commands.command(name="record", description="Record a match result")
    @app_commands.describe(
        winner="Winner (mention)",
        loser="Loser (mention)",
        winner_army="Winner's army",
        winner_disposition="Winner's disposition",
        loser_army="Loser's army",
        loser_disposition="Loser's disposition",
        winner_score="Winner's score",
        loser_score="Loser's score",
        date="Optional date (DD/MM/YYYY)",
        notes="Optional notes",
    )
    @app_commands.choices(
        winner_disposition=[
            app_commands.Choice(name="Take and Hold", value="Take and Hold"),
            app_commands.Choice(name="Purge the Foe", value="Purge the Foe"),
            app_commands.Choice(name="Disruption", value="Disruption"),
            app_commands.Choice(name="Recon", value="Recon"),
            app_commands.Choice(name="Priority assets", value="Priority assets"),
        ],
        loser_disposition=[
            app_commands.Choice(name="Take and Hold", value="Take and Hold"),
            app_commands.Choice(name="Purge the Foe", value="Purge the Foe"),
            app_commands.Choice(name="Disruption", value="Disruption"),
            app_commands.Choice(name="Recon", value="Recon"),
            app_commands.Choice(name="Priority assets", value="Priority assets"),
        ],
    )
    @app_commands.autocomplete(
        winner_army=army_autocomplete,
        loser_army=army_autocomplete,
    )
    async def record(
        self,
        interaction: discord.Interaction,
        winner: discord.User,
        loser: discord.User,
        winner_army: str,
        winner_disposition: str,
        loser_army: str,
        loser_disposition: str,
        winner_score: int,
        loser_score: int,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        # Basic validation
        if winner.id == loser.id:
            await interaction.followup.send(
                "Winner and loser cannot be the same user."
            )
            return

        if not isinstance(winner_score, int) or not isinstance(loser_score, int):
            await interaction.followup.send(
                "Scores must be integers."
            )
            return

        if winner_score < loser_score and (not notes or len(notes.strip()) == 0):
            await interaction.followup.send(
                "Winner score is less than loser score. Provide notes to explain a non-standard result."
            )
            return

        canonical_winner_army = self._validate_army_name(winner_army)
        if canonical_winner_army is None:
            await interaction.followup.send(
                "Winner army is not in the approved army list. Please use the autocomplete suggestions."
            )
            return

        canonical_loser_army = self._validate_army_name(loser_army)
        if canonical_loser_army is None:
            await interaction.followup.send(
                "Loser army is not in the approved army list. Please use the autocomplete suggestions."
            )
            return

        canonical_winner_disposition = self._validate_disposition(winner_disposition)
        if canonical_winner_disposition is None:
            await interaction.followup.send(
                "Winner disposition is not valid. Please choose one of the provided dispositions."
            )
            return

        canonical_loser_disposition = self._validate_disposition(loser_disposition)
        if canonical_loser_disposition is None:
            await interaction.followup.send(
                "Loser disposition is not valid. Please choose one of the provided dispositions."
            )
            return

        winner_army = canonical_winner_army
        loser_army = canonical_loser_army

        # Parse date
        if date:
            try:
                date_iso = self._parse_date_input(date).isoformat()
            except Exception:
                await interaction.followup.send(
                    "Date must be in DD/MM/YYYY format."
                )
                return
        else:
            date_iso = datetime.date.today().isoformat()

        # Write to db
        try:
            if not interaction.guild:
                await interaction.followup.send(
                    "This command must be used in a server (guild)."
                )
                return

            guild_id = str(interaction.guild.id)
            match_id = await self.db.add_match(
                guild_id,
                str(winner.id),
                str(loser.id),
                winner_score,
                loser_score,
                winner_army,
                canonical_winner_disposition,
                loser_army,
                canonical_loser_disposition,
                date_iso,
                notes,
            )
        except Exception as e:
            await interaction.followup.send(
                f"Failed to save match: {e}"
            )
            return

        embed = Embed(title="Match Recorded", color=discord.Color.green())
        embed.add_field(
            name="Winner",
            value=f"{winner.mention} ({winner_army}) - {winner_score}",
        )
        embed.add_field(
            name="Winner Disposition",
            value=canonical_winner_disposition,
        )
        embed.add_field(
            name="Loser",
            value=f"{loser.mention} ({loser_army}) - {loser_score}",
        )
        embed.add_field(
            name="Loser Disposition",
            value=canonical_loser_disposition,
        )
        embed.add_field(name="Date", value=self._format_date_display(date_iso))

        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)

        embed.set_footer(text=f"Match ID: {match_id}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="playerstats", description="Show stats for a player")
    async def playerstats(self, interaction: discord.Interaction, player: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        stats = await self.db.player_stats(str(player.id), str(interaction.guild.id))
        embed = Embed(title=f"Stats for {player.display_name}", color=discord.Color.blue())
        embed.add_field(name="Wins", value=str(stats["wins"]))
        embed.add_field(name="Losses", value=str(stats["losses"]))
        embed.add_field(name="Games", value=str(stats["total"]))
        embed.add_field(name="Win Rate", value=f"{stats['win_rate']:.2f}%")
        embed.add_field(name="Points Scored", value=str(stats["points_scored"]))
        embed.add_field(name="Points Allowed", value=str(stats["points_allowed"]))
        embed.add_field(name="Most Played", value=stats["most_played"] or "N/A")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="armystats", description="Show stats for an army")
    @app_commands.autocomplete(army=army_autocomplete)
    async def armystats(self, interaction: discord.Interaction, army: str):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        canonical_army = self._validate_army_name(army)
        if canonical_army is None:
            await interaction.response.send_message(
                "That army is not in the approved army list. Please use the autocomplete suggestions.",
                ephemeral=True,
            )
            return

        stats = await self.db.army_stats(canonical_army, str(interaction.guild.id))
        embed = Embed(title=f"Army Stats: {canonical_army}", color=discord.Color.dark_gold())
        embed.add_field(name="Games", value=str(stats["games"]))
        embed.add_field(name="Wins", value=str(stats["wins"]))
        embed.add_field(name="Losses", value=str(stats["losses"]))
        embed.add_field(name="Win Rate", value=f"{stats['win_rate']:.2f}%")

        players = []
        for p in stats["players"]:
            user = self.bot.get_user(int(p))
            players.append(user.display_name if user else p)

        embed.add_field(
            name="Players",
            value=", ".join(players) if players else "N/A",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="recent", description="Show recent matches")
    @app_commands.describe(
        limit="Number of matches to show",
        player="Filter by player",
        army="Filter by army",
    )
    @app_commands.autocomplete(army=army_autocomplete)
    async def recent(
        self,
        interaction: discord.Interaction,
        limit: int = 5,
        player: Optional[discord.Member] = None,
        army: Optional[str] = None,
    ):
        player_id = str(player.id) if player else None

        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        canonical_army = None
        if army:
            canonical_army = self._validate_army_name(army)
            if canonical_army is None:
                await interaction.response.send_message(
                    "That army is not in the approved army list. Please use the autocomplete suggestions.",
                    ephemeral=True,
                )
                return

        rows = await self.db.get_recent_matches(
            str(interaction.guild.id),
            limit=limit,
            player=player_id,
            army=canonical_army,
        )

        embed = Embed(title="Recent Matches", color=discord.Color.blurple())

        if not rows:
            embed.description = "No matches found."
            await interaction.response.send_message(embed=embed)
            return

        for r in rows:
            winner_mention = f"<@{r['winner_id']}>"
            loser_mention = f"<@{r['loser_id']}>"
            desc = (
                f"{winner_mention} ({r['winner_army']}) {r['winner_score']} - "
                f"{r['loser_score']} ({r['loser_army']}) {loser_mention}"
            )
            embed.add_field(
                name=f"Match {r['id']} - {self._format_date_display(r['date'])}",
                value=desc,
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Show leaderboards")
    @app_commands.describe(
        min_games="Minimum games for win rate leaderboard",
        limit="Number of players to show",
    )
    async def leaderboard(self, interaction: discord.Interaction, min_games: int = 3, limit: int = 10):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        data = await self.db.leaderboard(
            str(interaction.guild.id),
            min_games=min_games,
            limit=limit,
        )

        embed = Embed(title="Leaderboard", color=discord.Color.gold())

        # Most wins
        wins_lines = []
        for row in data["most_wins"]:
            user = self.bot.get_user(int(row["winner_id"]))
            name = user.display_name if user else row["winner_id"]
            wins_lines.append(f"{name} - {row['wins']}")
        embed.add_field(
            name="Most Wins",
            value="\n".join(wins_lines) if wins_lines else "N/A",
        )

        # Best win rate
        wr_lines = []
        for r in data["best_winrate"]:
            user = self.bot.get_user(int(r["player"]))
            name = user.display_name if user else r["player"]
            wr_lines.append(f"{name} - {r['win_rate']:.2f}% ({r['wins']}/{r['games']})")
        embed.add_field(
            name=f"Best Win Rate (min {min_games} games)",
            value="\n".join(wr_lines) if wr_lines else "N/A",
        )

        # Points
        pts_lines = []
        for r in data["points"]:
            user = self.bot.get_user(int(r["player"]))
            name = user.display_name if user else r["player"]
            pts_lines.append(f"{name} - {r['total_points']}")
        embed.add_field(
            name="Most Points",
            value="\n".join(pts_lines) if pts_lines else "N/A",
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="headtohead", description="Head to head between two players")
    async def headtohead(
        self,
        interaction: discord.Interaction,
        player1: discord.Member,
        player2: discord.Member,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        rows = await self.db.get_matches_between(
            str(player1.id),
            str(player2.id),
            str(interaction.guild.id),
        )

        if not rows:
            await interaction.response.send_message(
                "No matches found between those players.",
                ephemeral=True,
            )
            return

        p1_wins = 0
        p2_wins = 0
        p1_points = 0
        p2_points = 0
        armies = {}

        for r in rows:
            if r["winner_id"] == str(player1.id):
                p1_wins += 1
            elif r["winner_id"] == str(player2.id):
                p2_wins += 1

            if r["winner_id"] == str(player1.id):
                p1_points += r["winner_score"]
                p2_points += r["loser_score"]
            else:
                p2_points += r["winner_score"]
                p1_points += r["loser_score"]

            armies[r["winner_army"]] = armies.get(r["winner_army"], 0) + 1
            armies[r["loser_army"]] = armies.get(r["loser_army"], 0) + 1

        embed = Embed(
            title=f"Head to Head: {player1.display_name} vs {player2.display_name}",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Total Matches", value=str(len(rows)))
        embed.add_field(name=f"{player1.display_name} Wins", value=str(p1_wins))
        embed.add_field(name=f"{player2.display_name} Wins", value=str(p2_wins))
        embed.add_field(name=f"{player1.display_name} Points", value=str(p1_points))
        embed.add_field(name=f"{player2.display_name} Points", value=str(p2_points))

        top_army = max(armies.items(), key=lambda kv: kv[1])[0] if armies else "N/A"
        embed.add_field(name="Most Used Army in H2H", value=top_army)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete_match", description="Delete a recorded match (admin only)")
    async def delete_match(self, interaction: discord.Interaction, match_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You do not have permission to delete matches.",
                ephemeral=True,
            )
            return

        if not interaction.guild:
            await interaction.response.send_message(
                "This command must be used in a server (guild).",
                ephemeral=True,
            )
            return

        deleted = await self.db.delete_match(match_id, str(interaction.guild.id))
        if deleted:
            await interaction.response.send_message(f"Deleted match {match_id}.")
        else:
            await interaction.response.send_message(
                f"Match {match_id} not found.",
                ephemeral=True,
            )