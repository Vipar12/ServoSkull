#!/usr/bin/env python3
"""Script to fix dispositions and dates in commands.py"""

# Read the entire file
with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

# First, find the exact content to replace using a marker-based approach
# Look for the section with DispositionCog
if 'class DispositionCog(commands.Cog):' in content:
    # Find the start and end
    start_marker = '    ]\n\n\n    class DispositionCog'
    end_marker = '    def __init__(self, bot: commands.Bot, db: Database):'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx >= 0 and end_idx >= 0:
        # Extract the part before, the problematic part, and the part after
        before = content[:start_idx]
        after = content[end_idx:]

        # Build the replacement section
        replacement = '''    ]

    ALLOWED_DISPOSITIONS = [
        "Take and Hold",
        "Purge the Foe",
        "Disruption",
        "Priority Assets",
        "Reconnaissance",
    ]

    '''

        # Reconstruct
        content = before + replacement + after

        # Write back
        with open('cogs/commands.py', 'w', encoding='utf-8') as f:
            f.write(content)

        print("Successfully removed DispositionCog and added ALLOWED_DISPOSITIONS!")
    else:
        print(f"Could not find markers. start_idx={start_idx}, end_idx={end_idx}")
else:
    print("DispositionCog not found in file")
