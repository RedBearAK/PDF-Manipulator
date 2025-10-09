#!/usr/bin/env python3
"""
Test the format_page_ranges function.
File: test_format_page_ranges.py

Quick test to verify the page range formatting works correctly.
"""


def format_page_ranges(pages: set[int]) -> str:
    """Format page numbers into compact range notation."""
    if not pages:
        return "none"
    
    sorted_pages = sorted(pages)
    ranges = []
    start = sorted_pages[0]
    end = start
    
    for page in sorted_pages[1:]:
        if page == end + 1:
            end = page
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = page
            end = page
    
    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ", ".join(ranges)


def test_format_page_ranges():
    """Test the format_page_ranges function with various inputs."""
    
    test_cases = [
        # (input_set, expected_output, description)
        (set(), "none", "Empty set"),
        ({1}, "1", "Single page"),
        ({1, 2, 3}, "1-3", "Simple consecutive range"),
        ({1, 3, 5}, "1, 3, 5", "Non-consecutive pages"),
        ({1, 2, 3, 5, 7, 8, 9}, "1-3, 5, 7-9", "Mixed ranges and singles"),
        ({1, 2, 3, 4, 5}, "1-5", "All consecutive"),
        ({10, 15, 20, 25}, "10, 15, 20, 25", "All singles with gaps"),
        ({1, 2, 4, 5, 6, 10, 11}, "1-2, 4-6, 10-11", "Multiple ranges"),
        ({100}, "100", "Large single page number"),
        ({1, 2, 3, 10, 11, 12, 20, 21, 22}, "1-3, 10-12, 20-22", "Multiple 3-page ranges"),
    ]
    
    print("Testing format_page_ranges function:\n")
    
    passed = 0
    failed = 0
    
    for input_set, expected, description in test_cases:
        result = format_page_ranges(input_set)
        
        if result == expected:
            print(f"✓ {description}")
            print(f"  Input: {sorted(input_set) if input_set else 'empty'}")
            print(f"  Output: {result}")
            passed += 1
        else:
            print(f"✗ {description}")
            print(f"  Input: {sorted(input_set) if input_set else 'empty'}")
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run the tests."""
    success = test_format_page_ranges()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())


# End of file #
