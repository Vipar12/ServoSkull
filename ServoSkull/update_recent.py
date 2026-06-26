#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Update the recent matches display
old_recent = '''        for r in rows:
            winner_mention = f"<@{r['winner_id']}>"
            loser_mention = f"<@{r['loser_id']}>"
            desc = (
                f"{winner_mention} ({r['winner_army']}) {r['winner_score']} - "
                f"{r['loser_score']} ({r['loser_army']}) {loser_mention}"
            )
            embed.add_field(
                name=f"Match {r['id']} - {r['date']}",
                value=desc,
                inline=False,
            )'''

new_recent = '''        for r in rows:
            winner_mention = f"<@{r['winner_id']}>"
            loser_mention = f"<@{r['loser_id']}>"
            desc = (
                f"{winner_mention} ({r['winner_army']}) {r['winner_score']} - "
                f"{r['loser_score']} ({r['loser_army']}) {loser_mention}"
            )
            formatted_date = self._format_date_display(r['date'])
            embed.add_field(
                name=f"Match {r['id']} - {formatted_date}",
                value=desc,
                inline=False,
            )'''

if old_recent in content:
    content = content.replace(old_recent, new_recent)

    with open('../cogs/commands.py', 'w') as f:
        f.write(content)

    print("Updated recent matches display!")
else:
    print("Could not find recent matches section")
