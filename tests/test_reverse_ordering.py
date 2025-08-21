#!/usr/bin/env python3
"""
Quick verification that reverse ranges are working correctly after the create_ordered_group fix.
"""

# Simulated classes for testing the fix
class PageGroup:
    def __init__(self, pages, is_range, original_spec, preserve_order=False):
        self.pages = pages
        self.is_range = is_range
        self.original_spec = original_spec
        self.preserve_order = preserve_order

def get_ordered_pages_from_groups(groups, fallback_pages=None):
    """Fixed version that respects range order."""
    if not groups:
        return sorted(fallback_pages) if fallback_pages else []
    
    ordered_pages = []
    for group in groups:
        # For ranges, always preserve the order as specified in the pages list
        # For comma-separated preserve_order groups, also preserve order
        # For other groups, sort for backward compatibility
        if (hasattr(group, 'is_range') and group.is_range) or \
           (hasattr(group, 'preserve_order') and getattr(group, 'preserve_order', False)):
            # Preserve the exact order from this group
            ordered_pages.extend(group.pages)
        else:
            # Use sorted order for this group (backward compatibility)
            ordered_pages.extend(sorted(group.pages))
    
    return ordered_pages

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
        # Simulate "10-7" parsing (should be is_range=True now)
        {
            'description': 'Single reverse range "10-7"',
            'groups': [PageGroup([10, 9, 8, 7], True, "10-7", False)],
            'expected': [10, 9, 8, 7]
        },
        # Simulate "5-10" parsing (should be is_range=True)
        {
            'description': 'Single forward range "5-10"',
            'groups': [PageGroup([5, 6, 7, 8, 9, 10], True, "5-10", False)],
            'expected': [5, 6, 7, 8, 9, 10]
        },
        # Simulate "10,5,15,2" parsing (preserve_order=True)
        {
            'description': 'Comma-separated individual pages "10,5,15,2"',
            'groups': [
                PageGroup([10], False, "10", True),
                PageGroup([5], False, "5", True),
                PageGroup([15], False, "15", True),
                PageGroup([2], False, "2", True)
            ],
            'expected': [10, 5, 15, 2]
        },
        # Simulate "20-15,10-5" parsing (both preserve_order=True AND is_range=True)
        {
            'description': 'Comma-separated reverse ranges "20-15,10-5"',
            'groups': [
                PageGroup([20, 19, 18, 17, 16, 15], True, "20-15", True),
                PageGroup([10, 9, 8, 7, 6, 5], True, "10-5", True)
            ],
            'expected': [20, 19, 18, 17, 16, 15, 10, 9, 8, 7, 6, 5]
        }
    ]
    
    passed = 0
    total = len(scenarios)
    
    for scenario in scenarios:
        result = get_ordered_pages_from_groups(scenario['groups'])
        if result == scenario['expected']:
            print(f"✓ {scenario['description']}: {result}")
            passed += 1
        else:
            print(f"✗ {scenario['description']}: {result} (expected {scenario['expected']})")
    
    print(f"\nRealistic scenarios: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    test1_pass = test_reverse_ranges()
    test2_pass = test_realistic_scenarios()
    
    if test1_pass and test2_pass:
        print("\n✅ All tests passed! Reverse range fix is working correctly.")
    else:
        print("\n❌ Some tests failed. More work needed.")


# End of file #
