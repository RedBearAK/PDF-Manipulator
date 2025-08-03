"""
Group filtering logic for advanced page range selection.
Create: pdf_manipulator/core/page_range/group_filtering.py

Filters PageGroup objects based on index or content criteria.
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.page_range.boolean import UnifiedBooleanSupervisor


console = Console()


def filter_page_groups(groups: list[PageGroup], filter_criteria: str, 
                        pdf_path: Path, total_pages: int) -> list[PageGroup]:
    """
    Filter page groups based on criteria.
    
    Args:
        groups: List of PageGroup objects to filter
        filter_criteria: Filter expression (index-based or content-based)
        pdf_path: PDF file path for content analysis
        total_pages: Total pages in PDF
        
    Returns:
        Filtered list of PageGroup objects
        
    Examples:
        # Index-based filtering
        filter_page_groups(groups, "1,3,4", pdf_path, total_pages)
        
        # Content-based filtering  
        filter_page_groups(groups, "contains:'Important'", pdf_path, total_pages)
        filter_page_groups(groups, "contains:'Security' & !type:empty", pdf_path, total_pages)
        filter_page_groups(groups, "size:>1MB | contains:'Critical'", pdf_path, total_pages)
    """
    
    if not groups:
        return []
    
    if not filter_criteria or not filter_criteria.strip():
        return groups
    
    filter_criteria = filter_criteria.strip()
    
    # Check if this is index-based filtering (numbers and commas only)
    if _is_index_based_filter(filter_criteria):
        return _filter_by_indices(groups, filter_criteria)
    else:
        return _filter_by_criteria(groups, filter_criteria, pdf_path, total_pages)


def _is_index_based_filter(criteria: str) -> bool:
    """Check if filter criteria is index-based (like '1,3,4')."""
    # Remove whitespace and check if it's just numbers, commas, and dashes
    clean_criteria = re.sub(r'\s+', '', criteria)
    
    # Allow numbers, commas, and simple ranges like "1-3,5,7-9"
    return bool(re.match(r'^[\d,\-]+$', clean_criteria))


def _filter_by_indices(groups: list[PageGroup], indices_str: str) -> list[PageGroup]:
    """Filter groups by index positions (1-indexed)."""
    
    try:
        # Parse index specification (can include ranges like "1-3,5,7-9")
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


def _filter_by_criteria(groups: list[PageGroup], criteria: str, 
                        pdf_path: Path, total_pages: int) -> list[PageGroup]:
    """Filter groups by content criteria using boolean expressions."""
    
    filtered_groups = []
    
    for group in groups:
        if _group_matches_criteria(group, criteria, pdf_path, total_pages):
            filtered_groups.append(group)
    
    return filtered_groups


def _group_matches_criteria(group: PageGroup, criteria: str, 
                            pdf_path: Path, total_pages: int) -> bool:
    """Check if a single group matches the filter criteria."""
    
    # Create a temporary supervisor to evaluate criteria against this group's pages
    supervisor = UnifiedBooleanSupervisor(pdf_path, total_pages)
    
    try:
        # Evaluate criteria against the group's specific pages
        matching_pages, _ = supervisor.evaluate(criteria)
        
        # Check if any of the group's pages are in the matching set
        group_page_set = set(group.pages)
        matching_page_set = set(matching_pages)
        
        # Group matches if there's any overlap
        return bool(group_page_set & matching_page_set)
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not evaluate criteria '{criteria}' for group {group.original_spec}: {e}[/yellow]")
        return False


def _check_group_overlap(group: PageGroup, target_pages: set[int]) -> bool:
    """Check if group has any pages that overlap with target pages."""
    return bool(set(group.pages) & target_pages)


def _check_group_contains_all(group: PageGroup, target_pages: set[int]) -> bool:
    """Check if group contains all target pages."""
    return target_pages.issubset(set(group.pages))


def _get_group_total_size(group: PageGroup, pdf_path: Path) -> int:
    """Calculate total size of all pages in group (in bytes)."""
    try:
        from pdf_manipulator.core.page_analysis import PageAnalyzer
        
        with PageAnalyzer(pdf_path) as analyzer:
            total_size = 0
            for page_num in group.pages:
                analysis = analyzer.analyze_page(page_num)
                total_size += analysis.size_bytes
            return total_size
            
    except Exception:
        return 0


def validate_filter_syntax(filter_criteria: str) -> tuple[bool, str]:
    """
    Validate filter criteria syntax without requiring PDF access.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    if not filter_criteria or not filter_criteria.strip():
        return True, ""
    
    criteria = filter_criteria.strip()
    
    # Check if index-based
    if _is_index_based_filter(criteria):
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
    # (Full validation requires PDF access and is done during execution)
    
    # Check for basic syntax errors
    if criteria.count('(') != criteria.count(')'):
        return False, "Mismatched parentheses"
    
    # Check for unmatched quotes
    single_quotes = criteria.count("'")
    double_quotes = criteria.count('"')
    if single_quotes % 2 != 0:
        return False, "Unmatched single quote"
    if double_quotes % 2 != 0:
        return False, "Unmatched double quote"
    
    # Check for operators without operands
    if criteria.startswith(('&', '|')):
        return False, "Boolean operator missing left operand"
    
    if criteria.endswith(('&', '|')):
        return False, "Boolean operator missing right operand"
    
    # Check for multiple consecutive operators
    if any(op1 + op2 in criteria for op1 in ['&', '|'] for op2 in ['&', '|']):
        return False, "Multiple consecutive boolean operators"
    
    return True, ""


# Utility functions for CLI integration

def describe_filter_result(original_count: int, filtered_count: int, filter_criteria: str) -> str:
    """Create a description of the filtering result."""
    
    if filtered_count == original_count:
        return f"All {original_count} groups match filter"
    elif filtered_count == 0:
        return f"No groups match filter '{filter_criteria}'"
    else:
        return f"Filtered {original_count} groups to {filtered_count} using '{filter_criteria}'"


def preview_group_filtering(groups: list[PageGroup], filter_criteria: str, 
                            pdf_path: Path, total_pages: int, show_details: bool = True) -> None:
    """Preview what groups would be filtered (for dry-run or debugging)."""
    
    console.print(f"\n[blue]Filter Preview: '{filter_criteria}'[/blue]")
    console.print(f"Original groups: {len(groups)}")
    
    try:
        filtered_groups = filter_page_groups(groups, filter_criteria, pdf_path, total_pages)
        console.print(f"After filtering: {len(filtered_groups)}")
        
        if show_details and len(groups) <= 20:  # Don't spam for large numbers
            console.print("\n[yellow]Groups that would be kept:[/yellow]")
            for i, group in enumerate(groups):
                if group in filtered_groups:
                    status = "✓ KEEP"
                    style = "green"
                else:
                    status = "✗ SKIP"
                    style = "red"
                    
                page_desc = f"page {group.pages[0]}" if len(group.pages) == 1 else f"pages {group.pages[0]}-{group.pages[-1]}"
                console.print(f"  [{style}]{status}[/{style}] Group {i+1}: {page_desc} ({group.original_spec})")
        
    except Exception as e:
        console.print(f"[red]Filter preview failed: {e}[/red]")
