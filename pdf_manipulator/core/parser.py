"""Page range parsing functionality."""

import re

from pypdf import PdfReader
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PageGroup:
    pages: list[int]
    is_range: bool
    original_spec: str


# def parse_page_range(range_str: str, total_pages: int) -> tuple[set[int], str, list[PageGroup]]:
#     """
#     Parse page range string and return set of page numbers (1-indexed), description, and groupings.
def parse_page_range(range_str: str, total_pages: int, pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Parse page range string and return set of page numbers (1-indexed), description, and groupings.

    NEW: Pattern-based selection (when pdf_path provided):
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
    pages = set()
    descriptions = []
    groups = []  # Track the original groupings\
    
    # Remove quotes and extra spaces
    range_str = range_str.strip().strip('"\'')
    
    # Check for pattern-based selection FIRST (only if pdf_path provided)
    if pdf_path and _looks_like_pattern(range_str):
        try:
            matching_pages = _parse_pattern_expression(range_str, pdf_path, total_pages)
            
            if not matching_pages:
                raise ValueError(f"No pages found matching pattern: {range_str}")
            
            pages = set(matching_pages)
            desc = _create_pattern_description(range_str)
            groups = [PageGroup(list(pages), True, range_str)]
            return pages, desc, groups
            
        except ValueError:
            # If pattern parsing fails, fall through to normal parsing
            pass
    
    # NEW: Handle "all" keyword
    if range_str.lower() == "all":
        pages = set(range(1, total_pages + 1))
        groups = [PageGroup(list(pages), True, "all")]
        return pages, "all", groups

    # NEW: Detect if someone passed a filename instead of a range
    if '.' in range_str and (range_str.endswith('.pdf') or '/' in range_str or '\\' in range_str):
        raise ValueError(f"'{range_str}' looks like a filename, not a page range. Use 'all' to extract all pages.")

    # Handle comma-separated ranges
    parts = [p.strip() for p in range_str.split(',')]

    for part in parts:
        try:
            group_pages = []  # Pages in this specific group
            
            # Check for slicing syntax (contains :: or single : with 3 parts)
            if '::' in part or (part.count(':') == 2):
                # Parse slicing: start:stop:step
                slice_parts = part.split(':')
                start = int(slice_parts[0]) if slice_parts[0] else 1
                stop = int(slice_parts[1]) if slice_parts[1] else total_pages
                step = int(slice_parts[2]) if len(slice_parts) > 2 and slice_parts[2] else 1

                # Make stop inclusive for user-friendliness
                for p in range(start, stop + 1, step):
                    if 1 <= p <= total_pages:
                        pages.add(p)
                        group_pages.append(p)

                groups.append(PageGroup(group_pages, True, part))  # Step syntax is treated as range

                if not slice_parts[0] and not slice_parts[1]:
                    if step == 2:
                        descriptions.append("odd" if start == 1 else "even")
                    else:
                        descriptions.append(f"every-{step}")
                else:
                    descriptions.append(f"{start}-{stop}-step{step}")

            # Check for "first N" syntax
            elif part.lower().startswith('first'):
                match = re.match(r'first[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(1, min(n + 1, total_pages + 1)):
                        pages.add(p)
                        group_pages.append(p)
                    groups.append(PageGroup(group_pages, True, part))  # "first N" is treated as range
                    descriptions.append(f"first{n}")

            # Check for "last N" syntax
            elif part.lower().startswith('last'):
                match = re.match(r'last[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(max(1, total_pages - n + 1), total_pages + 1):
                        pages.add(p)
                        group_pages.append(p)
                    groups.append(PageGroup(group_pages, True, part))  # "last N" is treated as range
                    descriptions.append(f"last{n}")

            # Check for range syntax
            elif any(sep in part for sep in ['-', ':', '..']):
                # Find the separator
                sep = next(s for s in ['-', ':', '..'] if s in part)
                if sep == '..':
                    start_str, end_str = part.split('..')
                else:
                    # Be careful with negative numbers
                    parts_split = part.split(sep, 1)
                    start_str = parts_split[0]
                    end_str = parts_split[1] if len(parts_split) > 1 else ''

                # Parse start and end
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else total_pages

                if start > end:
                    raise ValueError(f"Invalid range: {start} > {end}")

                for p in range(start, end + 1):
                    if 1 <= p <= total_pages:
                        pages.add(p)
                        group_pages.append(p)

                groups.append(PageGroup(group_pages, True, part))  # Range syntax is treated as range
                descriptions.append(f"{start}-{end}")

            # Single page number
            else:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    pages.add(page_num)
                    group_pages.append(page_num)
                    groups.append(PageGroup(group_pages, False, part))  # Single page
                    descriptions.append(str(page_num))
                else:
                    raise ValueError(f"Page {page_num} out of range (1-{total_pages})")

        except ValueError as e:
            raise ValueError(f"Invalid page range '{part}': {str(e)}")

    if not pages:
        raise ValueError("No valid pages in range")

    # Create description for filename
    if len(descriptions) == 1:
        desc = descriptions[0]
    else:
        # Simplify if multiple parts
        desc = ",".join(descriptions)
        if len(desc) > 20:  # Keep filename reasonable
            desc = f"{min(pages)}-{max(pages)}-selected"

    # Format description
    if ',' in desc:
        desc = f"pages{desc}"
    elif any(d in desc for d in ['odd', 'even', 'every', 'first', 'last']):
        desc = desc  # Keep as is
    elif '-' in desc and not desc.startswith('pages'):
        desc = f"pages{desc}"
    else:
        desc = f"page{desc}"

    return pages, desc, groups



def _looks_like_pattern(range_str: str) -> bool:
    """Check if string looks like a pattern expression."""
    return any([
        range_str.startswith(('contains', 'regex', 'line-starts')),
        ':' in range_str and any(range_str.lower().startswith(p) for p in ['contains', 'regex', 'line-starts']),
    ])


def _create_pattern_description(range_str: str) -> str:
    """Create filename-safe description from pattern."""
    if len(range_str) > 15:
        return "pattern-match"
    safe = re.sub(r'[^\w\-]', '-', range_str)
    return safe[:15]


def _parse_pattern_expression(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse pattern expression and return matching page numbers."""
    
    # For now, implement simple single patterns only
    # (Complex AND/OR logic can be added in Phase 3)
    
    return _parse_single_pattern_with_offset(expression, pdf_path, total_pages)


def _parse_single_pattern_with_offset(pattern_str: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse single pattern with optional offset."""
    
    # Parse offset: pattern+N, pattern-N
    offset_match = re.search(r'([+-]\d+)$', pattern_str)
    if offset_match:
        offset = int(offset_match.group(1))
        base_pattern = pattern_str[:offset_match.start()]
    else:
        offset = 0
        base_pattern = pattern_str
    
    # Get base matches
    base_matches = _parse_base_pattern(base_pattern, pdf_path)
    
    # Apply offset
    result_pages = []
    for match_page in base_matches:
        target_page = match_page + offset
        if 1 <= target_page <= total_pages:
            result_pages.append(target_page)
    
    return sorted(list(set(result_pages)))


def _parse_base_pattern(pattern: str, pdf_path: Path) -> list[int]:
    """Parse base pattern (no offsets)."""
    
    # Parse case sensitivity and quoted literals
    case_sensitive = True
    if '/i:' in pattern:
        pattern_type, pattern_value = pattern.split('/i:', 1)
        case_sensitive = False
    elif ':' in pattern:
        pattern_type, pattern_value = pattern.split(':', 1)
    else:
        raise ValueError(f"Invalid pattern format: {pattern}")
    
    # Handle quoted literals (remove quotes, no offset parsing)
    if ((pattern_value.startswith('"') and pattern_value.endswith('"')) or
        (pattern_value.startswith("'") and pattern_value.endswith("'"))):
        pattern_value = pattern_value[1:-1]  # Remove quotes
    
    # Find matching pages
    return _find_pages_by_pattern(pdf_path, pattern_type, pattern_value, case_sensitive)


def _find_pages_by_pattern(pdf_path: Path, pattern_type: str, pattern_value: str, case_sensitive: bool) -> list[int]:
    """Find pages matching a specific pattern."""
    
    matching_pages = []
    
    try:
        reader = PdfReader(pdf_path)
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if not case_sensitive:
                page_text = page_text.lower()
                search_value = pattern_value.lower()
            else:
                search_value = pattern_value
            
            matched = False
            
            if pattern_type == 'contains':
                matched = search_value in page_text
                
            elif pattern_type == 'line-starts':
                lines = page_text.split('\n')
                matched = any(line.strip().startswith(search_value) for line in lines)
                
            elif pattern_type == 'regex':
                flags = 0 if case_sensitive else re.IGNORECASE
                matched = bool(re.search(pattern_value, page_text, flags))
            
            if matched:
                matching_pages.append(i + 1)  # Convert to 1-indexed
                
    except Exception as e:
        raise ValueError(f"Error searching for pattern: {e}")
    
    return matching_pages
