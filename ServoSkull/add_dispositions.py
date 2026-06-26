#!/usr/bin/env python3
with open('../cogs/commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact location to insert ALLOWED_DISPOSITIONS
# We want to insert it after ALLOWED_ARMIES and before def __init__

armies_end = content.find('    ]\n\n    def __init__')
if armies_end > 0:
    # Position after the first ']\n\n'
    insert_pos = armies_end + 7  # len('    ]\n\n')

    dispositions_code = '''ALLOWED_DISPOSITIONS = [
        "Take and Hold",
        "Purge the Foe",
        "Disruption",
        "Priority Assets",
        "Reconnaissance",
    ]

    '''

    new_content = content[:insert_pos] + dispositions_code + content[insert_pos:]

    with open('../cogs/commands.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Added ALLOWED_DISPOSITIONS!")
else:
    print("Could not find insertion point")
