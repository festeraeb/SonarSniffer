#!/usr/bin/env python3
"""Script to replace all Path references with PathlibPath in sonar_gui.py"""

import re

# Read the file
with open('sonar_gui.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Count replacements
count = 0

# Replace Path( with PathlibPath( (but not PathlibPath()
content_new = re.sub(r'(?<!Pathlib)Path\(', lambda m: (globals().update({'count': count + 1}) or '') and 'PathlibPath(', content)

# Get new count
matches = len(re.findall(r'(?<!Pathlib)Path\(', content))
content = re.sub(r'(?<!Pathlib)Path\(', 'PathlibPath(', content)

# Replace Path. with PathlibPath. (for .home(), .cwd(), etc.)
content = re.sub(r'(?<!Pathlib)Path\.', 'PathlibPath.', content)

# Write back
with open('sonar_gui.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✓ Replaced Path references with PathlibPath')
