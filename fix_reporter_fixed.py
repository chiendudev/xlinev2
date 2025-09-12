#!/usr/bin/env python3
"""Fix test_reporter_fixed.py by adding missing generated_at fields."""

import re

# Read the file
file_path = "/Users/chiendu/XlineV2/tests/core/analytics/test_reporter_fixed.py"
with open(file_path, 'r') as f:
    content = f.read()

# Fix PerformanceReport instances that are missing generated_at
# Pattern to match PerformanceReport constructor calls
pattern = r'(PerformanceReport\([^)]*?recommendations=\[[^\]]*?\])(\s*\))'

def add_generated_at(match):
    constructor_call = match.group(1)
    closing_paren = match.group(2)
    
    # Only add if generated_at is not already present
    if 'generated_at=' not in constructor_call:
        return constructor_call + ',\n                generated_at=datetime.now()' + closing_paren
    else:
        return match.group(0)

content = re.sub(pattern, add_generated_at, content, flags=re.DOTALL)

# Also fix cases where recommendations is a simple list
pattern2 = r'(PerformanceReport\([^)]*?recommendations=\[\])(\s*\))'
content = re.sub(pattern2, add_generated_at, content, flags=re.DOTALL)

# Write back
with open(file_path, 'w') as f:
    f.write(content)

print("Fixed test_reporter_fixed.py")
