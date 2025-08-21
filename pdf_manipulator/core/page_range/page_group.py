"""
Enhanced PageGroup class with order preservation support.
File: pdf_manipulator/core/page_range/page_group.py
"""

from dataclasses import dataclass


@dataclass
class PageGroup:
    pages: list[int]
    is_range: bool
    original_spec: str
    preserve_order: bool = False  # NEW: Whether to maintain input order vs natural sort order


def create_ordered_group(pages: list[int], original_spec: str, preserve_order: bool = False) -> PageGroup:
    """
    Create a PageGroup with appropriate range detection and order preservation.
    
    Args:
        pages: List of page numbers (in the intended order)
        original_spec: Original specification string
        preserve_order: Whether to preserve input order (True) or use natural sort (False)
    
    Returns:
        PageGroup with proper is_range setting
    """
    if not pages:
        return PageGroup([], False, original_spec, preserve_order)
    
    if len(pages) == 1:
        return PageGroup(pages, False, original_spec, preserve_order)
    
    # Check if this looks like a range specification (should not be sorted)
    is_range_spec = _looks_like_range_spec(original_spec)
    
    if preserve_order or is_range_spec:
        # Preserve the exact order for comma-separated lists OR range specifications
        # Check if consecutive in input order (forward or reverse)
        is_consecutive = _is_consecutive_sequence(pages)
        return PageGroup(pages, is_consecutive, original_spec, preserve_order)
    else:
        # Standard logic: sort and check consecutiveness (for individual pages)
        sorted_pages = sorted(set(pages))  # Remove duplicates and sort
        is_consecutive = all(sorted_pages[i] == sorted_pages[i-1] + 1 for i in range(1, len(sorted_pages)))
        return PageGroup(sorted_pages, is_consecutive, original_spec, preserve_order)


def _looks_like_range_spec(spec: str) -> bool:
    """Check if the spec looks like a range specification that should preserve order."""
    # Range indicators: contains -, :, or .. (but not first/last)
    if any(sep in spec for sep in ['-', ':', '..']):
        # Exclude first/last patterns which are not order-preserving ranges
        if not (spec.lower().startswith('first') or spec.lower().startswith('last')):
            return True
    return False


def _is_consecutive_sequence(pages: list[int]) -> bool:
    """Check if pages form a consecutive sequence (forward or reverse)."""
    if len(pages) <= 1:
        return False
    
    # Check forward consecutive: [1, 2, 3, 4]
    is_forward = all(pages[i] == pages[i-1] + 1 for i in range(1, len(pages)))
    
    # Check reverse consecutive: [4, 3, 2, 1]  
    is_reverse = all(pages[i] == pages[i-1] - 1 for i in range(1, len(pages)))
    
    return is_forward or is_reverse


def create_range_group(start: int, end: int, original_spec: str) -> PageGroup:
    """
    Create a PageGroup for a natural range (always preserves sequential order).
    
    Args:
        start: Starting page number
        end: Ending page number  
        original_spec: Original specification string
        
    Returns:
        PageGroup with sequential pages and is_range=True
    """
    if start > end:
        start, end = end, start  # Swap if reversed
    
    pages = list(range(start, end + 1))
    return PageGroup(pages, True, original_spec, preserve_order=False)


def merge_groups_in_order(groups: list[PageGroup], description: str) -> tuple[set[int], list[PageGroup]]:
    """
    Merge multiple PageGroups while preserving their relative order.
    
    Args:
        groups: List of PageGroups to merge
        description: Description for the merged result
        
    Returns:
        Tuple of (all_pages_set, ordered_groups_list)
    """
    all_pages = set()
    ordered_groups = []
    
    for group in groups:
        all_pages.update(group.pages)
        ordered_groups.append(group)
    
    return all_pages, ordered_groups


# End of file #
