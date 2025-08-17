"""
Quick test to verify number trimming fixes.
"""

import re


def _trim_numbers_from_end(content: str, count: int, number_pattern) -> str:
    """Trim N numbers from the end, removing the Nth-from-last number and everything after it."""
    matches = list(number_pattern.finditer(content))
    
    if count > len(matches):
        return ""  # Not enough numbers to trim
    
    if count == 0:
        return content
    
    # Find position at start of the Nth-from-last number
    # For count=1, we want the last number: matches[-1]
    # For count=2, we want the second-to-last: matches[-2]
    target_match = matches[-count]
    trim_from_position = target_match.start()
    
    return content[:trim_from_position]


def test_number_trimming_fix():
    """Test the fixed number trimming logic."""
    # Improved pattern: digits with optional decimal separators, no leading hyphens
    number_pattern = re.compile(r'\d+(?:[.,]\d+)*')
    
    test_cases = [
        # (content, count, expected_result)
        ("Ref-2024-001-TEMP", 1, "Ref-2024-"),
        ("Ref-2024-001-TEMP", 2, "Ref-"),
        ("Invoice INV-2024-001-TEMP", 1, "Invoice INV-2024-"),
        ("Account123Extra", 1, "Account"),
    ]
    
    print("Testing fixed number trimming:")
    for content, count, expected in test_cases:
        # Debug: show what numbers are found
        matches = list(number_pattern.finditer(content))
        found_numbers = [(m.group(), m.start(), m.end()) for m in matches]
        print(f"\nInput: '{content}'")
        print(f"Numbers found: {found_numbers}")
        
        result = _trim_numbers_from_end(content, count, number_pattern)
        status = "✓" if result == expected else "✗"
        print(f"{status} Trim {count} from end: '{content}' → '{result}' (expected '{expected}')")


if __name__ == "__main__":
    test_number_trimming_fix()


# End of file #
