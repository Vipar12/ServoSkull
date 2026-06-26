#!/usr/bin/env python3

with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

output = []
i = 0
while i < len(lines):
    line = lines[i]

    # Skip the entire DispositionCog class
    if 'class DispositionCog' in line:
        # Skip until we hit def __init__
        while i < len(lines) and 'def __init__' not in lines[i]:
            i += 1

        # Add dispositions before __init__
        output.append('\n')
        output.append('    ALLOWED_DISPOSITIONS = [\n')
        output.append('        "Take and Hold",\n')
        output.append('        "Purge the Foe",\n')
        output.append('        "Disruption",\n')
        output.append('        "Priority Assets",\n')
        output.append('        "Reconnaissance",\n')
        output.append('    ]\n')
        output.append('\n')
        # Don't skip the __init__ line, we'll add it next
        continue

    output.append(line)
    i += 1

with open('cogs/commands.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print('File fixed!')
