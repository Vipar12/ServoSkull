#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Find and replace the date parsing section with disposition validation + updated date parsing
old_date_section = '''        winner_army = canonical_winner_army
        loser_army = canonical_loser_army

        # Parse date
        if date:
            try:
                dt = datetime.datetime.fromisoformat(date)
                date_iso = dt.date().isoformat()
            except Exception:
                await interaction.response.send_message(
                    "Date must be in DD/MM/YYYY format.",
                    ephemeral=True,
                )
                return
        else:
            date_iso = datetime.date.today().isoformat()'''

new_date_section = '''        winner_army = canonical_winner_army
        loser_army = canonical_loser_army

        # Validate dispositions
        canonical_winner_disposition = self._validate_disposition(winner_disposition)
        if canonical_winner_disposition is None:
            await interaction.response.send_message(
                "Winner disposition is not in the approved list. Please use the autocomplete suggestions.",
                ephemeral=True,
            )
            return

        canonical_loser_disposition = self._validate_disposition(loser_disposition)
        if canonical_loser_disposition is None:
            await interaction.response.send_message(
                "Loser disposition is not in the approved list. Please use the autocomplete suggestions.",
                ephemeral=True,
            )
            return

        winner_disposition = canonical_winner_disposition
        loser_disposition = canonical_loser_disposition

        # Parse date - accepts DD/MM/YYYY format
        if date:
            try:
                # Try parsing as DD/MM/YYYY first
                dt = datetime.datetime.strptime(date, "%d/%m/%Y")
                date_iso = dt.date().isoformat()
            except ValueError:
                await interaction.response.send_message(
                    "Date must be in DD/MM/YYYY format.",
                    ephemeral=True,
                )
                return
        else:
            date_iso = datetime.date.today().isoformat()'''

if old_date_section in content:
    content = content.replace(old_date_section, new_date_section)

    with open('../cogs/commands.py', 'w') as f:
        f.write(content)

    print("Added disposition validation and updated date parsing!")
else:
    print("Could not find date parsing section")
