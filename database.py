"""
SQLite database wrapper for match storage and queries.
Handles creating tables and queries used by the bot.
"""
import sqlite3
import asyncio
from typing import Optional, List, Dict, Any
import datetime

DB_PATH = "matches.db"

CREATE_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    winner_id TEXT NOT NULL,
    loser_id TEXT NOT NULL,
    winner_score INTEGER NOT NULL,
    loser_score INTEGER NOT NULL,
    winner_army TEXT NOT NULL,
    loser_army TEXT NOT NULL,
    date TEXT NOT NULL,
    notes TEXT,
    timestamp INTEGER NOT NULL
);
"""

class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.conn: Optional[sqlite3.Connection] = None
        self.lock = asyncio.Lock()

    async def connect(self):
        # Use a thread-safe connection
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            self.conn.execute(CREATE_MATCHES_TABLE)
            # ensure index for guild filtering
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_guild ON matches(guild_id);")

    async def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    async def add_match(self, guild_id: str, winner_id: str, loser_id: str, winner_score: int, loser_score: int, winner_army: str, loser_army: str, date_iso: str, notes: Optional[str] = None):
        async with self.lock:
            ts = int(datetime.datetime.utcnow().timestamp())
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO matches (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, loser_army, date, notes, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, loser_army, date_iso, notes, ts)
            )
            self.conn.commit()
            return cur.lastrowid

    async def get_player_matches(self, user_id: str, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE (winner_id = ? OR loser_id = ?) AND guild_id = ? ORDER BY date DESC", (user_id, user_id, guild_id))
        return cur.fetchall()

    async def get_recent_matches(self, guild_id: str, limit: int = 10, player: Optional[str] = None, army: Optional[str] = None) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        query = "SELECT * FROM matches"
        params: List[Any] = []
        clauses: List[str] = []
        # always restrict to guild
        clauses.append("guild_id = ?")
        params.append(guild_id)
        if player:
            clauses.append("(winner_id = ? OR loser_id = ?)")
            params.extend([player, player])
        if army:
            clauses.append("(winner_army = ? OR loser_army = ?)")
            params.extend([army, army])
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)
        cur.execute(query, params)
        return cur.fetchall()

    async def get_all_matches(self, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE guild_id = ? ORDER BY date DESC", (guild_id,))
        return cur.fetchall()

    async def get_matches_between(self, user1: str, user2: str, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE ((winner_id = ? AND loser_id = ?) OR (winner_id = ? AND loser_id = ?)) AND guild_id = ? ORDER BY date DESC", (user1, user2, user2, user1, guild_id))
        return cur.fetchall()

    async def delete_match(self, match_id: int, guild_id: str):
        async with self.lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM matches WHERE id = ? AND guild_id = ?", (match_id, guild_id))
            self.conn.commit()
            return cur.rowcount

    # Summary helpers
    async def player_stats(self, user_id: str, guild_id: str) -> Dict[str, Any]:
        matches = await self.get_player_matches(user_id, guild_id)
        wins = 0
        losses = 0
        points_scored = 0
        points_allowed = 0
        armies = {}
        for m in matches:
            if m["winner_id"] == user_id:
                wins += 1
                points_scored += m["winner_score"]
                points_allowed += m["loser_score"]
                army = m["winner_army"]
                armies[army] = armies.get(army, 0) + 1
            else:
                losses += 1
                points_scored += m["loser_score"]
                points_allowed += m["winner_score"]
                army = m["loser_army"]
                armies[army] = armies.get(army, 0) + 1
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0.0
        most_played = max(armies.items(), key=lambda kv: kv[1])[0] if armies else None
        return {
            "wins": wins,
            "losses": losses,
            "total": total,
            "win_rate": win_rate,
            "points_scored": points_scored,
            "points_allowed": points_allowed,
            "most_played": most_played,
        }

    async def army_stats(self, army_name: str, guild_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE (winner_army = ? OR loser_army = ?) AND guild_id = ? ORDER BY date DESC", (army_name, army_name, guild_id))
        matches = cur.fetchall()
        games = len(matches)
        wins = 0
        losses = 0
        players = set()
        for m in matches:
            if m["winner_army"] == army_name:
                wins += 1
            if m["loser_army"] == army_name:
                losses += 1
            players.add(m["winner_id"])
            players.add(m["loser_id"])
        win_rate = (wins / games * 100) if games > 0 else 0.0
        return {
            "games": games,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "players": list(players),
        }

    async def leaderboard(self, guild_id: str, min_games: int = 0, limit: int = 10) -> Dict[str, Any]:
        cur = self.conn.cursor()
        # most wins per guild
        cur.execute("SELECT winner_id, COUNT(*) as wins FROM matches WHERE guild_id = ? GROUP BY winner_id ORDER BY wins DESC LIMIT ?", (guild_id, limit))
        most_wins = cur.fetchall()

        # points scored per guild
        cur.execute(
            "SELECT player, SUM(points) as total_points FROM ( SELECT winner_id as player, winner_score as points FROM matches WHERE guild_id = ? UNION ALL SELECT loser_id as player, loser_score as points FROM matches WHERE guild_id = ? ) GROUP BY player ORDER BY total_points DESC LIMIT ?",
            (guild_id, guild_id, limit),
        )
        points = cur.fetchall()

        # win rate with threshold per guild
        cur.execute(
            "SELECT player, SUM(is_win) as wins, COUNT(*) as games FROM ( SELECT winner_id as player, 1 as is_win FROM matches WHERE guild_id = ? UNION ALL SELECT loser_id as player, 0 as is_win FROM matches WHERE guild_id = ? ) GROUP BY player HAVING games >= ?",
            (guild_id, guild_id, min_games),
        )
        rows = cur.fetchall()
        winrates = []
        for r in rows:
            winrates.append({"player": r["player"], "wins": r["wins"], "games": r["games"], "win_rate": r["wins"]/r["games"]*100})
        winrates.sort(key=lambda x: x["win_rate"], reverse=True)
        return {
            "most_wins": most_wins,
            "points": points,
            "best_winrate": winrates[:limit]
        }