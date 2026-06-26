#!/usr/bin/env python3
with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with T'au
for i, line in enumerate(lines[35:50], start=35):
    if 'Votann' in line or 'Necrons' in line or 'Orks' in line or 'au' in line or '__init__' in line:
        print(f'{i}: {repr(line)}')
