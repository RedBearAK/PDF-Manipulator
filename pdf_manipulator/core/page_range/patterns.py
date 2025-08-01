import re

from pypdf import PdfReader
from pathlib import Path


#################################################################################################
# Public API functions

def looks_like_pattern(range_str: str) -> bool:
    """Check if string looks like a pattern expression."""
    return any([
        range_str.startswith(('contains', 'regex', 'line-starts')),
        ':' in range_str and any(range_str.lower().startswith(p) for p in ['contains', 'regex', 'line-starts']),
    ])


def looks_like_range_pattern(range_str: str) -> bool:
    """Check if string looks like a range pattern."""
    return ' to ' in range_str.lower()


def parse_pattern_expression(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse pattern expression and return matching page numbers."""
    
    # For now, implement simple single patterns only
    # (Complex AND/OR logic can be added in Phase 3)
    
    return _parse_single_pattern_with_offset(expression, pdf_path, total_pages)


def parse_range_pattern(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """
    Parse range patterns like 'contains:A to contains:B' or '5 to contains:End'
    
    Supports:
    - Pattern to pattern: contains:'Chapter 1' to contains:'Chapter 2'
    - Number to pattern: 5 to contains:'Appendix'
    - Pattern to number: contains:'Start' to 10
    - With offsets: contains:'Ch 1'+1 to contains:'Ch 2'-1
    """
    
    # Split on ' to ' (case insensitive)
    if ' to ' not in expression.lower():
        raise ValueError("Range pattern must contain ' to '")
    
    # Find the ' to ' separator (case insensitive)
    lower_expr = expression.lower()
    to_pos = lower_expr.find(' to ')
    
    start_expr = expression[:to_pos].strip()
    end_expr = expression[to_pos + 4:].strip()  # +4 for ' to '
    
    # Parse start expression
    start_pages = parse_single_expression(start_expr, pdf_path, total_pages)
    if not start_pages:
        raise ValueError(f"No pages found for start pattern: {start_expr}")
    start_page = min(start_pages)  # Use first matching page
    
    # Parse end expression  
    end_pages = parse_single_expression(end_expr, pdf_path, total_pages)
    if not end_pages:
        raise ValueError(f"No pages found for end pattern: {end_expr}")
    end_page = max(end_pages)  # Use last matching page
    
    if start_page > end_page:
        raise ValueError(f"Start page {start_page} is after end page {end_page}")
    
    return list(range(start_page, end_page + 1))


def parse_single_expression(expr: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse single expression - could be pattern or page number."""
    
    # Try to parse as simple number first
    try:
        page_num = int(expr)
        if 1 <= page_num <= total_pages:
            return [page_num]
        else:
            raise ValueError(f"Page {page_num} out of range (1-{total_pages})")
    except ValueError:
        pass
    
    # Must be a pattern - use existing pattern parsing
    return _parse_single_pattern_with_offset(expr, pdf_path, total_pages)

#################################################################################################
# Private helper functions (used inside module only)

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
