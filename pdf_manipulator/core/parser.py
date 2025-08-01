"""Page range parsing functionality."""

from pathlib import Path

from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser, PageGroup


# Simplified main function
def parse_page_range(range_str: str, total_pages: int, 
                        pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Parse page range string and return set of page numbers (1-indexed), description, and groupings.

    NEW: Range-based selection (when pdf_path provided):
    - contains:'Chapter 1' to contains:'Chapter 2'  - from pattern to pattern
    - 5 to contains:'Appendix'                      - from page to pattern
    - contains:'Start' to 10                        - from pattern to page
    - contains:'Ch 1'+1 to contains:'Ch 2'-1        - with offsets

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
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)
