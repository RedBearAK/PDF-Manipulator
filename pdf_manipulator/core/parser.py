"""Page range parsing functionality with unified boolean processing."""

from pathlib import Path

from pdf_manipulator.core.page_range.utils import sanitize_filename
from pdf_manipulator.core.page_range.boolean import (
    looks_like_boolean_expression,
    evaluate_boolean_expression_with_groups
)
from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser, PageGroup


def parse_page_range(range_str: str, total_pages: int, 
                        pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Parse page range string and return set of page numbers (1-indexed), description, and groupings.

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

    Returns: (set of page numbers, description for filename, list of page groups)
    """
    
    # Check if this is a boolean expression (simple or advanced)
    if pdf_path and looks_like_boolean_expression(range_str):
        return _parse_with_boolean_processor(range_str, pdf_path, total_pages)
    
    # Standard parsing for non-boolean expressions
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)


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
