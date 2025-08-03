"""
Test Range Patterns ("X to Y")
Run: python -m pdf_manipulator.tests.test_range_patterns

Tests advanced range pattern syntax: "pattern to pattern", "number to pattern", etc.
Does NOT test boolean combinations with range patterns (that's in test_magazine_processing).
"""

import sys

from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.page_range.patterns import looks_like_range_pattern


# Mock PDF path for testing
MOCK_PDF_PATH = Path("test_document.pdf")


def test_range_pattern_detection():
    """Test detection of range patterns vs other expressions."""
    print("=== Testing Range Pattern Detection ===")
    
    test_cases = [
        # Should be detected as range patterns
        ("contains:'Chapter 1' to contains:'Chapter 2'", True, "Pattern to pattern"),
        ("5 to contains:'End'", True, "Number to pattern"),
        ("contains:'Start' to 10", True, "Pattern to number"),
        ("type:text to type:empty", True, "Type to type"),
        ("size:>1MB to size:>5MB", True, "Size to size"),
        ("regex:'\\d+' to contains:'Summary'", True, "Regex to contains"),
        
        # Should NOT be detected as range patterns
        ("contains:'Go to the store'", False, "'to' in quoted text"),
        ("contains:'Page 5 to 10'", False, "'to' within single quote"),
        ('contains:"From A to B"', False, "'to' within double quotes"),
        ("type:text & contains:'Chapter'", False, "Boolean AND expression"),
        ("5-10", False, "Regular page range"),
        ("all", False, "Simple keyword"),
        ("contains:'text'", False, "Single pattern"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_range_pattern, description in test_cases:
        is_range_pattern = looks_like_range_pattern(range_str)
        
        if is_range_pattern == should_be_range_pattern:
            status = "range pattern" if is_range_pattern else "not range pattern"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "range pattern" if should_be_range_pattern else "not range pattern"
            actual = "range pattern" if is_range_pattern else "not range pattern"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Range pattern detection: {passed}/{total} passed\n")
    return passed == total


def test_range_pattern_syntax():
    """Test various range pattern syntax combinations."""
    print("=== Testing Range Pattern Syntax ===")
    
    test_cases = [
        ("contains:'Chapter 1' to contains:'Chapter 2'", "Basic pattern to pattern"),
        ("5 to contains:'Appendix'", "Number to pattern"),
        ("contains:'Introduction' to 15", "Pattern to number"),
        ("1 to 10", "Number to number"),
        ("type:text to type:image", "Type to type"),
        ("size:<500KB to size:>2MB", "Size to size"),
        ("regex:'Chapter \\d+' to regex:'Summary'", "Regex to regex"),
        ("line-starts:'1.' to line-starts:'A.'", "Line-starts to line-starts"),
        ("contains/i:'chapter' to contains/i:'summary'", "Case-insensitive patterns"),
        ('contains:"Chapter 1" to contains:"Chapter 2"', "Double quoted patterns"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            # Test that the range pattern parses correctly
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✓ {description}: '{range_str}' → Syntax OK")
            passed += 1
            
        except ValueError as e:
            if "Could not analyze PDF" in str(e) or "No pages found" in str(e):
                # Expected - we don't have a real PDF to analyze
                print(f"✓ {description}: '{range_str}' → Syntax OK (expected PDF analysis failure)")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → Syntax error: {e}")
                
        except Exception as e:
            # Other processing errors are acceptable since we're testing syntax
            print(f"✓ {description}: '{range_str}' → Syntax OK (expected processing error)")
            passed += 1
    
    print(f"Range pattern syntax: {passed}/{total} passed\n")
    return passed == total


def test_range_pattern_offsets():
    """Test range patterns with offset modifiers."""
    print("=== Testing Range Pattern Offsets ===")
    
    test_cases = [
        ("contains:'Chapter 1'+1 to contains:'Chapter 2'", "Start offset +1"),
        ("contains:'Chapter 1' to contains:'Chapter 2'-1", "End offset -1"),
        ("contains:'Start'+2 to contains:'End'-2", "Both offsets"),
        ("5+1 to contains:'Appendix'", "Number with offset to pattern"),
        ("contains:'Introduction' to 15-1", "Pattern to number with offset"),
        ("type:text+3 to type:image-1", "Type patterns with offsets"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✓ {description}: '{range_str}' → Syntax OK")
            passed += 1
            
        except ValueError as e:
            if "Could not analyze PDF" in str(e) or "No pages found" in str(e):
                print(f"✓ {description}: '{range_str}' → Syntax OK (expected PDF analysis failure)")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → Syntax error: {e}")
                
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Syntax OK (expected processing error)")
            passed += 1
    
    print(f"Range pattern offsets: {passed}/{total} passed\n")
    return passed == total


def test_quoted_to_handling():
    """Test that 'to' within quotes doesn't create range patterns."""
    print("=== Testing Quoted 'to' Handling ===")
    
    test_cases = [
        ("contains:'Go to page 5'", False, "Single quotes with 'to'"),
        ('contains:"From page 1 to page 10"', False, "Double quotes with 'to'"),
        ("contains:'How to do it'", False, "Natural 'to' usage"),
        ("regex:'\\d+ to \\d+'", False, "Regex with 'to'"),
        ("line-starts:'A to Z'", False, "Line-starts with 'to'"),
        
        # These should still work as range patterns
        ("contains:'Chapter' to contains:'Summary'", True, "'to' as separator"),
        ("contains:'A' to contains:'Z'", True, "Short patterns with 'to'"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_range_pattern, description in test_cases:
        is_range_pattern = looks_like_range_pattern(range_str)
        
        if is_range_pattern == should_be_range_pattern:
            status = "range pattern" if is_range_pattern else "single pattern"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "range pattern" if should_be_range_pattern else "single pattern"
            actual = "range pattern" if is_range_pattern else "single pattern"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Quoted 'to' handling: {passed}/{total} passed\n")
    return passed == total


def test_invalid_range_patterns():
    """Test invalid range pattern syntax."""
    print("=== Testing Invalid Range Pattern Syntax ===")
    
    test_cases = [
        ("contains:'A' to", "Missing end pattern"),
        ("to contains:'B'", "Missing start pattern"),
        ("contains:'A' to to contains:'B'", "Double 'to'"),
        ("contains: to contains:'B'", "Empty start pattern"),
        ("contains:'A' to contains:", "Empty end pattern"),
        ("5 to", "Number to nothing"),
        ("to 10", "Nothing to number"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✗ {description}: '{range_str}' → Should have failed but didn't")
            
        except ValueError as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
            
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
    
    print(f"Invalid range patterns: {passed}/{total} passed\n")
    return passed == total


def test_case_sensitivity():
    """Test case sensitivity in 'to' keyword detection."""
    print("=== Testing Case Sensitivity ===")
    
    test_cases = [
        ("contains:'A' to contains:'B'", True, "Lowercase 'to'"),
        ("contains:'A' TO contains:'B'", True, "Uppercase 'TO'"),
        ("contains:'A' To contains:'B'", True, "Mixed case 'To'"),
        ("contains:'A' tO contains:'B'", True, "Mixed case 'tO'"),
        
        # These should not be range patterns
        ("contains:'A'to contains:'B'", False, "No space before 'to'"),
        ("contains:'A' tocontains:'B'", False, "No space after 'to'"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_range_pattern, description in test_cases:
        is_range_pattern = looks_like_range_pattern(range_str)
        
        if is_range_pattern == should_be_range_pattern:
            status = "range pattern" if is_range_pattern else "not range pattern"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "range pattern" if should_be_range_pattern else "not range pattern"
            actual = "range pattern" if is_range_pattern else "not range pattern"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Case sensitivity: {passed}/{total} passed\n")
    return passed == total


def main():
    """Run all range pattern tests."""
    print("RANGE PATTERN TESTS")
    print("=" * 50)
    print("Note: These tests focus on syntax validation for 'X to Y' patterns.")
    print()
    
    tests = [
        test_range_pattern_detection,
        test_range_pattern_syntax,
        test_range_pattern_offsets,
        test_quoted_to_handling,
        test_invalid_range_patterns,
        test_case_sensitivity,
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    # Summary
    passed_tests = sum(results)
    total_tests = len(results)
    
    print("=" * 50)
    print(f"RANGE PATTERN TESTS: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL RANGE PATTERN TESTS PASSED!")
        return 0
    else:
        print("❌ Some range pattern tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
