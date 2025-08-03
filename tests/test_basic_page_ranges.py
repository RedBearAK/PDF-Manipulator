"""
Test Basic Page Range Parsing
Run: python -m pdf_manipulator.tests.test_basic_page_ranges

Tests fundamental page range parsing: numbers, ranges, slicing, first/last.
Does NOT test patterns, boolean expressions, or advanced features.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.core.parser import parse_page_range


def test_single_pages():
    """Test single page numbers."""
    print("=== Testing Single Pages ===")
    
    test_cases = [
        ("5", 10, {5}, "Single page 5"),
        ("1", 10, {1}, "First page"),
        ("10", 10, {10}, "Last page"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Single pages: {passed}/{total} passed\n")
    return passed == total


def test_ranges():
    """Test page ranges with different syntaxes."""
    print("=== Testing Page Ranges ===")
    
    test_cases = [
        ("3-7", 10, {3, 4, 5, 6, 7}, "Standard range 3-7"),
        ("3:7", 10, {3, 4, 5, 6, 7}, "Colon range 3:7"),
        ("3..7", 10, {3, 4, 5, 6, 7}, "Dotdot range 3..7"),
        ("1-3", 10, {1, 2, 3}, "Range from start"),
        ("8-10", 10, {8, 9, 10}, "Range to end"),
        ("5-5", 10, {5}, "Single page as range"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Ranges: {passed}/{total} passed\n")
    return passed == total


def test_open_ranges():
    """Test open-ended ranges."""
    print("=== Testing Open-Ended Ranges ===")
    
    test_cases = [
        ("3-", 10, {3, 4, 5, 6, 7, 8, 9, 10}, "Open end: 3 to end"),
        ("-7", 10, {1, 2, 3, 4, 5, 6, 7}, "Open start: start to 7"),
        ("8-", 10, {8, 9, 10}, "Near end: 8 to end"),
        ("-3", 10, {1, 2, 3}, "Near start: start to 3"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Open ranges: {passed}/{total} passed\n")
    return passed == total


def test_first_last():
    """Test first/last page selections."""
    print("=== Testing First/Last Selections ===")
    
    test_cases = [
        ("first 3", 10, {1, 2, 3}, "First 3 pages"),
        ("first-3", 10, {1, 2, 3}, "First 3 pages (dash syntax)"),
        ("last 2", 10, {9, 10}, "Last 2 pages"),
        ("last-2", 10, {9, 10}, "Last 2 pages (dash syntax)"),
        ("first 1", 10, {1}, "First 1 page"),
        ("last 1", 10, {10}, "Last 1 page"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"First/last: {passed}/{total} passed\n")
    return passed == total


def test_slicing():
    """Test step/slicing syntax."""
    print("=== Testing Slicing Syntax ===")
    
    test_cases = [
        ("::2", 10, {1, 3, 5, 7, 9}, "Odd pages (every 2nd from 1)"),
        ("2::2", 10, {2, 4, 6, 8, 10}, "Even pages (every 2nd from 2)"),
        ("1:6:2", 10, {1, 3, 5}, "Every 2nd from 1 to 6"),
        ("2:8:3", 10, {2, 5, 8}, "Every 3rd from 2 to 8"),
        ("5:10:1", 10, {5, 6, 7, 8, 9, 10}, "Every 1st from 5 to 10"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Slicing: {passed}/{total} passed\n")
    return passed == total


def test_multiple_ranges():
    """Test comma-separated multiple ranges."""
    print("=== Testing Multiple Ranges ===")
    
    test_cases = [
        ("1,3,5", 10, {1, 3, 5}, "Individual pages"),
        ("1-3,7", 10, {1, 2, 3, 7}, "Range plus single"),
        ("1-3,7,9-10", 10, {1, 2, 3, 7, 9, 10}, "Mixed ranges and singles"),
        ("first 2,last 2", 10, {1, 2, 9, 10}, "First and last"),
        ("2::2,1", 10, {1, 2, 4, 6, 8, 10}, "Even pages plus 1"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Multiple ranges: {passed}/{total} passed\n")
    return passed == total


def test_special_cases():
    """Test special keywords and edge cases."""
    print("=== Testing Special Cases ===")
    
    test_cases = [
        ("all", 10, {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, "All pages"),
        ("all", 5, {1, 2, 3, 4, 5}, "All pages (smaller PDF)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            
            if pages == expected_pages:
                print(f"✓ {description}: '{range_str}' → {sorted(pages)}")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → {sorted(pages)} (expected {sorted(expected_pages)})")
                
        except Exception as e:
            print(f"✗ {description}: '{range_str}' → ERROR: {e}")
    
    print(f"Special cases: {passed}/{total} passed\n")
    return passed == total


def test_error_cases():
    """Test invalid inputs that should raise errors."""
    print("=== Testing Error Cases ===")
    
    test_cases = [
        ("0", 10, "Page 0 (invalid)"),
        ("11", 10, "Page beyond range"),
        ("5-3", 10, "Invalid range (backwards)"),
        ("", 10, "Empty string"),
        ("abc", 10, "Non-numeric"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, total_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, total_pages)
            print(f"✗ {description}: '{range_str}' → Should have failed but got {sorted(pages)}")
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
    
    print(f"Error cases: {passed}/{total} passed\n")
    return passed == total


def main():
    """Run all basic page range tests."""
    print("BASIC PAGE RANGE PARSING TESTS")
    print("=" * 50)
    
    tests = [
        test_single_pages,
        test_ranges,
        test_open_ranges,
        test_first_last,
        test_slicing,
        test_multiple_ranges,
        test_special_cases,
        test_error_cases,
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    # Summary
    passed_tests = sum(results)
    total_tests = len(results)
    
    print("=" * 50)
    print(f"BASIC PAGE RANGE TESTS: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL BASIC PAGE RANGE TESTS PASSED!")
        return 0
    else:
        print("❌ Some basic page range tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
