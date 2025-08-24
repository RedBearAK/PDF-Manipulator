"""
Core deduplication logic for PDF page extraction.
File: pdf_manipulator/core/deduplication.py
"""

from rich.console import Console

console = Console()


def detect_duplicates(groups: list) -> dict:
    """
    Analyze groups for page overlaps and return duplicate information.
    
    Args:
        groups: List of PageGroup objects
        
    Returns:
        Dictionary with duplicate analysis results
    """
    page_to_groups = {}  # page_num -> list of (group_index, group_spec)
    duplicate_pages = set()
    
    for group_idx, group in enumerate(groups):
        if not hasattr(group, 'pages') or not group.pages:
            continue
            
        for page in group.pages:
            if page not in page_to_groups:
                page_to_groups[page] = []
            page_to_groups[page].append((group_idx, getattr(group, 'original_spec', f"group{group_idx+1}")))
            
            # Mark as duplicate if appears in multiple groups
            if len(page_to_groups[page]) > 1:
                duplicate_pages.add(page)
    
    # Find affected groups
    affected_groups = []
    for page in duplicate_pages:
        affected_groups.extend(page_to_groups[page])
    
    # Create overlap summary
    overlap_summary = ""
    if duplicate_pages:
        overlap_lines = []
        for page in sorted(duplicate_pages):
            group_specs = [spec for _, spec in page_to_groups[page]]
            overlap_lines.append(f"  Page {page} appears in: {', '.join(group_specs)}")
        overlap_summary = "\n".join(overlap_lines)
    
    return {
        'has_duplicates': bool(duplicate_pages),
        'duplicate_pages': sorted(list(duplicate_pages)),
        'affected_groups': list(set(affected_groups)),  # Remove duplicate group entries
        'overlap_summary': overlap_summary,
        'page_to_groups': page_to_groups
    }


def determine_default_dedup_strategy(args) -> str:
    """
    Determine the default deduplication strategy based on output mode.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Default deduplication strategy string
    """
    if hasattr(args, 'dedup') and args.dedup:
        return args.dedup
    elif hasattr(args, 'respect_groups') and args.respect_groups:
        return 'groups'  # Allow dupes between groups
    elif hasattr(args, 'separate_files') and args.separate_files:
        return 'strict'  # No duplicate page files
    else:
        return 'strict'  # Single file - no duplicate pages


def apply_deduplication_strategy(groups: list, strategy: str) -> tuple[list, dict]:
    """
    Apply deduplication strategy to groups and return processed groups and info.
    
    Args:
        groups: List of PageGroup objects
        strategy: Deduplication strategy ('none', 'strict', 'groups', 'warn', 'fail')
        
    Returns:
        Tuple of (processed_groups, dedup_info)
        
    Raises:
        ValueError: If strategy is 'fail' and duplicates are detected
    """
    duplicate_info = detect_duplicates(groups)
    
    if not duplicate_info['has_duplicates']:
        # No duplicates found - return groups unchanged
        return groups, duplicate_info
    
    if strategy == 'none':
        # Disable deduplication - allow all duplicates
        console.print("[dim]Deduplication disabled - allowing duplicate pages[/dim]")
        return groups, duplicate_info
    
    elif strategy == 'warn':
        # Show warning but use default strategy for mode
        console.print(f"[yellow]Warning: Detected {len(duplicate_info['duplicate_pages'])} duplicate pages:[/yellow]")
        console.print(duplicate_info['overlap_summary'])
        console.print("[yellow]Proceeding with strict deduplication (first occurrence wins)[/yellow]")
        strategy = 'strict'  # Fall through to strict handling
    
    elif strategy == 'fail':
        # Stop execution with error
        console.print(f"[red]Error: Detected {len(duplicate_info['duplicate_pages'])} duplicate pages:[/red]")
        console.print(duplicate_info['overlap_summary'])
        raise ValueError("Duplicate pages detected. Use --dedup to specify handling strategy.")
    
    # Apply actual deduplication for 'strict' and 'groups' strategies
    if strategy == 'strict':
        return _apply_strict_deduplication(groups, duplicate_info), duplicate_info
    elif strategy == 'groups':
        return _apply_groups_deduplication(groups, duplicate_info), duplicate_info
    else:
        raise ValueError(f"Unknown deduplication strategy: {strategy}")


def _apply_strict_deduplication(groups: list, duplicate_info: dict) -> list:
    """
    Apply strict deduplication - each page appears only once (first occurrence wins).
    """
    seen_pages = set()
    deduplicated_groups = []
    
    for group in groups:
        if not hasattr(group, 'pages') or not group.pages:
            # Keep empty groups as-is
            deduplicated_groups.append(group)
            continue
        
        # Filter out pages we've already seen
        new_pages = []
        for page in group.pages:
            if page not in seen_pages:
                new_pages.append(page)
                seen_pages.add(page)
        
        if new_pages:
            # Create new group with remaining pages
            from pdf_manipulator.core.page_range.page_group import PageGroup
            new_group = PageGroup(
                pages=new_pages,
                is_range=getattr(group, 'is_range', False),
                original_spec=getattr(group, 'original_spec', 'deduped')
            )
            # Preserve other attributes
            for attr in ['preserve_order']:
                if hasattr(group, attr):
                    setattr(new_group, attr, getattr(group, attr))
            deduplicated_groups.append(new_group)
    
    console.print(f"[dim]Strict deduplication: {len(duplicate_info['duplicate_pages'])} duplicate pages removed[/dim]")
    return deduplicated_groups


def _apply_groups_deduplication(groups: list, duplicate_info: dict) -> list:
    """
    Apply groups deduplication - remove duplicates within individual groups only.
    """
    deduplicated_groups = []
    
    for group in groups:
        if not hasattr(group, 'pages') or not group.pages:
            # Keep empty groups as-is
            deduplicated_groups.append(group)
            continue
        
        # Remove duplicates within this group only
        unique_pages = []
        seen_in_group = set()
        
        for page in group.pages:
            if page not in seen_in_group:
                unique_pages.append(page)
                seen_in_group.add(page)
        
        if unique_pages:
            # Create new group with unique pages
            from pdf_manipulator.core.page_range.page_group import PageGroup
            new_group = PageGroup(
                pages=unique_pages,
                is_range=getattr(group, 'is_range', False),
                original_spec=getattr(group, 'original_spec', 'deduped')
            )
            # Preserve other attributes
            for attr in ['preserve_order']:
                if hasattr(group, attr):
                    setattr(new_group, attr, getattr(group, attr))
            deduplicated_groups.append(new_group)
    
    console.print("[dim]Groups deduplication: duplicates removed within individual groups[/dim]")
    return deduplicated_groups


# End of file #
