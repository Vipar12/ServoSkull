"""
Data models or utilities for the bot.
Currently minimal but can be expanded.
"""
from dataclasses import dataclass

@dataclass
class MatchRecord:
    winner_id: str
    loser_id: str
    winner_score: int
    loser_score: int
    winner_army: str
    loser_army: str
    date: str
    notes: str = ""
