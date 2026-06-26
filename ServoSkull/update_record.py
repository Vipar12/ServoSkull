#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Update the describe decorator - add dispositions and update date format message
old_describe = '''    @app_commands.describe(
        winner="Winner (mention)",
        loser="Loser (mention)",
        winner_army="Winner's army",
        loser_army="Loser's army",
        winner_score="Winner's score",
        loser_score="Loser's score",
        date="Optional date (YYYY-MM-DD)",
        notes="Optional notes",
    )
    @app_commands.autocomplete(
        winner_army=army_autocomplete,
        loser_army=army_autocomplete,
    )'''

new_describe = '''    @app_commands.describe(
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
    @app_commands.autocomplete(
        winner_army=army_autocomplete,
        loser_army=army_autocomplete,
        winner_disposition=disposition_autocomplete,
        loser_disposition=disposition_autocomplete,
    )'''

if old_describe in content:
    content = content.replace(old_describe, new_describe)

    # Also update the function signature to include dispositions
    old_sig = '''    async def record(
        self,
        interaction: discord.Interaction,
        winner: discord.Member,
        loser: discord.Member,
        winner_army: str,
        loser_army: str,
        winner_score: int,
        loser_score: int,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ):'''

    new_sig = '''    async def record(
        self,
        interaction: discord.Interaction,
        winner: discord.Member,
        loser: discord.Member,
        winner_army: str,
        winner_disposition: str,
        loser_army: str,
        loser_disposition: str,
        winner_score: int,
        loser_score: int,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ):'''

    if old_sig in content:
        content = content.replace(old_sig, new_sig)

        # Update the date parsing error message
        old_date_msg = '"Date must be in YYYY-MM-DD format."'
        new_date_msg = '"Date must be in DD/MM/YYYY format."'

        content = content.replace(old_date_msg, new_date_msg)

        with open('../cogs/commands.py', 'w') as f:
            f.write(content)

        print("Updated record command decorators and signature!")
    else:
        print("Could not find function signature")
else:
    print("Could not find describe decorator")
