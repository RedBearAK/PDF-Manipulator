#!/usr/bin/env python3
"""
Test module for numeric page reordering functionality.
File: tests/test_numeric_reordering.py

Usage:  python test_numeric_reordering.py
        pytest test_numeric_reordering.py
"""

import sys
from pathlib import Path
from rich.console import Console

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.page_range.page_group import PageGroup, create_ordered_group, create_range_group
from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser
from pdf_manipulator.core.operations import get_ordered_pages_from_groups

console = Console()


def test_basic_reordering() -> bool:
    """Test basic numeric reordering functionality."""
    print("=== Testing Basic Numeric Reordering ===")
    
    # Test cases: (input, expected_order, description)
    test_cases = [
        ("10,5,15,2", [10, 5, 15, 2], "Non-sequential individual pages"),
        ("3,1,4,1", [3, 1, 4, 1], "Repeated pages (should preserve duplicates in input order)"),
        ("20,10,30", [20, 10, 30], "Descending then ascending"),
        ("1", [1], "Single page"),
        ("5-8", [5, 6, 7, 8], "Forward range should remain sequential"),
        ("10-7", [10, 9, 8, 7], "Reverse range should be sequential in reverse"),
        ("50-1", list(range(50, 0, -1)), "Full document reverse"),
        ("20-15,10-5", [20, 19, 18, 17, 16, 15, 10, 9, 8, 7, 6, 5], "Multiple reverse ranges"),
        ("1-5,10-6", [1, 2, 3, 4, 5, 10, 9, 8, 7, 6], "Mixed forward and reverse ranges"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_range, expected_order, description in test_cases:
        try:
            # Create fresh parser for each test to avoid state accumulation
            parser = PageRangeParser(total_pages=50)
            pages_set, desc, groups = parser.parse(input_range)
            actual_order = get_ordered_pages_from_groups(groups, pages_set)
            
            if actual_order == expected_order:
                print(f"✓ {description}: '{input_range}' → {actual_order}")
                passed += 1
            else:
                print(f"✗ {description}: '{input_range}'")
                print(f"    Expected: {expected_order}")
                print(f"    Got:      {actual_order}")
                
        except Exception as e:
            print(f"✗ {description}: '{input_range}' → Exception: {e}")
    
    print(f"Basic reordering: {passed}/{total} passed\n")
    return passed == total


def test_preserve_order_flag() -> bool:
    """Test that preserve_order flag works correctly.""" 
    print("=== Testing Preserve Order Flag ===")
    
    success = True
    
    # Test 1: preserve_order=True should maintain input order
    try:
        pages = [10, 5, 15, 2]
        group_preserve = create_ordered_group(pages, "test", preserve_order=True)
        
        if group_preserve.pages == [10, 5, 15, 2] and group_preserve.preserve_order:
            print("✓ preserve_order=True maintains input order")
        else:
            print(f"✗ preserve_order=True failed: {group_preserve.pages}, preserve_order={group_preserve.preserve_order}")
            success = False
            
    except Exception as e:
        print(f"✗ preserve_order=True test crashed: {e}")
        success = False
    
    # Test 2: preserve_order=False should sort
    try:
        pages = [10, 5, 15, 2]
        group_sort = create_ordered_group(pages, "test", preserve_order=False)
        
        if group_sort.pages == [2, 5, 10, 15] and not group_sort.preserve_order:
            print("✓ preserve_order=False sorts pages")
        else:
            print(f"✗ preserve_order=False failed: {group_sort.pages}, preserve_order={group_sort.preserve_order}")
            success = False
            
    except Exception as e:
        print(f"✗ preserve_order=False test crashed: {e}")
        success = False
    
    # Test 3: Range group should always be sequential
    try:
        range_group = create_range_group(5, 10, "5-10")
        
        if range_group.pages == [5, 6, 7, 8, 9, 10] and range_group.is_range:
            print("✓ Range groups maintain sequential order")
        else:
            print(f"✗ Range group failed: {range_group.pages}, is_range={range_group.is_range}")
            success = False
            
    except Exception as e:
        print(f"✗ Range group test crashed: {e}")
        success = False
    
    print(f"Preserve order flag: {'PASSED' if success else 'FAILED'}\n")
    return success


def test_mixed_groups() -> bool:
    """Test handling of mixed groups with different order preferences."""
    print("=== Testing Mixed Groups ===")
    
    try:
        # Create groups with different order preferences
        group1 = PageGroup([10, 5, 15], False, "custom", preserve_order=True)
        group2 = PageGroup([20, 1, 8], False, "sorted", preserve_order=False) 
        group3 = create_range_group(25, 27, "25-27")  # Range is always sequential
        
        groups = [group1, group2, group3]
        all_pages = {1, 5, 8, 10, 15, 20, 25, 26, 27}
        
        ordered_pages = get_ordered_pages_from_groups(groups, all_pages)
        
        # Expected: [10, 5, 15] + [1, 8, 20] + [25, 26, 27]
        expected = [10, 5, 15, 1, 8, 20, 25, 26, 27]
        
        if ordered_pages == expected:
            print(f"✓ Mixed groups handled correctly: {ordered_pages}")
            return True
        else:
            print(f"✗ Mixed groups failed:")
            print(f"    Expected: {expected}")
            print(f"    Got:      {ordered_pages}")
            return False
            
    except Exception as e:
        print(f"✗ Mixed groups test crashed: {e}")
        return False


def test_comma_detection() -> bool:
    """Test detection of when to preserve comma-separated order."""
    print("=== Testing Comma Order Detection ===")
    
    parser = PageRangeParser(total_pages=50)
    
    test_cases = [
        # Should preserve order (pure numeric specs)
        ("10,5,15,2", True, "Individual numbers"),
        ("5-8,10,3-6", True, "Mixed ranges and numbers"),
        ("first 3,last 2,10", True, "Special keywords with numbers"),
        ("::2,5-10", True, "Slicing with ranges"),
        
        # Should NOT preserve order (for now - until smart selector chaining is implemented)
        ("contains:'Chapter',type:text", False, "Smart selectors (not yet implemented)"),
        ("5", False, "Single item (no comma)"),
        ("5-10", False, "Single range (no comma)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_range, should_preserve, description in test_cases:
        try:
            detected = parser._should_preserve_comma_order(input_range)
            
            if detected == should_preserve:
                status = "preserve order" if detected else "standard processing"
                print(f"✓ {description}: '{input_range}' → {status}")
                passed += 1
            else:
                expected = "preserve order" if should_preserve else "standard processing"
                actual = "preserve order" if detected else "standard processing"
                print(f"✗ {description}: '{input_range}' → Expected {expected}, got {actual}")
                
        except Exception as e:
            print(f"✗ {description}: '{input_range}' → Exception: {e}")
    
    print(f"Comma detection: {passed}/{total} passed\n")
    return passed == total


def test_reverse_ranges() -> bool:
    """Test reverse range functionality specifically."""
    print("=== Testing Reverse Range Functionality ===")
    
    test_cases = [
        # Reverse ranges
        ("10-5", [10, 9, 8, 7, 6, 5], "Basic reverse range"),
        ("50-1", list(range(50, 0, -1)), "Full document reverse"),
        ("20-20", [20], "Single page range (start=end)"),
        ("25-15", [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15], "Medium reverse range"),
        
        # Mixed forward and reverse
        ("1-5,10-6", [1, 2, 3, 4, 5, 10, 9, 8, 7, 6], "Forward then reverse"),
        ("20-15,5-10", [20, 19, 18, 17, 16, 15, 5, 6, 7, 8, 9, 10], "Reverse then forward"),
        ("30-25,20,15-10,5", [30, 29, 28, 27, 26, 25, 20, 15, 14, 13, 12, 11, 10, 5], "Complex mixed"),
        
        # Practical examples
        ("50-40", [50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40], "Last 11 pages in reverse"),
        ("10-1,20-11", list(range(10, 0, -1)) + list(range(20, 10, -1)), "Two reverse ranges"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_range, expected_order, description in test_cases:
        try:
            # Create fresh parser for each test
            parser = PageRangeParser(total_pages=50)
            pages_set, desc, groups = parser.parse(input_range)
            actual_order = get_ordered_pages_from_groups(groups, pages_set)
            
            if actual_order == expected_order:
                print(f"✓ {description}: '{input_range}' → {actual_order}")
                passed += 1
            else:
                print(f"✗ {description}: '{input_range}'")
                print(f"    Expected: {expected_order}")
                print(f"    Got:      {actual_order}")
                
        except Exception as e:
            print(f"✗ {description}: '{input_range}' → Exception: {e}")
    
    print(f"Reverse ranges: {passed}/{total} passed\n")
    return passed == total


def test_backward_compatibility() -> bool:
    """Test that existing functionality still works."""
    print("=== Testing Backward Compatibility ===")
    
    parser = PageRangeParser(total_pages=50)
    
    test_cases = [
        ("all", list(range(1, 51)), "All pages"),
        ("5-10", [5, 6, 7, 8, 9, 10], "Simple range"),
        ("first 3", [1, 2, 3], "First N pages"),
        ("last 2", [49, 50], "Last N pages"),
        ("1,3,5", [1, 3, 5], "Individual pages (no reordering expected in backward compatibility)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_range, expected_pages, description in test_cases:
        try:
            pages_set, desc, groups = parser.parse(input_range)
            actual_pages = get_ordered_pages_from_groups(groups, pages_set)
            
            if actual_pages == expected_pages:
                print(f"✓ {description}: '{input_range}' → {actual_pages}")
                passed += 1
            else:
                print(f"✗ {description}: '{input_range}' → Expected {expected_pages}, got {actual_pages}")
                
        except Exception as e:
            print(f"✗ {description}: '{input_range}' → Exception: {e}")
    
    print(f"Backward compatibility: {passed}/{total} passed\n")
    return passed == total


def main() -> bool:
    """Run all tests and return overall success."""
    console.print("[cyan]Testing Numeric Page Reordering Implementation[/cyan]\n")
    
    tests = [
        test_basic_reordering,
        test_reverse_ranges,
        test_preserve_order_flag,
        test_mixed_groups,
        test_comma_detection,
        test_backward_compatibility,
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            console.print(f"[red]Test {test_func.__name__} crashed: {e}[/red]")
    
    console.print(f"\n[cyan]Overall Results: {passed_tests}/{total_tests} test groups passed[/cyan]")
    
    if passed_tests == total_tests:
        console.print("[green]✓ All tests passed! Numeric reordering is working correctly.[/green]")
        return True
    else:
        console.print("[red]✗ Some tests failed. Review implementation.[/red]")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


# End of file #
