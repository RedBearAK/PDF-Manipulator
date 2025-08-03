#!/usr/bin/env python3
"""
Test module for group filtering functionality.
Usage:  python test_group_filtering.py
        pytest test_group_filtering.py
"""

import sys
import tempfile

from pathlib import Path
from rich.console import Console

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.page_range.group_filtering import (
    filter_page_groups,
    validate_filter_syntax,
    describe_filter_result,
    _is_index_based_filter,
    _filter_by_indices
)


console = Console()


def create_test_groups() -> list[PageGroup]:
    """Create test page groups for filtering tests."""
    return [
        PageGroup([1], False, "page1"),                    # Group 1: single page
        PageGroup([2, 3, 4], True, "pages2-4"),          # Group 2: small range 
        PageGroup([5], False, "page5"),                    # Group 3: single page
        PageGroup([7, 8, 9, 10], True, "pages7-10"),     # Group 4: larger range
        PageGroup([12, 13], True, "pages12-13"),         # Group 5: small range
    ]


def test_index_based_filtering() -> bool:
    """Test index-based filtering with various patterns."""
    print("Testing index-based filtering...")
    success = True
    
    groups = create_test_groups()
    
    # Test 1: Simple index selection
    try:
        filtered = _filter_by_indices(groups, "1,3,5")
        expected_pages = [[1], [5], [12, 13]]  # Groups 1, 3, 5
        actual_pages = [group.pages for group in filtered]
        
        if actual_pages == expected_pages:
            print("  ✓ Simple index selection (1,3,5)")
        else:
            print(f"  ✗ Simple index selection failed: expected {expected_pages}, got {actual_pages}")
            success = False
    except Exception as e:
        print(f"  ✗ Simple index selection error: {e}")
        success = False
    
    # Test 2: Range index selection
    try:
        filtered = _filter_by_indices(groups, "2-4")
        expected_pages = [[2, 3, 4], [5], [7, 8, 9, 10]]  # Groups 2, 3, 4
        actual_pages = [group.pages for group in filtered]
        
        if actual_pages == expected_pages:
            print("  ✓ Range index selection (2-4)")
        else:
            print(f"  ✗ Range index selection failed: expected {expected_pages}, got {actual_pages}")
            success = False
    except Exception as e:
        print(f"  ✗ Range index selection error: {e}")
        success = False
    
    # Test 3: Mixed index selection
    try:
        filtered = _filter_by_indices(groups, "1,3-4")
        expected_pages = [[1], [5], [7, 8, 9, 10]]  # Groups 1, 3, 4
        actual_pages = [group.pages for group in filtered]
        
        if actual_pages == expected_pages:
            print("  ✓ Mixed index selection (1,3-4)")
        else:
            print(f"  ✗ Mixed index selection failed: expected {expected_pages}, got {actual_pages}")
            success = False
    except Exception as e:
        print(f"  ✗ Mixed index selection error: {e}")
        success = False
    
    # Test 4: Out of range indices (should warn but not crash)
    try:
        filtered = _filter_by_indices(groups, "1,10")  # 10 is out of range
        if len(filtered) == 1 and filtered[0].pages == [1]:
            print("  ✓ Out of range handling")
        else:
            print(f"  ✗ Out of range handling failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ Out of range handling error: {e}")
        success = False
    
    return success


def test_syntax_validation() -> bool:
    """Test filter syntax validation."""
    print("Testing syntax validation...")
    success = True
    
    test_cases = [
        # Valid cases
        ("1,2,3", True, "simple indices"),
        ("1-3,5", True, "mixed indices"),
        ("contains:'test'", True, "simple pattern"),
        ("type:text & !type:empty", True, "boolean expression"),
        ("", True, "empty filter"),
        
        # Invalid cases  
        ("1,", False, "trailing comma"),
        ("3-1", False, "invalid range"),
        ("0,1,2", False, "zero index"),
        ("contains:'test", False, "unmatched quote"),
        ("& type:text", False, "leading operator"),
        ("type:text &", False, "trailing operator"),
        ("((", False, "unmatched parentheses"),
    ]
    
    for criteria, should_be_valid, description in test_cases:
        try:
            is_valid, error_msg = validate_filter_syntax(criteria)
            
            if is_valid == should_be_valid:
                status = "✓" if should_be_valid else "✓ (correctly rejected)"
                print(f"  {status} {description}: '{criteria}'")
            else:
                print(f"  ✗ {description} failed: '{criteria}' -> valid={is_valid}, expected={should_be_valid}")
                if error_msg:
                    print(f"      Error: {error_msg}")
                success = False
                
        except Exception as e:
            print(f"  ✗ {description} crashed: {e}")
            success = False
    
    return success


def test_index_detection() -> bool:
    """Test detection of index-based vs content-based filters."""
    print("Testing index detection...")
    success = True
    
    test_cases = [
        # Index-based
        ("1,2,3", True),
        ("1-5", True),
        ("1,3-5,7", True),
        ("  1 , 2 , 3  ", True),  # with whitespace
        
        # Content-based
        ("contains:'test'", False),
        ("type:text", False),
        ("1,2,contains:'test'", False),  # mixed
        ("all", False),
        ("!1-5", False),  # boolean operator
        ("(1-3)", False),  # parentheses
    ]
    
    for criteria, expected_is_index in test_cases:
        try:
            is_index = _is_index_based_filter(criteria)
            
            if is_index == expected_is_index:
                filter_type = "index" if expected_is_index else "content"
                print(f"  ✓ {filter_type}: '{criteria}'")
            else:
                print(f"  ✗ Detection failed: '{criteria}' -> {is_index}, expected {expected_is_index}")
                success = False
                
        except Exception as e:
            print(f"  ✗ Detection crashed for '{criteria}': {e}")
            success = False
    
    return success


def test_empty_and_edge_cases() -> bool:
    """Test edge cases like empty groups, empty filters, etc."""
    print("Testing edge cases...")
    success = True
    
    groups = create_test_groups()
    
    # Test 1: Empty filter
    try:
        filtered = filter_page_groups(groups, "", Path("dummy.pdf"), 10)
        if len(filtered) == len(groups):
            print("  ✓ Empty filter returns all groups")
        else:
            print(f"  ✗ Empty filter failed: got {len(filtered)} groups, expected {len(groups)}")
            success = False
    except Exception as e:
        print(f"  ✗ Empty filter error: {e}")
        success = False
    
    # Test 2: Empty groups list
    try:
        filtered = filter_page_groups([], "1,2,3", Path("dummy.pdf"), 10)
        if len(filtered) == 0:
            print("  ✓ Empty groups list")
        else:
            print(f"  ✗ Empty groups list failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ Empty groups list error: {e}")
        success = False
    
    # Test 3: All indices out of range
    try:
        filtered = _filter_by_indices(groups, "10,11,12")  # All out of range
        if len(filtered) == 0:
            print("  ✓ All indices out of range")
        else:
            print(f"  ✗ All out of range failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ All out of range error: {e}")
        success = False
    
    # Test 4: Single group, single index
    try:
        single_group = [PageGroup([1], False, "page1")]
        filtered = _filter_by_indices(single_group, "1")
        if len(filtered) == 1 and filtered[0].pages == [1]:
            print("  ✓ Single group, single index")
        else:
            print(f"  ✗ Single group failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ Single group error: {e}")
        success = False
    
    return success


def test_description_helper() -> bool:
    """Test the description helper function."""
    print("Testing description helper...")
    success = True
    
    test_cases = [
        (5, 5, "all", "All 5 groups match filter"),
        (5, 0, "contains:'missing'", "No groups match filter 'contains:'missing''"),
        (10, 3, "type:text", "Filtered 10 groups to 3 using 'type:text'"),
    ]
    
    for original, filtered, criteria, expected in test_cases:
        try:
            result = describe_filter_result(original, filtered, criteria)
            if result == expected:
                print(f"  ✓ Description: {original}→{filtered}")
            else:
                print(f"  ✗ Description failed: got '{result}', expected '{expected}'")
                success = False
        except Exception as e:
            print(f"  ✗ Description error: {e}")
            success = False
    
    return success


def run_all_tests() -> bool:
    """Run all tests and return overall success."""
    console.print("\n[bold blue]Group Filtering Tests[/bold blue]")
    
    tests = [
        test_index_detection,
        test_syntax_validation,
        test_index_based_filtering,
        test_empty_and_edge_cases,
        test_description_helper,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            print()  # Add spacing between test groups
        except Exception as e:
            console.print(f"[red]Test {test_func.__name__} crashed: {e}[/red]")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        console.print(f"[bold green]All {total} test groups passed! ✓[/bold green]")
        return True
    else:
        console.print(f"[bold red]{passed}/{total} test groups passed[/bold red]")
        return False


def main() -> int:
    """Main entry point."""
    try:
        success = run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Test runner crashed: {e}[/red]")
        return 1


# Support for both standalone and pytest execution
def test_main():
    """Entry point for pytest."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
