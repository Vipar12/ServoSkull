#!/usr/bin/env python3
with open('../cogs/commands.py', 'r') as f:
    content = f.read()

# Fix the indentation issue - replace the malformed section
bad_section = '''ALLOWED_DISPOSITIONS = [
        "Take and Hold",
        "Purge the Foe",
        "Disruption",
        "Priority Assets",
        "Reconnaissance",
    ]

        def __init__'''

good_section = '''    ALLOWED_DISPOSITIONS = [
        "Take and Hold",
        "Purge the Foe",
        "Disruption",
        "Priority Assets",
        "Reconnaissance",
    ]

    def __init__'''

if bad_section in content:
    content = content.replace(bad_section, good_section)
    with open('../cogs/commands.py', 'w') as f:
        f.write(content)
    print("Fixed indentation!")
else:
    print("Section not found")
    # Try to show what we have
    if 'ALLOWED_DISPOSITIONS' in content:
        idx = content.find('ALLOWED_DISPOSITIONS')
        print(content[idx-50:idx+200])
