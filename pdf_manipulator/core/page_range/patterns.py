"""
Pattern Matching for Page Selection - Comma-Free Architecture  
File: pdf_manipulator/core/page_range/patterns.py

FIXED: Removed comma detection logic since comma parsing now happens at parser level.
This module now focuses solely on pattern matching for single expressions.

ENHANCED: Now uses pdfplumber's raw extract_text() for text extraction, which
properly reconstructs lines based on character positioning. This fixes issues
where pypdf splits lines incorrectly, causing regex patterns to fail on OCR'd PDFs.

Features:
- Single pattern detection: contains:, type:, size:, regex:, line-starts:
- Range pattern detection: "X to Y" patterns
- Pattern parsing and evaluation
- Quote-aware utilities for use by parser
- No comma detection - parser handles that
- Unified text extraction (core.text_extraction) shared with the scraper
"""

import re

from pypdf import PdfReader
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_analysis import PageAnalyzer
from pdf_manipulator.core.text_extraction import get_page_texts, clear_text_cache
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
from pdf_manipulator.core.page_range.page_group import PageGroup


console = Console()


#################################################################################################
# Text Extraction (delegated to the unified provider)

def _clear_extraction_cache():
    """Clear the shared extraction cache (useful for testing)."""
    clear_text_cache()


def _extract_all_page_texts(pdf_path: Path, total_pages: int) -> list[str]:
    """
    Get text for all pages via the unified text provider.

    Delegates to pdf_manipulator.core.text_extraction so page-selection
    patterns and scraper patterns are guaranteed to see identical text
    (sidecar text file if registered, else raw pdfplumber, else pypdf).
    Results are cached per PDF by the provider.

    Args:
        pdf_path: Path to the PDF file
        total_pages: Number of pages to extract

    Returns:
        List of text strings, one per page (0-indexed)
    """
    return get_page_texts(pdf_path, total_pages)


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
    """
    Check if string looks like a range pattern, respecting quoted strings.

    The ' to ' separator is matched case-insensitively ('TO', 'To', 'tO'),
    since it must be surrounded by spaces and is unambiguous in any case.
    Quoted text like contains:'A to B' never triggers detection.
    """
    return _contains_unquoted_text(range_str, ' to ', case_sensitive=False)


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
    # Extract start and end patterns (' to ' separator, any case)
    if ' to ' not in expression.lower():
        raise ValueError(f"Range pattern must contain ' to ': {expression}")
    
    # Split on ' to ' while respecting quotes, case-insensitively
    parts = _split_on_unquoted_text(expression, ' to ', case_sensitive=False)
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
    parts.append(current_part.strip())
    
    return parts


#################################################################################################
# Private helper functions

def _is_valid_pattern_value(value_part: str) -> bool:
    """Check if the value part of a pattern is valid."""
    # Empty value is invalid
    if not value_part or not value_part.strip():
        return False
    
    value_part = value_part.strip()
    
    # For quoted values, ensure there's content inside quotes
    if value_part.startswith('"') and value_part.endswith('"'):
        return len(value_part) > 2
    elif value_part.startswith("'") and value_part.endswith("'"):
        return len(value_part) > 2
    
    # For unquoted values, must be non-empty
    return bool(value_part)


def _contains_unquoted_text(text: str, search_text: str, case_sensitive: bool = True) -> bool:
    """Check if text contains search_text outside of quoted strings."""
    haystack = text if case_sensitive else text.lower()
    needle = search_text if case_sensitive else search_text.lower()
    if needle not in haystack:
        return False
    text = haystack  # Compare against the normalized form below
    search_text = needle
    
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escapes
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        # Handle quotes
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif not in_quote and text[i:i+len(search_text)] == search_text:
            return True
        
        i += 1
    
    return False


def _split_on_unquoted_text(text: str, separator: str, case_sensitive: bool = True) -> list[str]:
    """
    Split text on separator, but only when separator is outside quotes.

    With case_sensitive=False the separator matches in any case while the
    returned parts keep the original text untouched (only the separator
    match itself is case-folded).
    """
    compare_text = text if case_sensitive else text.lower()
    compare_sep = separator if case_sensitive else separator.lower()
    if compare_sep not in compare_text:
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
        elif not in_quote and compare_text[i:i+len(compare_sep)] == compare_sep:
            # Found unquoted separator - split here
            parts.append(current_part)
            current_part = ""
            i += len(compare_sep) - 1  # Skip separator (will be incremented at end of loop)
        else:
            current_part += char
        
        i += 1
    
    # Add final part
    parts.append(current_part)
    
    return parts


def _parse_single_pattern_with_offset(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse a single pattern expression and return matching page numbers."""
    # Check for offset modifiers (+N or -N at the end)
    offset = 0
    base_expression = expression
    
    # Match offset at end: +5, -3, etc.
    offset_match = re.search(r'([+-]\d+)$', expression)
    if offset_match:
        offset = int(offset_match.group(1))
        base_expression = expression[:offset_match.start()]
    
    # Get matching pages for the base pattern
    matching_pages = _evaluate_pattern(base_expression, pdf_path, total_pages)
    
    # Apply offset
    if offset != 0:
        matching_pages = [p + offset for p in matching_pages]
        # Filter to valid range
        matching_pages = [p for p in matching_pages if 1 <= p <= total_pages]
    
    return matching_pages


def _evaluate_pattern(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """
    Evaluate a pattern expression and return matching page numbers.
    
    Uses pdfplumber's raw extract_text() for text extraction, which properly
    reconstructs lines based on character positioning. This fixes issues where
    pypdf splits lines incorrectly on OCR'd PDFs.
    """
    if not pdf_path or not pdf_path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")
    
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
    
    # Extract all page texts upfront using tuned pdfplumber (or pypdf fallback)
    # This is the key improvement - pdfplumber's adaptive spacing reconstructs
    # text correctly, keeping "Place of receipt VALDEZ, AK" on one line instead
    # of splitting it across multiple lines like pypdf does.
    page_texts = _extract_all_page_texts(pdf_path, total_pages)
    
    matching_pages = []
    
    # For type: and size: patterns, delegate to PageAnalyzer, validating the
    # value FIRST so "type:invalid" or "size:badformat" fail loudly instead of
    # silently matching nothing (or everything)
    if pattern_type == 'type':
        valid_types = ('text', 'image', 'mixed', 'empty')
        if value.lower() not in valid_types:
            raise ValueError(
                f"Invalid page type '{value}': must be one of {', '.join(valid_types)}"
            )
        try:
            with PageAnalyzer(pdf_path) as analyzer:
                matching_pages = analyzer.get_pages_by_type(value.lower())
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error processing PDF: {e}")
    elif pattern_type == 'size':
        if not re.match(r'^(<=|>=|<|>|=)\d+(?:\.\d+)?\s*(B|KB|MB|GB)?$', value.strip(), re.IGNORECASE):
            raise ValueError(
                f"Invalid size condition '{value}': expected forms like "
                f"'<500KB', '>1MB', '>=2MB', '<=100KB'"
            )
        try:
            with PageAnalyzer(pdf_path) as analyzer:
                matching_pages = analyzer.get_pages_by_size(value.strip())
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error processing PDF: {e}")
    else:
        # For text-based patterns (contains, regex, line-starts), use extracted texts
        for page_num in range(1, total_pages + 1):
            text = page_texts[page_num - 1] if page_num <= len(page_texts) else ""
            if _text_matches_pattern(text, pattern_type, value, is_case_insensitive):
                matching_pages.append(page_num)
    
    return matching_pages


def _text_matches_pattern(text: str, pattern_type: str, value: str, case_insensitive: bool) -> bool:
    """
    Check if text matches the given pattern.
    
    This function receives pre-extracted text (from pdfplumber's raw extraction),
    which has proper line reconstruction for OCR'd PDFs.
    """
    if not text:
        return False
    
    try:
        if pattern_type == 'contains':
            if case_insensitive:
                return value.lower() in text.lower()
            else:
                return value in text
        
        elif pattern_type == 'regex':
            flags = re.IGNORECASE if case_insensitive else 0
            return bool(re.search(value, text, flags))
        
        elif pattern_type == 'line-starts':
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
            raise ValueError(f"Unknown text pattern type: {pattern_type}")
            
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
