"""
Advanced page selection pipeline integrating all filtering and boundary options.
Create: pdf_manipulator/core/advanced_page_selection.py

Coordinates: page range parsing → boundary detection → group filtering
"""

import argparse
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.page_range.group_filtering import (
    filter_page_groups, 
    describe_filter_result,
    preview_group_filtering
)

console = Console()


def process_advanced_page_selection(args: argparse.Namespace, pdf_path: Path, 
                                    total_pages: int) -> tuple[set[int], str, list[PageGroup]]:
    """
    Process advanced page selection with full pipeline.
    
    Pipeline:
    1. Initial page selection (--extract-pages)
    2. Boundary detection (--group-start, --group-end) 
    3. Group filtering (--filter-matches)
    
    Args:
        args: Parsed command line arguments
        pdf_path: Path to PDF file
        total_pages: Total pages in PDF
        
    Returns:
        Tuple of (final_pages, description, final_groups)
    """
    
    # Phase 1: Initial page selection
    console.print(f"[dim]Phase 1: Initial page selection: '{args.extract_pages}'[/dim]")
    
    initial_pages, initial_desc, initial_groups = parse_page_range(
        args.extract_pages, total_pages, pdf_path
    )
    
    console.print(f"[dim]  → {len(initial_pages)} pages in {len(initial_groups)} groups[/dim]")
    
    current_groups = initial_groups
    current_pages = initial_pages
    
    # Phase 2: Boundary detection (if specified)
    if args.group_start or args.group_end:
        console.print(f"[dim]Phase 2: Boundary detection[/dim]")
        
        if args.group_start:
            console.print(f"[dim]  Group start: '{args.group_start}'[/dim]")
        if args.group_end:
            console.print(f"[dim]  Group end: '{args.group_end}'[/dim]")
        
        current_groups = apply_boundary_detection(
            current_groups, 
            args.group_start, 
            args.group_end,
            pdf_path, 
            total_pages
        )
        
        # Recalculate pages from new groups
        current_pages = set()
        for group in current_groups:
            current_pages.update(group.pages)
        
        console.print(f"[dim]  → {len(current_pages)} pages in {len(current_groups)} groups after boundary detection[/dim]")
    
    # Phase 3: Group filtering (if specified)
    if args.filter_matches:
        console.print(f"[dim]Phase 3: Group filtering: '{args.filter_matches}'[/dim]")
        
        original_count = len(current_groups)
        
        current_groups = filter_page_groups(
            current_groups, 
            args.filter_matches,
            pdf_path, 
            total_pages
        )
        
        # Recalculate pages from filtered groups
        current_pages = set()
        for group in current_groups:
            current_pages.update(group.pages)
        
        # Show filtering results
        filter_desc = describe_filter_result(original_count, len(current_groups), args.filter_matches)
        console.print(f"[dim]  → {filter_desc}[/dim]")
        console.print(f"[dim]  → {len(current_pages)} pages in {len(current_groups)} groups after filtering[/dim]")
    
    # Create final description
    final_desc = create_advanced_description(args, initial_desc, len(current_groups))
    
    # Validate final result
    if not current_pages:
        if args.filter_matches:
            raise ValueError(f"No groups match filter criteria: {args.filter_matches}")
        elif args.group_start or args.group_end:
            raise ValueError("No groups remain after boundary detection")
        else:
            raise ValueError("No pages selected")
    
    console.print(f"[green]Final result: {len(current_pages)} pages in {len(current_groups)} groups[/green]")
    
    return current_pages, final_desc, current_groups


def apply_boundary_detection(groups: list[PageGroup], start_pattern: str, end_pattern: str,
                            pdf_path: Path, total_pages: int) -> list[PageGroup]:
    """
    Apply boundary detection to split/merge groups at pattern boundaries.
    
    This is an updated version of the boundary detection logic.
    """
    
    if not start_pattern and not end_pattern:
        return groups
    
    # Import here to avoid circular dependencies
    from pdf_manipulator.core.page_range.patterns import parse_pattern_expression
    
    # Find boundary pages
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
        new_groups.extend(_split_group_at_boundaries(group, start_pages, end_pages))
    
    return new_groups


def _split_group_at_boundaries(group: PageGroup, start_pages: set[int], 
                                end_pages: set[int]) -> list[PageGroup]:
    """Split a single group at boundary points."""
    
    if not group.pages:
        return [group]
    
    # Sort pages to process sequentially
    sorted_pages = sorted(group.pages)
    groups = []
    current_group_pages = []
    
    for page in sorted_pages:
        # Check if this page ends the current group
        if page in end_pages and current_group_pages:
            # End current group (inclusive - include the end page)
            current_group_pages.append(page)
            groups.append(_create_boundary_group(current_group_pages, group.original_spec))
            current_group_pages = []
            continue
        
        # Check if this page starts a new group
        if page in start_pages:
            # Start new group (finish current group first if it has pages)
            if current_group_pages:
                groups.append(_create_boundary_group(current_group_pages, group.original_spec))
                current_group_pages = []
            # Start new group with this page
            current_group_pages = [page]
        else:
            # Regular page - add to current group
            current_group_pages.append(page)
    
    # Don't forget the final group
    if current_group_pages:
        groups.append(_create_boundary_group(current_group_pages, group.original_spec))
    
    return groups if groups else [group]  # Return original if no splits occurred


def _create_boundary_group(pages: list[int], original_spec: str) -> PageGroup:
    """Create a PageGroup from boundary-split pages."""
    
    if not pages:
        return PageGroup([], False, original_spec)
    
    if len(pages) == 1:
        return PageGroup(pages, False, f"page{pages[0]}")
    else:
        # Check if consecutive
        sorted_pages = sorted(pages)
        is_consecutive = all(sorted_pages[i] == sorted_pages[i-1] + 1 for i in range(1, len(sorted_pages)))
        
        if is_consecutive:
            spec = f"pages{sorted_pages[0]}-{sorted_pages[-1]}"
            return PageGroup(pages, True, spec)
        else:
            # Non-consecutive - create a grouped spec
            spec = f"pages{','.join(map(str, sorted(pages)))}"
            return PageGroup(pages, True, spec)


def create_advanced_description(args: argparse.Namespace, initial_desc: str, 
                                final_group_count: int) -> str:
    """Create description for advanced page selection."""
    
    parts = [initial_desc]
    
    if args.group_start or args.group_end:
        if args.group_start and args.group_end:
            parts.append("bounded")
        elif args.group_start:
            parts.append("start-split")
        else:
            parts.append("end-split")
    
    if args.filter_matches:
        # Simplify filter description for filename
        filter_desc = args.filter_matches
        if len(filter_desc) > 10:
            if filter_desc.isdigit() or ',' in filter_desc:
                filter_desc = "filtered"
            else:
                filter_desc = "criteria"
        parts.append(filter_desc)
    
    if final_group_count > 1:
        parts.append(f"{final_group_count}groups")
    
    # Join and truncate if needed
    result = "-".join(parts)
    if len(result) > 30:
        result = f"advanced-{final_group_count}groups"
    
    return result


def preview_advanced_selection(args: argparse.Namespace, pdf_path: Path, 
                                total_pages: int, show_details: bool = True) -> None:
    """Preview advanced page selection without actually processing."""
    
    console.print(f"\n[bold blue]Advanced Page Selection Preview[/bold blue]")
    console.print(f"PDF: {pdf_path.name} ({total_pages} pages)")
    
    try:
        # Run through the pipeline
        final_pages, final_desc, final_groups = process_advanced_page_selection(
            args, pdf_path, total_pages
        )
        
        console.print(f"\n[bold green]Would extract {len(final_pages)} pages in {len(final_groups)} groups[/bold green]")
        console.print(f"Output description: {final_desc}")
        
        if show_details and len(final_groups) <= 10:
            console.print(f"\n[yellow]Groups that would be extracted:[/yellow]")
            for i, group in enumerate(final_groups):
                if len(group.pages) == 1:
                    page_desc = f"page {group.pages[0]}"
                else:
                    page_desc = f"pages {group.pages[0]}-{group.pages[-1]}"
                console.print(f"  Group {i+1}: {page_desc} ({len(group.pages)} pages)")
        
    except Exception as e:
        console.print(f"[red]Preview failed: {e}[/red]")


def validate_advanced_selection_args(args: argparse.Namespace) -> tuple[bool, str]:
    """
    Validate advanced selection arguments for early error detection.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    
    # Check that advanced options are only used with --extract-pages
    if args.filter_matches and not args.extract_pages:
        return False, "--filter-matches can only be used with --extract-pages"
    
    if (args.group_start or args.group_end) and not args.extract_pages:
        return False, "--group-start and --group-end can only be used with --extract-pages"
    
    # Validate filter syntax
    if args.filter_matches:
        from pdf_manipulator.core.page_range.group_filtering import validate_filter_syntax
        is_valid, error_msg = validate_filter_syntax(args.filter_matches)
        if not is_valid:
            return False, f"Invalid filter syntax: {error_msg}"
    
    return True, ""
