#!/usr/bin/env python3
import sys
with open('cogs/commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and print the exact bytes
idx = content.find('T')
for i in range(idx, min(idx+20, len(content))):
    c = content[i]
    print(f"Char {i-idx}: {repr(c)} (ord={ord(c)})")
