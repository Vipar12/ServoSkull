"""
SQLite database wrapper for match storage and queries.
Handles creating tables and queries used by the bot.
"""
import sqlite3
import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import datetime

DEFAULT_DB_PATH = Path(__file__).resolve().with_name("matches.db")
FALLBACK_DB_PATH = Path.home() / ".servoskull" / "matches.db"
DB_PATH = Path(os.getenv("SERVO_SKULL_DB_PATH", DEFAULT_DB_PATH))

CREATE_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    winner_id TEXT NOT NULL,
    loser_id TEXT NOT NULL,
    winner_score INTEGER NOT NULL,
    loser_score INTEGER NOT NULL,
    winner_army TEXT NOT NULL,
    winner_disposition TEXT NOT NULL DEFAULT '',
    loser_army TEXT NOT NULL,
    loser_disposition TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    notes TEXT,
    timestamp INTEGER NOT NULL
);
"""

ADDITIONAL_MATCH_COLUMNS = (
    ("winner_disposition", "TEXT NOT NULL DEFAULT ''"),
    ("loser_disposition", "TEXT NOT NULL DEFAULT ''"),
)

class Database:
    def __init__(self, path: str | Path = DB_PATH):
        self.path = Path(path)
        self.conn: Optional[sqlite3.Connection] = None
        self.lock = asyncio.Lock()
        self._fallback_used = False

    def _open_connection(self, db_path: Path) -> sqlite3.Connection:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            try:
                db_path.chmod(0o666)
            except Exception:
                pass

        conn = sqlite3.connect(
            f"file:{db_path.resolve().as_posix()}?mode=rwc",
            uri=True,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute(CREATE_MATCHES_TABLE)
            existing_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(matches);").fetchall()
            }
            for column_name, column_def in ADDITIONAL_MATCH_COLUMNS:
                if column_name not in existing_columns:
                    conn.execute(f"ALTER TABLE matches ADD COLUMN {column_name} {column_def};")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_guild ON matches(guild_id);")
        return conn

    def _migrate_date_format(self) -> int:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT id, date FROM matches").fetchall()
        updated = 0
        for row in rows:
            date_value = row["date"]
            try:
                parsed = datetime.datetime.strptime(date_value, "%Y-%m-%d")
            except Exception:
                continue

            new_value = parsed.strftime("%d/%m/%Y")
            if new_value != date_value:
                cur.execute("UPDATE matches SET date = ? WHERE id = ?", (new_value, row["id"]))
                updated += 1

        if updated:
            self.conn.commit()
        return updated

    async def connect(self):
        self.conn = self._open_connection(self.path)
        self._migrate_date_format()

    async def _switch_to_fallback(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        self.path = FALLBACK_DB_PATH
        self.conn = self._open_connection(self.path)
        self._fallback_used = True

    async def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    async def add_match(self, guild_id: str, winner_id: str, loser_id: str, winner_score: int, loser_score: int, winner_army: str, winner_disposition: str, loser_army: str, loser_disposition: str, date_iso: str, notes: Optional[str] = None):
        async with self.lock:
            ts = int(datetime.datetime.utcnow().timestamp())
            try:
                cur = self.conn.cursor()
                cur.execute(
                    "INSERT INTO matches (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, winner_disposition, loser_army, loser_disposition, date, notes, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, winner_disposition, loser_army, loser_disposition, date_iso, notes, ts)
                )
                self.conn.commit()
                return cur.lastrowid
            except sqlite3.OperationalError as e:
                if "readonly database" in str(e).lower() and not self._fallback_used:
                    await self._switch_to_fallback()
                    cur = self.conn.cursor()
                    cur.execute(
                        "INSERT INTO matches (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, winner_disposition, loser_army, loser_disposition, date, notes, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (guild_id, winner_id, loser_id, winner_score, loser_score, winner_army, winner_disposition, loser_army, loser_disposition, date_iso, notes, ts)
                    )
                    self.conn.commit()
                    return cur.lastrowid
                raise

    async def get_player_matches(self, user_id: str, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE (winner_id = ? OR loser_id = ?) AND guild_id = ? ORDER BY timestamp DESC", (user_id, user_id, guild_id))
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
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cur.execute(query, params)
        return cur.fetchall()

    async def get_all_matches(self, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE guild_id = ? ORDER BY timestamp DESC", (guild_id,))
        return cur.fetchall()

    async def get_matches_between(self, user1: str, user2: str, guild_id: str) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM matches WHERE ((winner_id = ? AND loser_id = ?) OR (winner_id = ? AND loser_id = ?)) AND guild_id = ? ORDER BY timestamp DESC", (user1, user2, user2, user1, guild_id))
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
        cur.execute("SELECT * FROM matches WHERE (winner_army = ? OR loser_army = ?) AND guild_id = ? ORDER BY timestamp DESC", (army_name, army_name, guild_id))
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