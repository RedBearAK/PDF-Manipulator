"""
Pattern Matching for Page Selection - Comma-Free Architecture  
File: pdf_manipulator/core/page_range/patterns.py

FIXED: Removed comma detection logic since comma parsing now happens at parser level.
This module now focuses solely on pattern matching for single expressions.

ENHANCED: Now uses pdfplumber with tuned adaptive spacing for text extraction,
which dramatically improves pattern matching accuracy on OCR'd PDFs.

Features:
- Single pattern detection: contains:, type:, size:, regex:, line-starts:
- Range pattern detection: "X to Y" patterns
- Pattern parsing and evaluation
- Quote-aware utilities for use by parser
- No comma detection - parser handles that
- Tuned pdfplumber text extraction for reliable pattern matching
"""

import re

from pypdf import PdfReader
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_analysis import PageAnalyzer
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
from pdf_manipulator.core.page_range.page_group import PageGroup

# Try to import the tuned pdfplumber processor for better text extraction
try:
    from simple_pdf_scraper.processors.pdfplumber_processor import PDFPlumberProcessor
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


console = Console()


#################################################################################################
# Text Extraction Helper (NEW)

def _extract_all_page_texts(pdf_path: Path, total_pages: int) -> list[str]:
    """
    Extract text from all pages using pdfplumber (tuned) or pypdf fallback.
    
    The pdfplumber processor uses empirically-tuned adaptive spacing that
    dramatically improves text reconstruction from OCR'd PDFs. This fixes
    issues where pypdf splits lines incorrectly, causing regex patterns to fail.
    
    Args:
        pdf_path: Path to the PDF file
        total_pages: Number of pages to extract
        
    Returns:
        List of text strings, one per page (0-indexed)
    """
    if PDFPLUMBER_AVAILABLE:
        try:
            # Use the tuned processor with empirically-tested defaults:
            # - add_space_ratio=1.1 prevents over-insertion while catching concatenated text
            # - add_tab_ratio=1.3 creates structural boundaries
            # - Both values automatically adapt to any font size
            processor = PDFPlumberProcessor()
            all_texts = processor.extract_pages(pdf_path)
            
            # Ensure we have the right number of pages
            if len(all_texts) >= total_pages:
                return all_texts[:total_pages]
            
            # Pad with empty strings if needed
            return all_texts + [""] * (total_pages - len(all_texts))
            
        except Exception:
            pass  # Fall through to pypdf
    
    # Fallback to pypdf (less accurate for OCR'd PDFs)
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            texts = []
            for i in range(min(total_pages, len(reader.pages))):
                try:
                    text = reader.pages[i].extract_text()
                    texts.append(text if text else "")
                except Exception:
                    texts.append("")
            
            # Pad with empty strings if needed
            return texts + [""] * (total_pages - len(texts))
            
    except Exception:
        return [""] * total_pages


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
    
    # Check if it's a pattern
    if looks_like_pattern(expr):
        return parse_pattern_expression(expr, pdf_path, total_pages)
    
    # Try numeric parsing
    try:
        page_num = int(expr)
        if 1 <= page_num <= total_pages:
            return [page_num]
        return []
    except ValueError:
        pass
    
    raise ValueError(f"Could not parse expression: {expr}")


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


def _contains_unquoted_text(text: str, search_text: str) -> bool:
    """Check if text contains search_text outside of quoted strings."""
    if search_text not in text:
        return False
    
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


def _split_on_unquoted_text(text: str, separator: str) -> list[str]:
    """Split text on separator, but only when separator is outside quotes."""
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
    
    ENHANCED: Now uses pdfplumber with tuned adaptive spacing for text extraction,
    which dramatically improves pattern matching accuracy on OCR'd PDFs.
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
    
    # For type: and size: patterns, we still need the pypdf page objects
    if pattern_type in ['type', 'size']:
        try:
            with suppress_pdf_warnings():
                reader = PdfReader(pdf_path)
                for page_num in range(1, min(total_pages + 1, len(reader.pages) + 1)):
                    page = reader.pages[page_num - 1]
                    if _page_matches_structural_pattern(page, pattern_type, value, is_case_insensitive):
                        matching_pages.append(page_num)
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
    
    This function receives pre-extracted text (from pdfplumber's tuned extraction),
    which has proper spacing and line breaks for OCR'd PDFs.
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


def _page_matches_structural_pattern(page, pattern_type: str, value: str, case_insensitive: bool) -> bool:
    """
    Check if a page matches structural patterns (type, size).
    
    These patterns need access to the pypdf page object for structural analysis,
    not just extracted text.
    """
    try:
        if pattern_type == 'type':
            # Simplified type detection - should use PageAnalyzer
            if value.lower() == 'text':
                text = page.extract_text()
                if text:
                    text = text.strip()
                return text and len(text) > 50  # Simple heuristic
            elif value.lower() == 'image':
                # Check for images - simplified
                return '/XObject' in str(page.get('/Resources', {}))
            else:
                return False
        
        elif pattern_type == 'size':
            # Simplified size detection - should be more sophisticated
            return True  # Placeholder
        
        else:
            raise ValueError(f"Unknown structural pattern type: {pattern_type}")
            
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
