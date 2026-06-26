#!/usr/bin/env python3
"""Script to fix commands.py"""

with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Process line by line
output = []
i = 0
while i < len(lines):
    # Check if we're at the DispositionCog class
    if 'class DispositionCog' in lines[i]:
        # Skip this class and everything until we hit 'def __init__'
        while i < len(lines):
            if 'def __init__' in lines[i]:
                # Found __init__, now we add ALLOWED_DISPOSITIONS
                output.append('\n    ALLOWED_DISPOSITIONS = [\n')
                output.append('        "Take and Hold",\n')
                output.append('        "Purge the Foe",\n')
                output.append('        "Disruption",\n')
                output.append('        "Priority Assets",\n')
                output.append('        "Reconnaissance",\n')
                output.append('    ]\n')
                output.append('\n')
                output.append(lines[i])
                i += 1
                break
            i += 1
    else:
        output.append(lines[i])
        i += 1

with open('cogs/commands.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("Done!")
