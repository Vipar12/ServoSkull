#!/usr/bin/env python3
with open('cogs/commands.py', 'rb') as f:
    content = f.read()

# Find DispositionCog section
idx = content.find(b'class DispositionCog')
if idx >= 0:
    # Print 500 bytes around it
    start = max(0, idx - 100)
    end = min(len(content), idx + 400)
    section = content[start:end]
    print(repr(section))
