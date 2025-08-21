"""
Pattern Matching for Page Selection - No Comma Detection
File: pdf_manipulator/core/page_range/patterns.py

FIXED: Removed comma detection logic since comma parsing now happens at parser level.
"""

import re

from pypdf import PdfReader
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_analysis import PageAnalyzer
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
from pdf_manipulator.core.page_range.page_group import PageGroup


console = Console()


#################################################################################################
# Public API functions

def looks_like_pattern(range_str: str) -> bool:
    """
    Check if string looks like a pattern expression.
    
    FIXED: No comma detection - that happens at parser level now.
    """
    # Simple pattern detection - no comma checking needed
    return any([
        range_str.startswith(('contains:', 'regex:', 'line-starts:', 'type:', 'size:')),
        ':' in range_str and any(range_str.lower().startswith(p + ':') for p in ['contains', 'regex', 'line-starts', 'type', 'size']),
    ])


def looks_like_range_pattern(range_str: str) -> bool:
    """Check if string looks like a range pattern, respecting quoted strings."""
    return _contains_unquoted_text(range_str, ' to ')


def parse_pattern_expression(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse pattern expression and return matching page numbers."""
    return _parse_single_pattern_with_offset(expression, pdf_path, total_pages)


def parse_range_pattern(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """
    Parse range patterns like 'contains:A to contains:B' and find ALL matching sections.
    
    This is the backward-compatible version that just returns pages.
    For grouping information, use parse_range_pattern_with_groups().
    """
    all_pages, _ = parse_range_pattern_with_groups(expression, pdf_path, total_pages)
    return all_pages


def parse_range_pattern_with_groups(expression: str, pdf_path: Path, total_pages: int) -> tuple[list[int], list[PageGroup]]:
    """
    Parse range patterns and return both pages and groups.
    
    Finds ALL matching A...B sections, not just first A to last B.
    """
    # Extract start and end patterns
    if ' to ' not in expression:
        raise ValueError(f"Range pattern must contain ' to ': {expression}")
    
    # Split on ' to ' while respecting quotes
    parts = _split_on_unquoted_text(expression, ' to ')
    if len(parts) != 2:
        raise ValueError(f"Range pattern must have exactly one ' to ' separator: {expression}")
    
    start_pattern, end_pattern = parts
    start_pattern = start_pattern.strip()
    end_pattern = end_pattern.strip()
    
    # Find all matching sections
    sections = _find_all_range_sections(start_pattern, end_pattern, pdf_path, total_pages)
    
    # Combine all pages and create groups
    all_pages = []
    groups = []
    
    for i, (start_page, end_page) in enumerate(sections):
        section_pages = list(range(start_page, end_page + 1))
        all_pages.extend(section_pages)
        
        # Create group for this section
        group = PageGroup(
            pages=section_pages,
            is_range=True,
            original_spec=f"{expression} (section {i+1})"
        )
        groups.append(group)
    
    return all_pages, groups


def parse_single_expression(expr: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse single expression - could be pattern or page number."""
    expr = expr.strip()
    
    # Try as pattern first
    if looks_like_pattern(expr):
        return parse_pattern_expression(expr, pdf_path, total_pages)
    
    # Try as simple page number
    if expr.isdigit():
        page_num = int(expr)
        if 1 <= page_num <= total_pages:
            return [page_num]
        else:
            raise ValueError(f"Page number {page_num} out of range (1-{total_pages})")
    
    # Try as simple range
    if re.match(r'^\d+-\d+$', expr):
        start_str, end_str = expr.split('-')
        start, end = int(start_str), int(end_str)
        
        if not (1 <= start <= total_pages and 1 <= end <= total_pages):
            raise ValueError(f"Page numbers out of range: {expr}")
        
        if start <= end:
            return list(range(start, end + 1))
        else:
            return list(range(start, end - 1, -1))
    
    raise ValueError(f"Could not parse expression: {expr}")


def split_comma_respecting_quotes(text: str) -> list[str]:
    """
    Split text on commas while respecting quoted strings.
    
    This function splits on commas that are NOT inside quoted strings,
    properly handling both single and double quotes.
    
    Examples:
        'a,b,c' → ['a', 'b', 'c']
        'contains:"CORDOVA, AK",contains:"CRAIG, AK"' → ['contains:"CORDOVA, AK"', 'contains:"CRAIG, AK"']
        "a,'b,c',d" → ['a', "'b,c'", 'd']
    """
    if ',' not in text:
        return [text]
    
    parts = []
    current_part = ""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escape sequences
        if char == '\\' and i + 1 < len(text):
            # Add the escape and the escaped character
            current_part += char + text[i + 1]
            i += 2
            continue
        
        # Handle quote start/end
        if char in ['"', "'"] and not in_quote:
            # Starting a quote
            in_quote = True
            quote_char = char
            current_part += char
        elif char == quote_char and in_quote:
            # Ending the quote
            in_quote = False
            quote_char = None
            current_part += char
        elif char == ',' and not in_quote:
            # Comma outside quotes - split here
            parts.append(current_part.strip())
            current_part = ""
        else:
            # Regular character
            current_part += char
        
        i += 1
    
    # Add the last part
    if current_part or text.endswith(','):
        parts.append(current_part.strip())
    
    return parts


#################################################################################################
# Private helper functions

def _contains_unquoted_text(text: str, search_text: str) -> bool:
    """Check if text contains search_text outside quoted strings."""
    in_quote = False
    quote_char = None
    i = 0
    
    while i <= len(text) - len(search_text):
        char = text[i]
        
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif not in_quote:
            if text[i:i+len(search_text)] == search_text:
                return True
        
        i += 1
    
    return False


def _split_on_unquoted_text(text: str, separator: str) -> list[str]:
    """Split text on separator while respecting quoted strings."""
    parts = []
    current_part = ""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escape sequences
        if char == '\\' and i + 1 < len(text):
            current_part += char + text[i + 1]
            i += 2
            continue
        
        # Handle quotes
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
            current_part += char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current_part += char
        elif not in_quote and text[i:i+len(separator)] == separator:
            # Found separator outside quotes
            parts.append(current_part)
            current_part = ""
            i += len(separator)
            continue
        else:
            current_part += char
        
        i += 1
    
    # Add the last part
    parts.append(current_part)
    return parts


def _find_all_range_sections(start_pattern: str, end_pattern: str, pdf_path: Path, total_pages: int) -> list[tuple[int, int]]:
    """Find all sections that match start_pattern...end_pattern."""
    sections = []
    
    # Get pages that match start and end patterns
    start_pages = set(_parse_single_pattern_with_offset(start_pattern, pdf_path, total_pages))
    end_pages = set(_parse_single_pattern_with_offset(end_pattern, pdf_path, total_pages))
    
    # Find all valid start...end pairs
    for start_page in sorted(start_pages):
        # Find the next end page after this start
        valid_end_pages = [ep for ep in end_pages if ep >= start_page]
        if valid_end_pages:
            end_page = min(valid_end_pages)
            sections.append((start_page, end_page))
    
    return sections


def _parse_single_pattern_with_offset(pattern: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse a single pattern and return matching page numbers."""
    pattern = pattern.strip()
    
    # Extract pattern type and value
    if ':' not in pattern:
        raise ValueError(f"Pattern must contain ':' separator: {pattern}")
    
    pattern_type, pattern_value = pattern.split(':', 1)
    pattern_type = pattern_type.lower().strip()
    pattern_value = pattern_value.strip()
    
    # Remove quotes from pattern value if present
    if ((pattern_value.startswith('"') and pattern_value.endswith('"')) or
        (pattern_value.startswith("'") and pattern_value.endswith("'"))):
        pattern_value = pattern_value[1:-1]
    
    # Handle different pattern types
    if pattern_type == 'contains':
        return _find_pages_containing_text(pattern_value, pdf_path, total_pages)
    elif pattern_type == 'type':
        return _find_pages_by_type(pattern_value, pdf_path, total_pages)
    elif pattern_type == 'size':
        return _find_pages_by_size(pattern_value, pdf_path, total_pages)
    elif pattern_type == 'regex':
        return _find_pages_by_regex(pattern_value, pdf_path, total_pages)
    elif pattern_type == 'line-starts':
        return _find_pages_by_line_starts(pattern_value, pdf_path, total_pages)
    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")


def _find_pages_containing_text(search_text: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Find pages containing specific text."""
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_containing_text(search_text)
            
        if not matching_pages:
            console.print(f"[dim]No pages found containing '{search_text}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing pages for text '{search_text}': {e}")


def _find_pages_by_type(page_type: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Find pages by type (text, image, mixed, empty)."""
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_by_type(page_type)
            
        if not matching_pages:
            console.print(f"[dim]No pages found of type '{page_type}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing page types: {e}")


def _find_pages_by_size(size_condition: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Find pages by size condition (e.g., '>1MB', '<500KB')."""
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_by_size(size_condition)
            
        if not matching_pages:
            console.print(f"[dim]No pages found matching size condition '{size_condition}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing page sizes: {e}")


def _find_pages_by_regex(regex_pattern: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Find pages matching regex pattern."""
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_by_regex(regex_pattern)
            
        if not matching_pages:
            console.print(f"[dim]No pages found matching regex '{regex_pattern}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing pages with regex '{regex_pattern}': {e}")


def _find_pages_by_line_starts(line_start: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Find pages with lines starting with specific text."""
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_with_line_starts(line_start)
            
        if not matching_pages:
            console.print(f"[dim]No pages found with lines starting with '{line_start}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing pages for line starts '{line_start}': {e}")


# End of file #
