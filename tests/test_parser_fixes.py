#!/usr/bin/env python3
"""
Quick test to verify the parser fixes work correctly.
"""

import sys
from pathlib import Path

# Simulated imports for testing - replace with actual imports
class PageGroup:
    def __init__(self, pages, is_range, original_spec, preserve_order=False):
        self.pages = pages
        self.is_range = is_range
        self.original_spec = original_spec
        self.preserve_order = preserve_order

def get_ordered_pages_from_groups(groups, fallback_pages=None):
    """Enhanced version that respects range order."""
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

# Simplified parser for testing the key fixes
class TestParser:
    def __init__(self, total_pages):
        self.total_pages = total_pages
        self._reset_state()
    
    def _reset_state(self):
        self.ordered_groups = []
        self.preserve_comma_order = False
    
    def parse(self, range_str):
        # Reset state for fresh parsing
        self._reset_state()
        
        # Check for comma-separated order preservation
        self.preserve_comma_order = ',' in range_str and self._is_numeric_only(range_str)
        
        # Split and parse parts
        if ',' in range_str:
            parts = [p.strip() for p in range_str.split(',')]
            for part in parts:
                pages, spec = self._parse_single_part(part)
                if pages:
                    is_range = self._is_range_spec(pages, spec)
                    group = PageGroup(
                        pages=pages, 
                        is_range=is_range,
                        original_spec=spec,
                        preserve_order=self.preserve_comma_order
                    )
                    self.ordered_groups.append(group)
        else:
            pages, spec = self._parse_single_part(range_str)
            if pages:
                is_range = self._is_range_spec(pages, spec)
                group = PageGroup(
                    pages=pages,
                    is_range=is_range,
                    original_spec=spec,
                    preserve_order=False
                )
                self.ordered_groups.append(group)
        
        # Return results
        all_pages = set()
        for group in self.ordered_groups:
            all_pages.update(group.pages)
        
        return all_pages, range_str, self.ordered_groups
    
    def _is_numeric_only(self, range_str):
        """Check if all parts are numeric specifications."""
        parts = [p.strip() for p in range_str.split(',')]
        for part in parts:
            if not (part.isdigit() or '-' in part or 'first' in part.lower() or 'last' in part.lower()):
                return False
        return True
    
    def _parse_single_part(self, part):
        """Parse a single part and return (pages, spec)."""
        part = part.strip()
        
        if part.isdigit():
            page = int(part)
            if 1 <= page <= self.total_pages:
                return [page], part
        
        elif '-' in part and not part.startswith('-') and not part.endswith('-'):
            try:
                start_str, end_str = part.split('-', 1)
                start = int(start_str)
                end = int(end_str)
                
                if start == end:
                    return [start], part
                elif start < end:
                    return list(range(start, end + 1)), part
                else:
                    return list(range(start, end - 1, -1)), part
            except ValueError:
                pass
        
        elif part.lower().startswith('first'):
            import re
            match = re.match(r'first[-\s]+(\d+)', part.lower())
            if match:
                count = int(match.group(1))
                return list(range(1, min(count + 1, self.total_pages + 1))), part
        
        elif part.lower().startswith('last'):
            import re
            match = re.match(r'last[-\s]+(\d+)', part.lower())
            if match:
                count = int(match.group(1))
                start_page = max(1, self.total_pages - count + 1)
                return list(range(start_page, self.total_pages + 1)), part
        
        return [], part
    
    def _is_range_spec(self, pages, spec):
        """Check if this represents a range specification."""
        if len(pages) <= 1:
            return False
        
        # Check if it's a range specification syntax
        if any(sep in spec for sep in ['-', ':', '..']) and not spec.startswith('first') and not spec.startswith('last'):
            return True
        
        # Check if pages are consecutive or reverse consecutive
        if len(pages) > 1:
            # Forward consecutive: [1, 2, 3, 4]
            is_forward_consecutive = all(pages[i] == pages[i-1] + 1 for i in range(1, len(pages)))
            # Reverse consecutive: [4, 3, 2, 1]
            is_reverse_consecutive = all(pages[i] == pages[i-1] - 1 for i in range(1, len(pages)))
            return is_forward_consecutive or is_reverse_consecutive
        
        return False

def test_key_fixes():
    """Test the key fixes for parsing issues."""
    print("=== Testing Key Parser Fixes ===")
    
    test_cases = [
        # Basic reordering
        ("10,5,15,2", [10, 5, 15, 2], "Individual pages in order"),
        ("10-7", [10, 9, 8, 7], "Reverse range"),
        ("20-20", [20], "Single page range"),
        
        # Non-comma cases (should not preserve order)
        ("first 3", [1, 2, 3], "First N pages"),
        ("last 2", [49, 50], "Last N pages"),
        ("5-10", [5, 6, 7, 8, 9, 10], "Forward range"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_range, expected_order, description in test_cases:
        try:
            parser = TestParser(total_pages=50)  # Fresh parser each time
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
    
    print(f"\nKey fixes test: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    success = test_key_fixes()
    if success:
        print("✅ Key fixes working correctly!")
    else:
        print("❌ Some fixes need more work.")


# End of file #
