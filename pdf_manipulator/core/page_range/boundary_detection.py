"""
Boundary detection for splitting page groups at pattern-based boundaries.
File: pdf_manipulator/core/page_range/boundary_detection.py

This module handles splitting page groups at boundaries defined by patterns.
Used by the parser when --group-start or --group-end options are specified.
"""

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.page_range.patterns import parse_pattern_expression


console = Console()


def apply_boundary_detection(groups: list[PageGroup], 
                            start_pattern: str, 
                            end_pattern: str,
                            pdf_path: Path, 
                            total_pages: int) -> list[PageGroup]:
    """
    Apply boundary detection to split groups at pattern boundaries.
    
    This is the canonical implementation used by all callers.
    
    Args:
        groups: Initial page groups to split
        start_pattern: Pattern for starting new groups (e.g., "contains:'Chapter'")
        end_pattern: Pattern for ending groups (e.g., "contains:'Summary'")
        pdf_path: Path to PDF file (for pattern matching)
        total_pages: Total pages in PDF
        
    Returns:
        New list of groups split at boundaries
        
    Examples:
        # Split at chapter starts
        groups = apply_boundary_detection(groups, "contains:'Chapter'", None, pdf_path, 100)
        
        # Split at section ends
        groups = apply_boundary_detection(groups, None, "contains:'Summary'", pdf_path, 100)
        
        # Both start and end boundaries
        groups = apply_boundary_detection(groups, "contains:'Article'", 
                                         "contains:'References'", pdf_path, 100)
    """
    
    if not start_pattern and not end_pattern:
        return groups
    
    # Find boundary pages using pattern matching
    start_pages = set()
    if start_pattern:
        try:
            start_pages = set(parse_pattern_expression(start_pattern, pdf_path, total_pages))
            console.print(f"[dim]    Start boundaries at pages: {sorted(start_pages)}[/dim]")
        except ValueError as e:
            raise ValueError(f"Invalid start boundary pattern: {e}")
    
    end_pages = set()
    if end_pattern:
        try:
            end_pages = set(parse_pattern_expression(end_pattern, pdf_path, total_pages))
            console.print(f"[dim]    End boundaries at pages: {sorted(end_pages)}[/dim]")
        except ValueError as e:
            raise ValueError(f"Invalid end boundary pattern: {e}")
    
    # Split each group at boundary points
    new_groups = []
    for group in groups:
        split_results = _split_group_at_boundaries(group, start_pages, end_pages)
        # Filter out any empty groups (safety check)
        new_groups.extend([g for g in split_results if g.pages])
    
    return new_groups


def _split_group_at_boundaries(group: PageGroup, 
                                start_pages: set[int], 
                                end_pages: set[int]) -> list[PageGroup]:
    """
    Split a single group at boundary points.
    
    Correctly handles all cases:
    - Page is both start AND end (single-page group)
    - Consecutive boundaries (each becomes single-page group)
    - First/last pages as boundaries
    - Regular boundaries with content between them
    
    Args:
        group: PageGroup to split
        start_pages: Set of page numbers that start new groups
        end_pages: Set of page numbers that end groups (inclusive)
        
    Returns:
        List of new PageGroup objects after splitting
    """
    
    if not group.pages:
        return [group]
    
    sorted_pages = sorted(group.pages)
    groups = []
    current_group_pages = []
    
    for page in sorted_pages:
        is_start = page in start_pages
        is_end = page in end_pages
        
        # Case 1: Page is BOTH start and end - single-page group
        if is_start and is_end:
            if current_group_pages:
                groups.append(_create_boundary_group(current_group_pages, group.original_spec))
            groups.append(_create_boundary_group([page], group.original_spec))
            current_group_pages = []
            
        # Case 2: Page ends the current group (inclusive)
        elif is_end:
            current_group_pages.append(page)
            groups.append(_create_boundary_group(current_group_pages, group.original_spec))
            current_group_pages = []
            
        # Case 3: Page starts a new group
        elif is_start:
            if current_group_pages:
                groups.append(_create_boundary_group(current_group_pages, group.original_spec))
            current_group_pages = [page]
            
        # Case 4: Regular page - add to current group
        else:
            current_group_pages.append(page)
    
    # Don't forget the final group
    if current_group_pages:
        groups.append(_create_boundary_group(current_group_pages, group.original_spec))
    
    return groups if groups else [group]


def _create_boundary_group(pages: list[int], original_spec: str) -> PageGroup:
    """
    Create a PageGroup from boundary-split pages.
    
    Args:
        pages: List of page numbers in the group
        original_spec: Original specification string (for reference)
        
    Returns:
        PageGroup object with appropriate metadata
    """
    
    if not pages:
        return PageGroup([], False, original_spec)
    
    if len(pages) == 1:
        return PageGroup(pages, False, f"page{pages[0]}")
    
    # Check if consecutive
    sorted_pages = sorted(pages)
    is_consecutive = all(sorted_pages[i] == sorted_pages[i-1] + 1 
                        for i in range(1, len(sorted_pages)))
    
    if is_consecutive:
        spec = f"pages{sorted_pages[0]}-{sorted_pages[-1]}"
        return PageGroup(pages, True, spec)
    else:
        spec = f"pages{','.join(map(str, sorted(pages)))}"
        return PageGroup(pages, True, spec)


# End of file #
