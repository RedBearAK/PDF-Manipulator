#!/usr/bin/env python3
"""
Standalone test for group filtering logic.
This test doesn't require the full PDF manipulator codebase to be integrated.
Usage: python test_standalone_filtering.py
"""

import re
import sys

from pathlib import Path
from rich.console import Console


console = Console()


class PageGroup:
    """Standalone PageGroup class for testing."""
    def __init__(self, pages: list[int], is_range: bool, original_spec: str):
        self.pages = pages
        self.is_range = is_range
        self.original_spec = original_spec
    
    def __repr__(self):
        return f"PageGroup(pages={self.pages}, is_range={self.is_range}, spec='{self.original_spec}')"


def is_index_based_filter(criteria: str) -> bool:
    """Check if filter criteria is index-based (like '1,3,4')."""
    clean_criteria = re.sub(r'\s+', '', criteria)
    return bool(re.match(r'^[\d,\-]+$', clean_criteria))


def filter_by_indices(groups: list[PageGroup], indices_str: str) -> list[PageGroup]:
    """Filter groups by index positions (1-indexed)."""
    
    try:
        selected_indices = set()
        
        for part in indices_str.split(','):
            part = part.strip()
            if '-' in part and not part.startswith('-') and not part.endswith('-'):
                # Range like "1-3"
                start_str, end_str = part.split('-', 1)
                start_idx = int(start_str)
                end_idx = int(end_str)
                
                if start_idx > end_idx:
                    raise ValueError(f"Invalid range {part}: start > end")
                
                selected_indices.update(range(start_idx, end_idx + 1))
            else:
                # Single index
                selected_indices.add(int(part))
        
        # Filter groups (convert to 0-indexed for list access)
        filtered_groups = []
        for i, group in enumerate(groups):
            if (i + 1) in selected_indices:  # groups are 1-indexed in user input
                filtered_groups.append(group)
        
        # Warn about out-of-range indices
        max_index = len(groups)
        out_of_range = [idx for idx in selected_indices if idx < 1 or idx > max_index]
        if out_of_range:
            console.print(f"[yellow]Warning: Group indices out of range (1-{max_index}): {sorted(out_of_range)}[/yellow]")
        
        return filtered_groups
        
    except ValueError as e:
        raise ValueError(f"Invalid index filter '{indices_str}': {e}")


def validate_filter_syntax(filter_criteria: str) -> tuple[bool, str]:
    """Validate filter criteria syntax without requiring PDF access."""
    
    if not filter_criteria or not filter_criteria.strip():
        return True, ""
    
    criteria = filter_criteria.strip()
    
    # Check if index-based
    if is_index_based_filter(criteria):
        try:
            # Try to parse indices to validate syntax
            for part in criteria.split(','):
                part = part.strip()
                if '-' in part and not part.startswith('-') and not part.endswith('-'):
                    start_str, end_str = part.split('-', 1)
                    start_idx = int(start_str)
                    end_idx = int(end_str)
                    if start_idx > end_idx:
                        return False, f"Invalid range {part}: start > end"
                    if start_idx < 1:
                        return False, f"Group indices must be >= 1, found {start_idx}"
                else:
                    idx = int(part)
                    if idx < 1:
                        return False, f"Group indices must be >= 1, found {idx}"
            return True, ""
        except ValueError as e:
            return False, f"Invalid index syntax: {e}"
    
    # For content-based criteria, basic syntax validation
    if criteria.count('(') != criteria.count(')'):
        return False, "Mismatched parentheses"
    
    # Check for unmatched quotes
    single_quotes = criteria.count("'")
    double_quotes = criteria.count('"')
    if single_quotes % 2 != 0:
        return False, "Unmatched single quote"
    if double_quotes % 2 != 0:
        return False, "Unmatched double quote"
    
    if criteria.startswith(('&', '|')):
        return False, "Boolean operator missing left operand"
    
    if criteria.endswith(('&', '|')):
        return False, "Boolean operator missing right operand"
    
    return True, ""


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
        filtered = filter_by_indices(groups, "1,3,5")
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
        filtered = filter_by_indices(groups, "2-4")
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
        filtered = filter_by_indices(groups, "1,3-4")
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
        filtered = filter_by_indices(groups, "1,10")  # 10 is out of range
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
            is_index = is_index_based_filter(criteria)
            
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
    
    # Test 1: Empty groups list
    try:
        filtered = filter_by_indices([], "1,2,3")
        if len(filtered) == 0:
            print("  ✓ Empty groups list")
        else:
            print(f"  ✗ Empty groups list failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ Empty groups list error: {e}")
        success = False
    
    # Test 2: All indices out of range
    try:
        filtered = filter_by_indices(groups, "10,11,12")  # All out of range
        if len(filtered) == 0:
            print("  ✓ All indices out of range")
        else:
            print(f"  ✗ All out of range failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ All out of range error: {e}")
        success = False
    
    # Test 3: Single group, single index
    try:
        single_group = [PageGroup([1], False, "page1")]
        filtered = filter_by_indices(single_group, "1")
        if len(filtered) == 1 and filtered[0].pages == [1]:
            print("  ✓ Single group, single index")
        else:
            print(f"  ✗ Single group failed: got {len(filtered)} groups")
            success = False
    except Exception as e:
        print(f"  ✗ Single group error: {e}")
        success = False
    
    return success


def run_all_tests() -> bool:
    """Run all tests and return overall success."""
    console.print("\n[bold blue]Standalone Group Filtering Tests[/bold blue]")
    console.print("[dim]Testing core filtering logic without full codebase dependency[/dim]")
    
    tests = [
        test_index_detection,
        test_syntax_validation,
        test_index_based_filtering,
        test_empty_and_edge_cases,
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
        console.print("[dim]Core group filtering logic is working correctly[/dim]")
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


if __name__ == "__main__":
    sys.exit(main())
