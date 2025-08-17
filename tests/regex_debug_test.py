"""
Debug script to test the regex pattern parsing.
"""

import re

# Current regex
COMPACT_PATTERN = re.compile(
    r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})(-?)'
    r'(pg(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?'
    r'(mt(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?$'
)

test_cases = [
    "d1wd5pg3-",
    "r1wd1pg3-", 
    "r1wd1mt2-",
    "r1wd1pg2-4",
    "r1wd1pg2",
    "r1wd1",
]

print("Testing current regex:")
for test in test_cases:
    match = COMPACT_PATTERN.match(test)
    if match:
        print(f"✓ '{test}' -> groups: {match.groups()}")
    else:
        print(f"✗ '{test}' -> NO MATCH")

print("\nTesting just the pg/mt parts:")
pg_pattern = re.compile(r'pg(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0)')

pg_tests = ["pg3-", "pg2-4", "pg2", "pg-2", "pg0"]
for test in pg_tests:
    match = pg_pattern.match(test)
    if match:
        print(f"✓ '{test}' matches pg pattern")
    else:
        print(f"✗ '{test}' does not match pg pattern")

print("\nTesting step by step:")
# Build up the regex piece by piece
step1 = re.compile(r'^([udlr]\d{1,2})?')
step2 = re.compile(r'^([udlr]\d{1,2})?([udlr]\d{1,2})?')
step3 = re.compile(r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)')
step4 = re.compile(r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})')
step5 = re.compile(r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})(-?)')

test_str = "d1wd5pg3-"
print(f"Testing '{test_str}':")
print(f"Step 1 (movement1): {step1.match(test_str).groups() if step1.match(test_str) else 'NO MATCH'}")
print(f"Step 2 (movement2): {step2.match(test_str).groups() if step2.match(test_str) else 'NO MATCH'}")
print(f"Step 3 (extract_type): {step3.match(test_str).groups() if step3.match(test_str) else 'NO MATCH'}")
print(f"Step 4 (extract_count): {step4.match(test_str).groups() if step4.match(test_str) else 'NO MATCH'}")
print(f"Step 5 (flexible): {step5.match(test_str).groups() if step5.match(test_str) else 'NO MATCH'}")

# Check what's left after step 5
if step5.match(test_str):
    match_len = len(step5.match(test_str).group(0))
    remainder = test_str[match_len:]
    print(f"Remainder after basic pattern: '{remainder}'")
