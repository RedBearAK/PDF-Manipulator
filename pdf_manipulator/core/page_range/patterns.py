"""
Updated patterns.py with type and size pattern support + comma-separated fixes.
File: pdf_manipulator/core/page_range/patterns.py

FIXED: Prevents comma-separated lists from being misidentified as single patterns.
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
    
    FIXED: Don't treat comma-separated lists as single patterns.
    """
    # FIXED: Don't treat comma-separated lists as single patterns
    # If this looks like a comma-separated list, let comma parsing handle it
    if _looks_like_comma_separated_list_pattern(range_str):
        return False
    
    # Original pattern detection logic
    return any([
        range_str.startswith(('contains', 'regex', 'line-starts', 'type', 'size')),
        ':' in range_str and any(range_str.lower().startswith(p) for p in ['contains', 'regex', 'line-starts', 'type', 'size']),
    ])


def looks_like_range_pattern(range_str: str) -> bool:
    """Check if string looks like a range pattern, respecting quoted strings."""
    return _contains_unquoted_text(range_str, ' to ')


def parse_pattern_expression(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse pattern expression and return matching page numbers."""
    
    # For now, implement simple single patterns only
    # (Complex AND/OR logic can be added in Phase 3)
    
    return _parse_single_pattern_with_offset(expression, pdf_path, total_pages)


def parse_range_pattern(expression: str, pdf_path: Path, total_pages: int) -> list[int]:
    """
    Parse range patterns like 'contains:A to contains:B' and find ALL matching sections.
    
    FIXED: Now finds all A...B pairs, not just first A to last B.
    
    This is the backward-compatible version that just returns pages.
    For grouping information, use parse_range_pattern_with_groups().
    """
    all_pages, _ = parse_range_pattern_with_groups(expression, pdf_path, total_pages)
    return all_pages


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
    
    # Try to parse as number with offset (e.g., "5+1", "10-2")
    offset_match = re.search(r'^(\d+)([+-]\d+)$', expr)
    if offset_match:
        base_num = int(offset_match.group(1))
        offset = int(offset_match.group(2))
        target_page = base_num + offset
        if 1 <= target_page <= total_pages:
            return [target_page]
        else:
            raise ValueError(f"Page {target_page} (from {base_num}{offset:+d}) out of range (1-{total_pages})")
    
    # Must be a pattern - use existing pattern parsing
    return _parse_single_pattern_with_offset(expr, pdf_path, total_pages)


def parse_range_pattern_with_groups(expression: str, pdf_path: Path, 
                                    total_pages: int) -> tuple[list[int], list]:
    """
    Parse range patterns and return both pages and the logical section groups.
    
    Returns:
        Tuple of (all_pages, section_groups) where section_groups is a list of PageGroup objects
    """
    
    # Strip outer parentheses if present
    expression = expression.strip()
    if expression.startswith('(') and expression.endswith(')'):
        # Check if these are the outermost parentheses
        paren_count = 0
        is_outermost = True
        for i, char in enumerate(expression[1:-1], 1):  # Skip first and last char
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count < 0:  # Closing paren before we close the outer one
                    is_outermost = False
                    break
        
        if is_outermost and paren_count == 0:
            expression = expression[1:-1].strip()  # Remove outer parentheses
    
    # Split on ' to ' (case insensitive)
    if ' to ' not in expression.lower():
        raise ValueError("Range pattern must contain ' to '")
    
    # Find the ' to ' separator (case insensitive)
    lower_expr = expression.lower()
    to_pos = lower_expr.find(' to ')
    
    start_expr = expression[:to_pos].strip()
    end_expr = expression[to_pos + 4:].strip()  # +4 for ' to '
    
    if not start_expr:
        raise ValueError("Missing start pattern in range")
    if not end_expr:
        raise ValueError("Missing end pattern in range")
    
    # Parse start and end expressions
    start_pages = parse_single_expression(start_expr, pdf_path, total_pages)
    if not start_pages:
        raise ValueError(f"No pages found for start pattern: {start_expr}")
    
    end_pages = parse_single_expression(end_expr, pdf_path, total_pages)
    if not end_pages:
        raise ValueError(f"No pages found for end pattern: {end_expr}")
    
    # Find all start-to-end sections and create PageGroups
    
    sections = []
    section_groups = []
    used_ends = set()
    
    for start_page in sorted(start_pages):
        # Find next end page after this start (that hasn't been used)
        next_end = None
        for end_page in sorted(end_pages):
            if end_page >= start_page and end_page not in used_ends:
                next_end = end_page
                break
        
        if next_end is not None:
            # Create section from start to end (inclusive)
            section_pages = list(range(start_page, next_end + 1))
            sections.append(section_pages)
            used_ends.add(next_end)
            
            # Create PageGroup for this section
            if len(section_pages) == 1:
                group_spec = f"page{section_pages[0]}"
                section_groups.append(PageGroup(section_pages, False, group_spec))
            else:
                group_spec = f"pages{section_pages[0]}-{section_pages[-1]}"
                section_groups.append(PageGroup(section_pages, True, group_spec))
        else:
            # Start page with no valid end - create single-page section
            sections.append([start_page])
            group_spec = f"page{start_page}"
            section_groups.append(PageGroup([start_page], False, group_spec))
    
    # Flatten all sections into single list of pages
    all_pages = []
    for section in sections:
        all_pages.extend(section)
    
    if not all_pages:
        raise ValueError(f"No valid sections found from {start_expr} to {end_expr}")
    
    return all_pages, section_groups


#################################################################################################
# Private helper functions (used inside module only)

def _looks_like_comma_separated_list_pattern(range_str: str) -> bool:
    """
    Check if string looks like a comma-separated list that starts with a pattern.
    
    This prevents comma-separated lists from being misidentified as single patterns.
    FIXED: Now uses quote-aware comma splitting.
    """
    if ',' not in range_str:
        return False
    
    # FIXED: Split by comma respecting quoted strings
    parts = split_comma_respecting_quotes(range_str)
    
    # Need at least 2 parts to be a list
    if len(parts) < 2:
        return False
    
    # If first part looks like a pattern but we have more parts, it's probably a list
    first_part = parts[0].strip()
    if _is_individual_pattern(first_part):
        # Check if other parts also look like valid individual expressions
        valid_expressions = 0
        for part in parts[1:]:  # Skip first part
            if _is_individual_expression_pattern(part.strip()):
                valid_expressions += 1
        
        # If we have multiple valid expressions, treat as comma-separated
        return valid_expressions >= 1
    
    return False


def _is_individual_pattern(expr: str) -> bool:
    """Check if expression looks like an individual pattern (not comma-separated)."""
    expr = expr.strip()
    
    # Pattern expressions (contains:, type:, etc.) without commas OUTSIDE quotes
    if ':' in expr and not _has_unquoted_commas(expr):
        return any(expr.lower().startswith(p) for p in ['contains', 'type', 'size', 'regex', 'line-starts'])
    
    return False


def _is_individual_expression_pattern(expr: str) -> bool:
    """Check if expression looks like an individual expression for pattern context."""
    expr = expr.strip()
    
    # Numeric specifications
    if expr.isdigit():
        return True
    if '-' in expr and not expr.startswith('-') and not expr.endswith('-'):
        try:
            parts = expr.split('-', 1)
            int(parts[0])
            int(parts[1])
            return True
        except ValueError:
            pass
    
    # Special keywords
    if expr.lower() in ['all']:
        return True
    
    # Pattern expressions (contains:, type:, etc.) - commas inside quotes are OK
    if ':' in expr and any(expr.lower().startswith(p) for p in ['contains', 'type', 'size', 'regex']):
        return True
    
    # Boolean expressions (but without commas OUTSIDE quotes)
    if ('&' in expr or '|' in expr or expr.startswith('!')) and not _has_unquoted_commas(expr):
        return True
    
    # Range expressions (first, last, etc.)
    if any(expr.lower().startswith(w) for w in ['first', 'last']):
        return True
    
    return False


def _has_unquoted_commas(text: str) -> bool:
    """Check if text contains commas outside of quoted strings."""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escape sequences
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        # Handle quote start/end
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif char == ',' and not in_quote:
            # Found comma outside quotes
            return True
        
        i += 1
    
    return False


def _contains_unquoted_text(text: str, search_text: str) -> bool:
    """Check if text contains search_text outside of quoted strings."""
    in_quote = False
    quote_char = None
    search_lower = search_text.lower()
    text_lower = text.lower()
    
    i = 0
    while i <= len(text_lower) - len(search_lower):
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
        elif not in_quote:
            # Check for search text when not in quotes
            if text_lower[i:i+len(search_lower)] == search_lower:
                return True
        
        i += 1
    
    return False


def _parse_single_pattern_with_offset(pattern_str: str, pdf_path: Path, total_pages: int) -> list[int]:
    """Parse single pattern with optional offset and validate syntax."""
    
    # Parse offset: pattern+N, pattern-N
    offset_match = re.search(r'([+-]\d+)$', pattern_str)
    if offset_match:
        offset = int(offset_match.group(1))
        base_pattern = pattern_str[:offset_match.start()]
    else:
        offset = 0
        base_pattern = pattern_str
        
        # If no valid offset found, check for invalid suffixes
        if ':' in base_pattern:  # This is a pattern (has type:value)
            # Find where the quoted value ends
            if '/i:' in base_pattern:
                pattern_type, pattern_value = base_pattern.split('/i:', 1)
            else:
                pattern_type, pattern_value = base_pattern.split(':', 1)
            
            # Check if pattern_value has quotes and what comes after
            if ((pattern_value.startswith('"') and '"' in pattern_value[1:]) or
                (pattern_value.startswith("'") and "'" in pattern_value[1:])):
                
                # Find end of quoted section
                quote_char = pattern_value[0]
                end_quote_pos = pattern_value.find(quote_char, 1)
                if end_quote_pos > 0:
                    after_quote = pattern_value[end_quote_pos + 1:].strip()
                    if after_quote:  # Something after the closing quote
                        if after_quote == 'to':
                            raise ValueError("Incomplete range pattern: missing end expression")
                        elif after_quote.startswith('to'):
                            raise ValueError("Invalid range syntax: use ' to ' with proper spacing")
                        else:
                            raise ValueError(f"Invalid syntax after pattern: '{after_quote}'")
    
    # Get base matches
    base_matches = _parse_base_pattern(base_pattern, pdf_path)
    
    # ADD VALIDATION: Check if there's invalid syntax after the pattern
    _validate_pattern_suffix(pattern_str, base_pattern, offset_match)
    
    # Apply offset
    result_pages = []
    for match_page in base_matches:
        target_page = match_page + offset
        if 1 <= target_page <= total_pages:
            result_pages.append(target_page)
    
    return sorted(list(set(result_pages)))


def _validate_pattern_suffix(full_pattern: str, base_pattern: str, offset_match):
    """Validate that nothing invalid comes after the base pattern."""
    if offset_match:
        return  # Offset was valid
    
    # Check if there's anything after the base pattern
    if len(full_pattern) > len(base_pattern):
        suffix = full_pattern[len(base_pattern):]
        
        # Only valid suffixes are offsets (already handled) or range indicators
        if suffix.startswith(' to '):
            return  # Valid range start
        elif suffix == ' to':
            raise ValueError("Incomplete range pattern: missing end expression")
        elif suffix.startswith('to'):
            raise ValueError("Invalid range syntax: missing space before 'to'")
        else:
            raise ValueError(f"Invalid syntax after pattern: '{suffix}'")


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
    
    if not pattern_value.strip():
        raise ValueError(f"Empty pattern value for {pattern_type}")
    
    # Find matching pages
    return _find_pages_by_pattern(pdf_path, pattern_type, pattern_value, case_sensitive)


def _find_pages_by_pattern(pdf_path: Path, pattern_type: str, pattern_value: str, 
                            case_sensitive: bool) -> list[int]:
    """Find pages matching a specific pattern."""
    
    matching_pages = []
    
    # Handle new pattern types first
    if pattern_type == 'type':
        return _find_pages_by_type(pdf_path, pattern_value)
    elif pattern_type == 'size':
        return _find_pages_by_size(pdf_path, pattern_value)
    
    # Handle existing text-based patterns
    try:
        with suppress_pdf_warnings():
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


def _find_pages_by_type(pdf_path: Path, page_type: str) -> list[int]:
    """Find pages matching a specific content type."""
    
    valid_types = ['text', 'image', 'mixed', 'empty']
    if page_type.lower() not in valid_types:
        raise ValueError(f"Invalid page type '{page_type}'. Valid types: {', '.join(valid_types)}")
    
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_by_type(page_type.lower())
            
        if not matching_pages:
            console.print(f"[dim]No pages found with type '{page_type}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing page types: {e}")


def _find_pages_by_size(pdf_path: Path, size_condition: str) -> list[int]:
    """Find pages matching a size condition."""
    
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            matching_pages = analyzer.get_pages_by_size(size_condition)
            
        if not matching_pages:
            console.print(f"[dim]No pages found matching size condition '{size_condition}'[/dim]")
            
        return matching_pages
        
    except Exception as e:
        raise ValueError(f"Error analyzing page sizes: {e}")


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


# End of file #
