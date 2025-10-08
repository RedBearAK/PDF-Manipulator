"""
Enhanced parse_page_range function with advanced filtering and boundary detection.
File: pdf_manipulator/core/parser.py

This maintains backward compatibility while adding advanced features.
All existing call sites continue to work unchanged.
"""

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.utils import sanitize_filename
from pdf_manipulator.core.page_range.boolean import (
    looks_like_boolean_expression,
    evaluate_boolean_expression_with_groups
)
from pdf_manipulator.core.operation_context import OpCtx
from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser, PageGroup
from pdf_manipulator.core.page_range.boundary_detection import apply_boundary_detection


console = Console()


def parse_page_range(*args, **kwargs):
    """
    Parse page range using OpCtx - parameters ignored for backward compatibility.

    Parse page range string and return set of page numbers (1-indexed), description, and groupings.

    Enhanced version that supports advanced filtering and boundary detection:
    
    Args:
        range_str: Page range expression (e.g., "1-5", "contains:'text'", "type:text & size:>1MB")
        total_pages: Total pages in PDF  
        pdf_path: Path to PDF file (required for content-based patterns)
        filter_matches: Optional group filtering criteria (e.g., "1,3,4", "contains:'Important'")
        group_start: Optional pattern to start new groups (e.g., "contains:'Chapter'")
        group_end: Optional pattern to end groups (e.g., "contains:'Summary'")
        
    Returns:
        Tuple of (set of page numbers, description for filename, list of page groups)
        
    Backward Compatibility:
        All existing calls work unchanged. Advanced features are opt-in via new parameters.

    NEW: Unified Boolean Processing:
    - Handles ALL boolean expressions (simple and advanced) through single clean entry point
    - Preserves group structure through magazine processing
    - No circular dependencies - clean architecture

    Range-based selection (when pdf_path provided):
    - contains:'Chapter 1' to contains:'Chapter 2'  - from pattern to pattern
    - 5 to contains:'Appendix'                      - from page to pattern
    - contains:'Start' to 10                        - from pattern to page
    - contains:'Ch 1'+1 to contains:'Ch 2'-1        - with offsets

    Boolean expressions with range patterns:
    - (contains:'Article' to contains:'End') & !type:image  - Magazine processing
    - (contains:'Chapter' to contains:'Summary') | contains:'Sidebar'  - Complex combinations

    Simple boolean expressions:
    - contains:'Invoice' & contains:'Total'         - Standard boolean AND
    - type:text | type:mixed                        - Standard boolean OR
    - all & !contains:'DRAFT'                       - Standard boolean NOT

    Existing pattern-based selection:
    - contains[/i]:"TEXT"       - pages containing TEXT (use quotes for literals)
    - regex[/i]:"PATTERN"       - pages matching regex
    - line-starts[/i]:"TEXT"    - pages with lines starting with TEXT
    
    With offset modifiers:
    - contains:Chapter 1+1      - page after "Chapter 1" match
    - contains:Summary-2        - 2 pages before "Summary" match

    Supports:
    - Single page: "5"
    - Range: "3-7" or "3:7" or "3..7"
    - Open-ended: "3-" (page 3 to end) or "-7" (start to page 7)
    - First N: "first 3" or "first-3"
    - Last N: "last 2" or "last-2"
    - Multiple: "1-3,7,9-11"
    - Slicing: "::2" (odd pages), "2::2" (even pages), "5:10:2" (every 2nd from 5 to 10)
    - All pages: "all"

    Advanced Features:
    - Group filtering: filter_matches="1,3,4" or filter_matches="contains:'Important'"
    - Boundary detection: group_start="contains:'Chapter'", group_end="contains:'Summary'"
    """
    
    # Discard incoming parameters
    args = None
    kwargs = None
    
    # Check if we already have results
    if OpCtx.has_parsed_results():
        console.print("✨ Using cached parsing results")
        cached = OpCtx.get_cached_parsing_results()
        return cached.selected_pages, cached.range_description, cached.page_groups
    

    # DEFENSIVE GUARD: Validate OpCtx state before proceeding
    if not OpCtx.current_pdf_path or not OpCtx.current_page_count:
        raise RuntimeError(
            "PDF context not initialized. "
            "Call OpCtx.set_current_pdf(pdf_path, page_count) before parsing. "
            "This is a bug in the batch processing logic."
        )

    # Get all parameters from OpCtx
    range_str = OpCtx.get_page_range_arg()
    total_pages = OpCtx.current_page_count
    pdf_path = OpCtx.current_pdf_path
    filter_matches = getattr(OpCtx.args, 'filter_matches', None)
    group_start = getattr(OpCtx.args, 'group_start', None)
    group_end = getattr(OpCtx.args, 'group_end', None)
    
    # Check if any advanced features are requested
    has_advanced_features = any([filter_matches, group_start, group_end])
    
    if has_advanced_features:
        # Use advanced pipeline
        selected_pages, range_description, page_groups = _parse_with_advanced_pipeline(
            range_str, total_pages, pdf_path, filter_matches, group_start, group_end
        )
    else:
        # Use original logic
        selected_pages, range_description, page_groups = _parse_original_logic(range_str, total_pages, pdf_path)
    
    # Store results in OpCtx and return
    OpCtx.store_parsed_results(selected_pages, range_description, page_groups)
    return selected_pages, range_description, page_groups


def _parse_original_logic(range_str: str, total_pages: int, pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """Original parse_page_range logic for backward compatibility."""
    
    # Check if this is a boolean expression (simple or advanced)
    if pdf_path and looks_like_boolean_expression(range_str):
        return _parse_with_boolean_processor(range_str, pdf_path, total_pages)
    
    # Standard parsing for non-boolean expressions
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)


def _parse_with_advanced_pipeline(range_str: str, total_pages: int, pdf_path: Path,
                                    filter_matches: str, group_start: str, 
                                    group_end: str) -> tuple[set[int], str, list[PageGroup]]:
    """Parse using advanced pipeline with filtering and boundary detection."""
    
    # Phase 1: Initial page selection (use original logic)
    initial_pages, initial_desc, initial_groups = _parse_original_logic(range_str, total_pages, pdf_path)
    
    current_groups = initial_groups
    current_pages = initial_pages
    
    # Phase 2: Boundary detection (if specified)
    if group_start or group_end:
        current_groups = _apply_boundary_detection(
            current_groups, group_start, group_end, pdf_path, total_pages
        )
        
        # Recalculate pages from new groups
        current_pages = set()
        for group in current_groups:
            current_pages.update(group.pages)
    
    # Phase 3: Group filtering (if specified)
    if filter_matches:
        from pdf_manipulator.core.page_range.group_filtering import filter_page_groups
        
        current_groups = filter_page_groups(
            current_groups, filter_matches, pdf_path, total_pages
        )
        
        # Recalculate pages from filtered groups
        current_pages = set()
        for group in current_groups:
            current_pages.update(group.pages)
    
    # Create final description
    final_desc = _create_advanced_description(
        initial_desc, filter_matches, group_start, group_end, len(current_groups)
    )
    
    # Validate final result
    if not current_pages:
        if filter_matches:
            raise ValueError(f"No groups match filter criteria: {filter_matches}")
        elif group_start or group_end:
            raise ValueError("No groups remain after boundary detection")
        else:
            raise ValueError("No pages selected")
    
    return current_pages, final_desc, current_groups


def _parse_with_boolean_processor(range_str: str, pdf_path: Path, 
                                total_pages: int) -> tuple[set[int], str, list[PageGroup]]:
    """Parse using unified boolean processor for all boolean expressions."""
    
    pages, groups = evaluate_boolean_expression_with_groups(range_str, pdf_path, total_pages)
    
    # Create description for filename
    description = _create_boolean_description(range_str, len(groups))
    
    return set(pages), description, groups


def _create_boolean_description(range_str: str, num_groups: int) -> str:
    """Create filename-safe description for boolean expressions."""
    
    # Simplify complex expressions for filename
    if len(range_str) > 30:
        if num_groups > 1:
            return f"boolean-{num_groups}groups"
        else:
            return "boolean-selection"
    
    # Clean up the expression for filename use
    clean_desc = sanitize_filename(range_str, max_length=25)
    
    if num_groups > 1:
        return f"{clean_desc}-{num_groups}g"
    else:
        return clean_desc


def _apply_boundary_detection(groups: list[PageGroup], start_pattern: str, end_pattern: str,
                                pdf_path: Path, total_pages: int) -> list[PageGroup]:
    """
    Apply boundary detection to split/merge groups at pattern boundaries.
    
    Delegates to the boundary_detection module to avoid code duplication.
    """
    
    if not start_pattern and not end_pattern:
        return groups
    
    # # Import here to avoid circular dependency
    # from pdf_manipulator.core.page_range.boundary_detection import apply_boundary_detection
    
    return apply_boundary_detection(groups, start_pattern, end_pattern, pdf_path, total_pages)


def _create_advanced_description(initial_desc: str, filter_matches: str, 
                                group_start: str, group_end: str, final_group_count: int) -> str:
    """Create description for advanced page selection."""
    
    parts = [initial_desc]
    
    if group_start or group_end:
        if group_start and group_end:
            parts.append("bounded")
        elif group_start:
            parts.append("start-split")
        else:
            parts.append("end-split")
    
    if filter_matches:
        # Simplify filter description for filename
        filter_desc = filter_matches
        if len(filter_desc) > 10:
            if filter_desc.replace(',', '').replace('-', '').isdigit():
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


def parse_page_range_from_args(*args, **kwargs):
    """
    Convenience wrapper for backward compatibility.
    Just delegates to parse_page_range().
    """
    # Discard parameters
    args = None
    kwargs = None
    
    # Check if we already have results
    cached = OpCtx.get_cached_parsing_results()
    if cached:
        console.print("✨ Using cached parsing results")
        return cached.selected_pages, cached.range_description, cached.page_groups
    
    # No results yet - parse using OpCtx args
    selected_pages, range_description, page_groups = parse_page_range(
        OpCtx.get_page_range_arg(),
        OpCtx.current_page_count,
        OpCtx.current_pdf_path,
        getattr(OpCtx.args, 'filter_matches', None),
        getattr(OpCtx.args, 'group_start', None),
        getattr(OpCtx.args, 'group_end', None)
    )
    
    # Store and return
    OpCtx.store_parsed_results(selected_pages, range_description, page_groups)
    return selected_pages, range_description, page_groups


# End of file #
