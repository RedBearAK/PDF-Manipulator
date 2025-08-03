#!/usr/bin/env python3
"""
Test module for advanced page selection pipeline.
Usage:  python test_advanced_selection.py
        pytest test_advanced_selection.py
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.advanced_page_selection import (
    create_advanced_description,
    validate_advanced_selection_args,
    _split_group_at_boundaries,
    _create_boundary_group
)

console = Console()


def create_mock_args(**kwargs) -> argparse.Namespace:
    """Create mock arguments for testing."""
    args = argparse.Namespace()
    
    # Set defaults
    args.extract_pages = None
    args.filter_matches = None
    args.group_start = None
    args.group_end = None
    
    # Apply overrides
    for key, value in kwargs.items():
        setattr(args, key, value)
    
    return args


def test_argument_validation() -> bool:
    """Test validation of advanced selection arguments."""
    print("Testing argument validation...")
    success = True
    
    test_cases = [
        # Valid cases
        ({"extract_pages": "1-5"}, True, "basic extraction"),
        ({"extract_pages": "1-5", "filter_matches": "1,2"}, True, "with filtering"),
        ({"extract_pages": "1-5", "group_start": "contains:'test'"}, True, "with boundaries"),
        ({"extract_pages": "1-5", "filter_matches": "1,2", "group_start": "contains:'test'"}, True, "all options"),
        
        # Invalid cases
        ({"filter_matches": "1,2"}, False, "filter without extraction"),
        ({"group_start": "contains:'test'"}, False, "boundaries without extraction"),
        ({"extract_pages": "1-5", "filter_matches": "1,"}, False, "invalid filter syntax"),
    ]
    
    for kwargs, should_be_valid, description in test_cases:
        try:
            args = create_mock_args(**kwargs)
            is_valid, error_msg = validate_advanced_selection_args(args)
            
            if is_valid == should_be_valid:
                status = "✓" if should_be_valid else "✓ (correctly rejected)"
                print(f"  {status} {description}")
            else:
                print(f"  ✗ {description} failed: valid={is_valid}, expected={should_be_valid}")
                if error_msg:
                    print(f"      Error: {error_msg}")
                success = False
                
        except Exception as e:
            print(f"  ✗ {description} crashed: {e}")
            success = False
    
    return success


def test_boundary_group_creation() -> bool:
    """Test creation of groups from boundary detection."""
    print("Testing boundary group creation...")
    success = True
    
    test_cases = [
        # (pages, original_spec, expected_is_range, description)
        ([1], "test", False, "single page"),
        ([1, 2, 3], "test", True, "consecutive pages"),
        ([1, 3, 5], "test", True, "non-consecutive pages"),
        ([], "test", False, "empty pages"),
    ]
    
    for pages, original_spec, expected_is_range, description in test_cases:
        try:
            group = _create_boundary_group(pages, original_spec)
            
            if group.pages == pages and group.is_range == expected_is_range:
                print(f"  ✓ {description}: {pages} -> is_range={group.is_range}")
            else:
                print(f"  ✗ {description} failed: pages={group.pages}, is_range={group.is_range}")
                print(f"      Expected: pages={pages}, is_range={expected_is_range}")
                success = False
                
        except Exception as e:
            print(f"  ✗ {description} crashed: {e}")
            success = False
    
    return success


def test_group_splitting() -> bool:
    """Test splitting groups at boundary points."""
    print("Testing group splitting at boundaries...")
    success = True
    
    # Test case: split a group at start boundaries
    try:
        original_group = PageGroup([1, 2, 3, 4, 5], True, "pages1-5")
        start_pages = {2, 4}  # Split at pages 2 and 4
        end_pages = set()
        
        result_groups = _split_group_at_boundaries(original_group, start_pages, end_pages)
        
        # Should get: [1], [2,3], [4,5]
        expected_page_lists = [[1], [2, 3], [4, 5]]
        actual_page_lists = [group.pages for group in result_groups]
        
        if actual_page_lists == expected_page_lists:
            print(f"  ✓ Start boundary splitting: {actual_page_lists}")
        else:
            print(f"  ✗ Start boundary splitting failed:")
            print(f"      Expected: {expected_page_lists}")
            print(f"      Got: {actual_page_lists}")
            success = False
            
    except Exception as e:
        print(f"  ✗ Start boundary splitting crashed: {e}")
        success = False
    
    # Test case: split a group at end boundaries  
    try:
        original_group = PageGroup([1, 2, 3, 4, 5], True, "pages1-5")
        start_pages = set()
        end_pages = {2, 4}  # End at pages 2 and 4
        
        result_groups = _split_group_at_boundaries(original_group, start_pages, end_pages)
        
        # Should get: [1,2], [3,4], [5]
        expected_page_lists = [[1, 2], [3, 4], [5]]
        actual_page_lists = [group.pages for group in result_groups]
        
        if actual_page_lists == expected_page_lists:
            print(f"  ✓ End boundary splitting: {actual_page_lists}")
        else:
            print(f"  ✗ End boundary splitting failed:")
            print(f"      Expected: {expected_page_lists}")
            print(f"      Got: {actual_page_lists}")
            success = False
            
    except Exception as e:
        print(f"  ✗ End boundary splitting crashed: {e}")
        success = False
    
    # Test case: no boundaries (should return original)
    try:
        original_group = PageGroup([1, 2, 3], True, "pages1-3")
        start_pages = set()
        end_pages = set()
        
        result_groups = _split_group_at_boundaries(original_group, start_pages, end_pages)
        
        if len(result_groups) == 1 and result_groups[0].pages == [1, 2, 3]:
            print(f"  ✓ No boundaries (unchanged): {result_groups[0].pages}")
        else:
            print(f"  ✗ No boundaries failed: got {len(result_groups)} groups")
            success = False
            
    except Exception as e:
        print(f"  ✗ No boundaries crashed: {e}")
        success = False
    
    return success


def test_description_creation() -> bool:
    """Test creation of advanced selection descriptions."""
    print("Testing description creation...")
    success = True
    
    test_cases = [
        # (args_kwargs, initial_desc, final_group_count, expected_pattern, description)
        ({"extract_pages": "1-5"}, "pages1-5", 1, "pages1-5", "basic extraction"),
        ({"extract_pages": "1-5", "filter_matches": "1,2"}, "pages1-5", 2, "pages1-5-1,2", "with index filter"),
        ({"extract_pages": "1-5", "group_start": "test"}, "pages1-5", 3, "pages1-5-start-split", "with group start"),
        ({"extract_pages": "1-5", "filter_matches": "type:text"}, "pages1-5", 2, "pages1-5-criteria", "with content filter"),
    ]
    
    for args_kwargs, initial_desc, final_group_count, expected_pattern, description in test_cases:
        try:
            args = create_mock_args(**args_kwargs)
            result = create_advanced_description(args, initial_desc, final_group_count)
            
            # Check that result contains expected elements (flexible matching)
            if isinstance(expected_pattern, str):
                # For basic cases, check exact match or reasonable similarity
                if result == expected_pattern or initial_desc in result:
                    print(f"  ✓ {description}: '{result}'")
                else:
                    print(f"  ✗ {description} failed: got '{result}', expected pattern '{expected_pattern}'")
                    success = False
            else:
                print(f"  ✓ {description}: '{result}' (pattern check)")
                
        except Exception as e:
            print(f"  ✗ {description} crashed: {e}")
            success = False
    
    return success


def test_edge_cases() -> bool:
    """Test edge cases for advanced selection."""
    print("Testing edge cases...")
    success = True
    
    # Test empty group handling
    try:
        empty_group = PageGroup([], False, "empty")
        start_pages = {1, 2}
        end_pages = {3}
        
        result = _split_group_at_boundaries(empty_group, start_pages, end_pages)
        
        if len(result) == 1 and result[0].pages == []:
            print("  ✓ Empty group handling")
        else:
            print(f"  ✗ Empty group handling failed: got {len(result)} groups")
            success = False
            
    except Exception as e:
        print(f"  ✗ Empty group handling crashed: {e}")
        success = False
    
    # Test single page group
    try:
        single_group = PageGroup([5], False, "page5")
        start_pages = {5}  # Boundary at the only page
        end_pages = set()
        
        result = _split_group_at_boundaries(single_group, start_pages, end_pages)
        
        if len(result) == 1 and result[0].pages == [5]:
            print("  ✓ Single page with boundary")
        else:
            print(f"  ✗ Single page with boundary failed: got {[g.pages for g in result]}")
            success = False
            
    except Exception as e:
        print(f"  ✗ Single page with boundary crashed: {e}")
        success = False
    
    # Test boundary outside group range
    try:
        group = PageGroup([10, 11, 12], True, "pages10-12")
        start_pages = {5, 15}  # Boundaries outside group range
        end_pages = set()
        
        result = _split_group_at_boundaries(group, start_pages, end_pages)
        
        if len(result) == 1 and result[0].pages == [10, 11, 12]:
            print("  ✓ Boundaries outside range")
        else:
            print(f"  ✗ Boundaries outside range failed: got {[g.pages for g in result]}")
            success = False
            
    except Exception as e:
        print(f"  ✗ Boundaries outside range crashed: {e}")
        success = False
    
    return success


def run_all_tests() -> bool:
    """Run all tests and return overall success."""
    console.print("\n[bold blue]Advanced Page Selection Tests[/bold blue]")
    
    tests = [
        test_argument_validation,
        test_boundary_group_creation,
        test_group_splitting,
        test_description_creation,
        test_edge_cases,
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
