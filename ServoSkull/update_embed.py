#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Update the embed display in the record function
old_embed = '''        embed = Embed(title="Match Recorded", color=discord.Color.green())
        embed.add_field(
            name="Winner",
            value=f"{winner.mention} ({winner_army}) - {winner_score}",
        )
        embed.add_field(
            name="Loser",
            value=f"{loser.mention} ({loser_army}) - {loser_score}",
        )
        embed.add_field(name="Date", value=date_iso)

        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)

        embed.set_footer(text=f"Match ID: {match_id}")
        await interaction.response.send_message(embed=embed)'''

new_embed = '''        formatted_date = self._format_date_display(date_iso)

        embed = Embed(title="Match Recorded", color=discord.Color.green())
        embed.add_field(
            name="Winner",
            value=f"{winner.mention} ({winner_army}) - {winner_score}",
        )
        embed.add_field(
            name="Winner Disposition",
            value=winner_disposition,
        )
        embed.add_field(
            name="Loser",
            value=f"{loser.mention} ({loser_army}) - {loser_score}",
        )
        embed.add_field(
            name="Loser Disposition",
            value=loser_disposition,
        )
        embed.add_field(name="Date", value=formatted_date)

        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)

        embed.set_footer(text=f"Match ID: {match_id}")
        await interaction.response.send_message(embed=embed)'''

if old_embed in content:
    content = content.replace(old_embed, new_embed)

    with open('../cogs/commands.py', 'w') as f:
        f.write(content)

    print("Updated embed display!")
else:
    print("Could not find embed section")
