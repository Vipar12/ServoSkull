#!/usr/bin/env python3
with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(39, 70):
    print(f"{i}: {repr(lines[i])}")
