"""
Pattern Matching for Page Selection - Comma-Free Architecture  
File: pdf_manipulator/core/page_range/patterns.py

FIXED: Removed comma detection logic since comma parsing now happens at parser level.
This module now focuses solely on pattern matching for single expressions.

Features:
- Single pattern detection: contains:, type:, size:, regex:, line-starts:
- Range pattern detection: "X to Y" patterns
- Pattern parsing and evaluation
- Quote-aware utilities for use by parser
- No comma detection - parser handles that
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
    range_str = range_str.strip()
    
    # Must contain a colon to be a pattern
    if ':' not in range_str:
        return False
    
    # Check for valid pattern prefixes
    pattern_prefixes = ['contains', 'regex', 'line-starts', 'type', 'size']
    
    for prefix in pattern_prefixes:
        # Handle case-insensitive patterns: "contains/i:"
        if range_str.lower().startswith(prefix + '/i:'):
            value_part = range_str[len(prefix) + 3:]  # Skip "prefix/i:"
            return _is_valid_pattern_value(value_part)
        # Handle regular patterns: "contains:"
        elif range_str.lower().startswith(prefix + ':'):
            value_part = range_str[len(prefix) + 1:]  # Skip "prefix:"
            return _is_valid_pattern_value(value_part)
    
    return False


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
    
    This function is used by the main parser for comma separation.
    It's the ONLY comma-related function that should remain in this module.
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
        
        # Handle escapes
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
        elif char == ',' and not in_quote:
            # Found unquoted comma - split here
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
        
        i += 1
    
    # Add final part
    if current_part:
        parts.append(current_part.strip())
    
    return parts


#################################################################################################
# Private helper functions

def _is_valid_pattern_value(value: str) -> bool:
    """Validate that a pattern has a non-empty value."""
    # Empty value is invalid (this fixes 'contains:')
    if not value or not value.strip():
        return False
    
    # For quoted values, ensure there's content inside quotes
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return len(value) > 2  # More than just quotes
    elif value.startswith("'") and value.endswith("'"):
        return len(value) > 2  # More than just quotes
    
    # For unquoted values, must be non-empty
    return bool(value)


def _contains_unquoted_text(text: str, search_text: str) -> bool:
    """Check if text contains search_text outside quoted strings."""
    if search_text not in text:
        return False
    
    # Find all occurrences of search_text
    start = 0
    while True:
        pos = text.find(search_text, start)
        if pos == -1:
            break
        
        # Check if this occurrence is outside quotes
        if not _is_position_quoted(text, pos):
            return True
        
        start = pos + len(search_text)
    
    return False


def _is_position_quoted(text: str, pos: int) -> bool:
    """Check if position is inside quoted string."""
    in_quote = False
    quote_char = None
    
    for i, char in enumerate(text):
        if i == pos:
            return in_quote
        
        if char == '\\' and i + 1 < len(text):
            i += 1  # Skip escaped character
            continue
        
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
    
    return False


def _split_on_unquoted_text(text: str, separator: str) -> list[str]:
    """Split text on separator while respecting quoted strings."""
    if separator not in text:
        return [text]
    
    parts = []
    current_part = ""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escapes
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
            # Found unquoted separator - split here
            parts.append(current_part)
            current_part = ""
            i += len(separator) - 1  # Skip separator (will be incremented at end of loop)
        else:
            current_part += char
        
        i += 1
    
    # Add final part
    parts.append(current_part)
    
    return parts


def _parse_single_pattern_with_offset(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse a single pattern expression and return matching page numbers."""
    # This would contain the actual pattern matching logic
    # For now, provide a basic implementation that can be expanded
    
    if not pdf_path or not pdf_path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")
    
    # Basic pattern parsing - this should be expanded with full implementation
    expression = expression.strip()
    
    # Parse pattern type and value
    if ':' not in expression:
        raise ValueError(f"Invalid pattern format: {expression}")
    
    # Handle case-insensitive patterns
    is_case_insensitive = False
    if '/i:' in expression:
        pattern_type, value = expression.split('/i:', 1)
        is_case_insensitive = True
    else:
        pattern_type, value = expression.split(':', 1)
    
    pattern_type = pattern_type.lower().strip()
    value = value.strip()
    
    # Remove quotes if present
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    
    if not value:
        raise ValueError(f"Empty pattern value: {expression}")
    
    # This is a simplified implementation - should be expanded with full PDF analysis
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            matching_pages = []
            
            for page_num in range(1, min(total_pages + 1, len(reader.pages) + 1)):
                if _page_matches_pattern(reader.pages[page_num - 1], pattern_type, value, is_case_insensitive):
                    matching_pages.append(page_num)
            
            return matching_pages
            
    except Exception as e:
        raise ValueError(f"Error processing PDF: {e}")


def _page_matches_pattern(page, pattern_type: str, value: str, case_insensitive: bool) -> bool:
    """Check if a page matches the given pattern."""
    # Simplified pattern matching - should be expanded with full implementation
    
    try:
        if pattern_type == 'contains':
            text = page.extract_text()
            if case_insensitive:
                return value.lower() in text.lower()
            else:
                return value in text
        
        elif pattern_type == 'type':
            # Simplified type detection - should use PageAnalyzer
            if value.lower() == 'text':
                text = page.extract_text().strip()
                return len(text) > 50  # Simple heuristic
            elif value.lower() == 'image':
                # Check for images - simplified
                return '/XObject' in str(page.get('/Resources', {}))
            else:
                return False
        
        elif pattern_type == 'size':
            # Simplified size detection - should be more sophisticated
            return True  # Placeholder
        
        elif pattern_type == 'regex':
            text = page.extract_text()
            flags = re.IGNORECASE if case_insensitive else 0
            return bool(re.search(value, text, flags))
        
        elif pattern_type == 'line-starts':
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if case_insensitive:
                    if line.lower().startswith(value.lower()):
                        return True
                else:
                    if line.startswith(value):
                        return True
            return False
        
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
            
    except Exception:
        return False


def _find_all_range_sections(start_pattern: str, end_pattern: str, pdf_path: Path, total_pages: int) -> list[tuple[int, int]]:
    """Find all sections matching the range pattern."""
    # Find all pages matching start pattern
    start_pages = parse_pattern_expression(start_pattern, pdf_path, total_pages)
    
    # Find all pages matching end pattern  
    end_pages = parse_pattern_expression(end_pattern, pdf_path, total_pages)
    
    if not start_pages:
        raise ValueError(f"No pages found matching start pattern: {start_pattern}")
    
    if not end_pages:
        raise ValueError(f"No pages found matching end pattern: {end_pattern}")
    
    # Find all valid start->end sections
    sections = []
    
    for start_page in sorted(start_pages):
        # Find the next end page after this start page
        valid_end_pages = [ep for ep in end_pages if ep >= start_page]
        if valid_end_pages:
            end_page = min(valid_end_pages)
            sections.append((start_page, end_page))
    
    if not sections:
        raise ValueError(f"No valid sections found from '{start_pattern}' to '{end_pattern}'")
    
    return sections


# End of file #
