#!/usr/bin/env python3
"""
Quick verification that reverse ranges are working correctly after the create_ordered_group fix.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the canonical function from operations (no more duplicates!)
from pdf_manipulator.core.operations import get_ordered_pages_from_groups

# Simulated classes for testing the fix
class PageGroup:
    def __init__(self, pages, is_range, original_spec, preserve_order=False):
        self.pages = pages
        self.is_range = is_range
        self.original_spec = original_spec
        self.preserve_order = preserve_order

def test_reverse_ranges():
    """Test that reverse ranges work correctly."""
    print("=== Testing Fixed Reverse Range Logic ===")
    
    test_cases = [
        # (pages, is_range, preserve_order, expected_result, description)
        ([10, 9, 8, 7], True, False, [10, 9, 8, 7], "Reverse range (is_range=True)"),
        ([5, 6, 7, 8], True, False, [5, 6, 7, 8], "Forward range (is_range=True)"),
        ([10, 5, 15], False, True, [10, 5, 15], "Preserve order (is_range=False, preserve_order=True)"),
        ([10, 5, 15], False, False, [5, 10, 15], "No special handling (should sort)"),
        ([20], False, False, [20], "Single page"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for pages, is_range, preserve_order, expected, description in test_cases:
        group = PageGroup(pages, is_range, "test", preserve_order)
        result = get_ordered_pages_from_groups([group])
        
        if result == expected:
            print(f"✓ {description}: {pages} → {result}")
            passed += 1
        else:
            print(f"✗ {description}: {pages} → {result} (expected {expected})")
    
    print(f"\nReverse range fix test: {passed}/{total} passed")
    return passed == total

def test_realistic_scenarios():
    """Test realistic parsing scenarios with proper is_range flags."""
    print("\n=== Testing Realistic Scenarios ===")
    
    scenarios = [
        # Test range detection and ordering
        {
            'name': 'Simple forward range',
            'groups': [PageGroup([5, 6, 7, 8], True, "5-8")],
            'expected': [5, 6, 7, 8]
        },
        {
            'name': 'Simple reverse range', 
            'groups': [PageGroup([10, 9, 8, 7], True, "10-7")],
            'expected': [10, 9, 8, 7]
        },
        {
            'name': 'Mixed comma-separated with order preservation',
            'groups': [
                PageGroup([10], False, "10", preserve_order=True),
                PageGroup([5], False, "5", preserve_order=True), 
                PageGroup([15], False, "15", preserve_order=True)
            ],
            'expected': [10, 5, 15]
        },
        {
            'name': 'Mixed ranges and individuals',
            'groups': [
                PageGroup([1, 2, 3], True, "1-3"),
                PageGroup([20], False, "20"),
                PageGroup([15, 14], True, "15-14")
            ],
            'expected': [1, 2, 3, 20, 15, 14]  # Ranges preserve order, individual sorts within context
        }
    ]
    
    passed = 0
    total = len(scenarios)
    
    for scenario in scenarios:
        result = get_ordered_pages_from_groups(scenario['groups'])
        if result == scenario['expected']:
            print(f"✓ {scenario['name']}: {result}")
            passed += 1
        else:
            print(f"✗ {scenario['name']}: got {result}, expected {scenario['expected']}")
    
    print(f"\nRealistic scenarios: {passed}/{total} passed")
    return passed == total

def test_empty_and_edge_cases():
    """Test empty groups and edge cases."""
    print("\n=== Testing Empty Groups and Edge Cases ===")
    
    test_cases = [
        {
            'name': 'Empty groups list',
            'groups': [],
            'fallback': {1, 3, 5},
            'expected': [1, 3, 5]  # Should sort fallback
        },
        {
            'name': 'Groups with empty pages',
            'groups': [
                PageGroup([1, 2], True, "1-2"),
                PageGroup([], False, "empty"),  # Empty group
                PageGroup([5], False, "5")
            ],
            'expected': [1, 2, 5]  # Should skip empty group
        },
        {
            'name': 'Single page groups',
            'groups': [
                PageGroup([10], False, "10"),
                PageGroup([5], False, "5"),
                PageGroup([1], False, "1")
            ],
            'expected': [1, 5, 10]  # Should sort individual pages without preserve_order
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for case in test_cases:
        fallback = case.get('fallback', None)
        result = get_ordered_pages_from_groups(case['groups'], fallback)
        if result == case['expected']:
            print(f"✓ {case['name']}: {result}")
            passed += 1
        else:
            print(f"✗ {case['name']}: got {result}, expected {case['expected']}")
    
    print(f"\nEdge cases: {passed}/{total} passed")
    return passed == total

def main():
    """Run all tests."""
    print("🔧 Testing get_ordered_pages_from_groups function")
    print("   Using canonical implementation from operations.py")
    print("=" * 60)
    
    all_passed = True
    
    tests = [
        test_reverse_ranges,
        test_realistic_scenarios,
        test_empty_and_edge_cases
    ]
    
    for test_func in tests:
        if not test_func():
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! The function works correctly.")
    else:
        print("❌ Some tests failed. Review the implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


# End of file #
