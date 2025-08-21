#!/usr/bin/env python3
"""
Debug script to check boolean vs pattern detection.
File: debug_boolean_detection.py

Run: python debug_boolean_detection.py
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports  
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pdf_manipulator.core.page_range.patterns import looks_like_pattern
    from pdf_manipulator.core.page_range.boolean import looks_like_boolean_expression
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import functions: {e}")
    IMPORTS_AVAILABLE = False


def test_problematic_string():
    """Test the specific string that's failing."""
    if not IMPORTS_AVAILABLE:
        print("Cannot run debug - imports not available")
        return
    
    # This is the exact string from your error
    test_string = 'contains:"NAKN EK, AK" | contains:"EK, AK" | contains:"NAKNEK, AK"'
    
    print("=== Debugging Boolean vs Pattern Detection ===")
    print(f"Test string: {test_string}")
    print()
    
    # Check pattern detection
    try:
        is_pattern = looks_like_pattern(test_string)
        print(f"looks_like_pattern(): {is_pattern}")
    except Exception as e:
        print(f"looks_like_pattern() error: {e}")
        is_pattern = None
    
    # Check boolean detection
    try:
        is_boolean = looks_like_boolean_expression(test_string)
        print(f"looks_like_boolean_expression(): {is_boolean}")
    except Exception as e:
        print(f"looks_like_boolean_expression() error: {e}")
        is_boolean = None
    
    print()
    print("=== Analysis ===")
    if is_pattern and not is_boolean:
        print("❌ PROBLEM: Detected as pattern but NOT as boolean")
        print("   This will send it to pattern parser instead of boolean parser")
        print("   The pattern parser then fails on the '|' operators")
    elif is_boolean and not is_pattern:
        print("✅ CORRECT: Detected as boolean, not pattern")
    elif is_boolean and is_pattern:
        print("⚠️  AMBIGUOUS: Detected as both boolean AND pattern")
        print("   Order of checks in _try_advanced_patterns() matters")
    else:
        print("❓ NEITHER: Not detected as boolean OR pattern")
    
    print()
    print("=== Expected Behavior ===")
    print("This string should be:")
    print("- looks_like_boolean_expression(): True  (has '|' operators)")
    print("- looks_like_pattern(): False (or True but boolean checked first)")


def test_simpler_cases():
    """Test simpler cases to understand the logic."""
    if not IMPORTS_AVAILABLE:
        return
    
    print("\n=== Testing Simpler Cases ===")
    
    test_cases = [
        'contains:"simple pattern"',
        'contains:"A" | contains:"B"',
        'contains:"text with, comma"',
        'contains:"A",contains:"B"',  # Comma-separated
    ]
    
    for test_str in test_cases:
        try:
            is_pattern = looks_like_pattern(test_str)
            is_boolean = looks_like_boolean_expression(test_str)
            print(f"'{test_str}':")
            print(f"  Pattern: {is_pattern}, Boolean: {is_boolean}")
        except Exception as e:
            print(f"'{test_str}': Error - {e}")


if __name__ == "__main__":
    test_problematic_string()
    test_simpler_cases()
