"""
Final enhanced page range parser with smart selector comma support.
File: pdf_manipulator/core/page_range/page_range_parser.py

Complete replacement module with all edge cases fixed:
- Numeric arbitrary reordering with order preservation
- Reverse range support (10-7 → [10, 9, 8, 7])
- File selector support (file:pages.txt)
- Smart selector comma support: "1-5,contains:'Chapter',10-15"
- All pattern validation edge cases handled properly
- Production ready with robust error checking
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.utils import (
    create_pattern_description, create_boolean_description, sanitize_filename)

from pdf_manipulator.core.page_range.patterns import (
    looks_like_pattern,
    looks_like_range_pattern,
    parse_pattern_expression,
)

from pdf_manipulator.core.page_range.boolean import (
    looks_like_boolean_expression,
    parse_boolean_expression
)

from pdf_manipulator.core.page_range.page_group import (
    PageGroup, create_ordered_group, create_range_group, merge_groups_in_order
)

# File selector import - graceful fallback if not yet implemented
try:
    from pdf_manipulator.core.page_range.file_selector import FileSelector
    FILE_SELECTOR_AVAILABLE = True
except ImportError:
    FILE_SELECTOR_AVAILABLE = False

console = Console()


class PageRangeParser:
    """
    Enhanced page range parser with comprehensive comma-separated support.
    
    Features:
    - Numeric arbitrary reordering: "10,5,15,2" → [10, 5, 15, 2]
    - Reverse ranges: "10-7" → [10, 9, 8, 7]
    - File selectors: "file:pages.txt" → loads from file
    - Smart selector comma support: "1-5,contains:'Chapter',type:image,10-15"
    - Boolean expression comma support: "contains:'A' & type:text,5-10"
    - Range pattern comma support: "1-3,contains:'Start' to contains:'End',20"
    - All existing syntax preserved
    - Robust edge case handling
    """
    
    def __init__(self, total_pages: int, pdf_path: Path = None):
        self.total_pages = total_pages
        self.pdf_path = pdf_path
        
        # Initialize file selector if available
        if FILE_SELECTOR_AVAILABLE:
            self.file_selector = FileSelector(base_path=pdf_path.parent if pdf_path else None)
        else:
            self.file_selector = None
            
        self._reset_state()
    
    def _reset_state(self):
        """Reset parser state for fresh parsing (prevents state accumulation)."""
        self.ordered_groups = []  # Maintain order of groups for comma-separated lists
        self.preserve_comma_order = False  # Flag for comma-separated order preservation
    
    def parse(self, range_str: str) -> tuple[set[int], str, list[PageGroup]]:
        """
        Main entry point for parsing page ranges with full feature support.
        
        Args:
            range_str: Page range specification
            
        Returns:
            Tuple of (all_pages_set, description, ordered_groups)
        """
        
        # Reset state for fresh parsing
        self._reset_state()

        # Clean input - remove matching quote pairs only
        if ((range_str.startswith('"') and range_str.endswith('"')) or
            (range_str.startswith("'") and range_str.endswith("'"))):
            range_str = range_str[1:-1]

        # File selector expansion (if available and needed)
        if self.file_selector and 'file:' in range_str:
            try:
                original_range_str = range_str
                range_str = self.file_selector.expand_file_selectors(range_str)
                
                # Show expansion if files were processed
                if range_str != original_range_str:
                    console.print(f"[dim]Expanded file selectors: '{original_range_str}' → '{range_str}'[/dim]")
                    
            except ValueError as e:
                raise ValueError(f"File selector error: {e}")

        # Detect if this should preserve comma-separated order
        self.preserve_comma_order = self._should_preserve_comma_order(range_str)

        # Try advanced patterns first (if PDF available)
        if self.pdf_path:
            result = self._try_advanced_patterns(range_str)
            if result:
                return result
        
        # Handle special keywords
        result = self._try_special_keywords(range_str)
        if result:
            return result
        
        # Parse comma-separated parts (maintaining order if needed)
        self._parse_comma_separated_parts_ordered(range_str)
        
        # Validate and format result
        return self._finalize_result_ordered()
    
    def _should_preserve_comma_order(self, range_str: str) -> bool:
        """
        Determine if this range string should preserve comma-separated order.
        
        ENHANCED: Now supports smart selectors, boolean expressions, and range patterns
        alongside the original numeric specifications.
        
        Enables order preservation for comma-separated specifications including:
        - Numeric specifications: "10,5,15,2" 
        - Smart selectors: "contains:'Chapter',type:image"
        - Boolean expressions: "contains:'A' & type:text,5-10"
        - Range patterns: "contains:'Start' to contains:'End',20"
        - Mixed specifications: "1-5,contains:'Summary',10-15"
        """
        if ',' not in range_str:
            return False
            
        # Check if all parts are valid comma-separated specifications
        parts = [p.strip() for p in range_str.split(',')]
        for part in parts:
            # Skip file selectors (they should be expanded at this point)
            if self.file_selector and self.file_selector.is_file_selector(part):
                continue
                
            if not self._is_valid_comma_specification(part):
                # If any part is invalid, fall back to standard processing
                return False
        
        return True
    
    def _is_valid_comma_specification(self, part: str) -> bool:
        """
        Check if a part is a valid comma-separated specification with robust edge case handling.
        
        ENHANCED: Now supports smart selectors, boolean expressions, and range patterns
        alongside the original numeric specifications.
        
        Supports:
        - Numeric specs: numbers, ranges, slices, first/last patterns
        - Smart selectors: contains:'text', type:image, size:>1MB, regex:'pattern'
        - Boolean expressions: contains:'A' & type:text, type:text | type:image, !type:empty
        - Range patterns: contains:'Start' to contains:'End', 5 to contains:'End'
        - Special keywords: all
        """
        part = part.strip()
        
        # Empty or whitespace-only parts are invalid
        if not part:
            return False
        
        # Numeric specifications (existing logic)
        if self._is_numeric_specification(part):
            return True
        
        # Smart selector patterns with enhanced validation
        if self._is_valid_pattern(part):
            return True
        
        # Boolean expressions with enhanced validation
        if self._is_valid_boolean_expression(part):
            return True
        
        # Range patterns with enhanced validation
        if self._is_valid_range_pattern(part):
            return True
        
        # Special keywords
        if part.lower() in ['all']:
            return True
            
        return False
    
    def _is_valid_pattern(self, part: str) -> bool:
        """Enhanced pattern validation with proper edge case handling."""
        # Must have a colon to be a valid pattern
        if ':' not in part:
            return False
        
        # Check for valid pattern prefixes
        pattern_prefixes = ['contains', 'regex', 'line-starts', 'type', 'size']
        
        for prefix in pattern_prefixes:
            # Handle case-insensitive patterns: "contains/i:"
            if part.lower().startswith(prefix + '/i:'):
                value_part = part[len(prefix) + 3:]  # Skip "prefix/i:"
                return self._is_valid_pattern_value(value_part)
            # Handle regular patterns: "contains:"
            elif part.lower().startswith(prefix + ':'):
                value_part = part[len(prefix) + 1:]  # Skip "prefix:"
                return self._is_valid_pattern_value(value_part)
        
        return False
    
    def _is_valid_pattern_value(self, value: str) -> bool:
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
    
    def _is_valid_boolean_expression(self, part: str) -> bool:
        """Enhanced boolean expression validation."""
        # Must have boolean operators
        operators = [' & ', ' | ', '!']
        has_operator = any(op in part for op in operators)
        
        if not has_operator:
            return False
        
        # Check if operators are inside quotes (should not be boolean then)
        if self._operators_are_quoted(part):
            return False
        
        # FIXED: Must contain valid patterns or keywords when operators are present
        # This fixes 'text with & symbol' being incorrectly accepted
        return self._contains_valid_boolean_components(part)
    
    def _operators_are_quoted(self, text: str) -> bool:
        """Check if boolean operators are inside quoted strings."""
        operators = [' & ', ' | ']
        
        for quote in ['"', "'"]:
            if quote in text:
                parts = text.split(quote)
                for i in range(1, len(parts), 2):  # Check odd indices (inside quotes)
                    if any(op in parts[i] for op in operators):
                        return True
        return False
    
    def _contains_valid_boolean_components(self, text: str) -> bool:
        """Check if a boolean expression contains valid components."""
        # Split by operators but keep a simple check
        # This is a basic validation - the real parsing happens later
        
        # Remove NOT operators for simpler checking
        simplified = text.replace('!', '').strip()
        
        # Split by AND/OR operators  
        parts = []
        for op in [' & ', ' | ']:
            if op in simplified:
                parts.extend([p.strip() for p in simplified.split(op)])
                break
        
        if not parts:
            parts = [simplified.strip()]
        
        # Each part should be a valid pattern, keyword, or parenthesized expression
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Handle parentheses
            if part.startswith('(') and part.endswith(')'):
                part = part[1:-1].strip()
                # Recursively check parenthesized content
                if not self._contains_valid_boolean_components(part):
                    return False
                continue
            
            # FIXED: More strict validation - must be a proper pattern, keyword, or numeric
            is_valid_component = (
                self._is_valid_pattern(part) or 
                part.lower() in ['all'] or 
                self._is_numeric_specification(part)
            )
            
            if not is_valid_component:
                # FIXED: This now properly rejects 'text with & symbol'
                return False
        
        return True
    
    def _looks_like_numeric(self, part: str) -> bool:
        """Quick check if something looks numeric (for boolean validation)."""
        return part.isdigit() or '-' in part or ':' in part or part.lower().startswith(('first', 'last'))
    
    def _is_valid_range_pattern(self, part: str) -> bool:
        """Enhanced range pattern validation."""
        # Must contain ' to '
        if ' to ' not in part:
            return False
        
        # Check if 'to' is inside quotes (should not be range pattern then)
        if self._text_is_quoted(part, ' to '):
            return False
        
        # Split by ' to ' and validate both parts
        parts = part.split(' to ')
        if len(parts) != 2:
            return False
        
        start_part, end_part = [p.strip() for p in parts]
        
        # Both parts must be valid (either patterns or numbers)
        return (self._is_valid_range_component(start_part) and 
                self._is_valid_range_component(end_part))
    
    def _is_valid_range_component(self, part: str) -> bool:
        """Check if a range component is valid (pattern or number)."""
        if not part:
            return False
        
        # Could be a number
        if part.isdigit():
            return True
        
        # Could be a valid pattern (FIXED: now uses proper validation)
        if self._is_valid_pattern(part):
            return True
        
        # Could be a keyword
        if part.lower() in ['all']:
            return True
        
        # FIXED: Could be a numeric specification (like "first 3", "-5", etc.)
        if self._is_numeric_specification(part):
            return True
        
        # FIXED: Reject things like 'page' which are neither numbers nor valid patterns
        # This fixes 'page 5 to page 10' being incorrectly accepted
        return False
    
    def _text_is_quoted(self, text: str, search_text: str) -> bool:
        """Check if search_text appears inside quotes."""
        for quote in ['"', "'"]:
            if quote in text:
                parts = text.split(quote)
                for i in range(1, len(parts), 2):  # Check odd indices (inside quotes)
                    if search_text in parts[i]:
                        return True
        return False
    
    def _is_numeric_specification(self, part: str) -> bool:
        """Check if a part is a numeric specification (number, range, slice, etc.)."""
        part = part.strip()
        
        # Single number
        if part.isdigit():
            return True
            
        # Negative number (for relative indexing)
        if part.startswith('-') and part[1:].isdigit():
            return True
            
        # Range patterns: "5-10", "5:", ":10", "5:10", "5:10:2", etc.
        if re.match(r'^-?\d*[-:].[-:]*\d*$', part) or re.match(r'^-?\d+::-?\d*$', part):
            return True
            
        # First/last patterns: "first 3", "last 2", etc.
        if re.match(r'^(first|last)[-\s]+\d+$', part.lower()):
            return True
            
        # Slicing patterns: "::2", "2::2", etc.
        if re.match(r'^::\d+$', part) or re.match(r'^\d+::\d*$', part):
            return True
            
        return False
    
    def _try_special_keywords(self, range_str: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """Handle special keywords like 'all' and detect invalid input."""
        if range_str.lower() == "all":
            pages = set(range(1, self.total_pages + 1))
            groups = [PageGroup(list(pages), True, "all")]
            return pages, "all", groups
        
        # Detect filename instead of range
        if '.' in range_str and (range_str.endswith('.pdf') or '/' in range_str or '\\' in range_str):
            raise ValueError(f"'{range_str}' looks like a filename, not a page range. Use 'all' to extract all pages.")
        
        return None
    
    def _try_advanced_patterns(self, range_str: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """Try to parse as advanced patterns (boolean, range patterns, etc.)."""
        # IMPORTANT: Check for boolean expressions FIRST before single patterns
        # This prevents complex boolean expressions from being misinterpreted as single patterns
        if looks_like_boolean_expression(range_str):
            try:
                pages, groups = parse_boolean_expression(range_str, self.pdf_path, self.total_pages)
                description = create_boolean_description(range_str)
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Boolean expression error: {e}")
        
        # Check for range patterns second
        if looks_like_range_pattern(range_str):
            try:
                from pdf_manipulator.core.page_range.patterns import parse_range_pattern_with_groups
                pages, groups = parse_range_pattern_with_groups(range_str, self.pdf_path, self.total_pages)
                description = create_pattern_description(range_str)
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Range pattern error: {e}")
        
        # Check for single patterns LAST (to avoid conflicts with boolean expressions)
        # This ensures that complex expressions like "(contains:'A' | contains:'B')" 
        # are handled as boolean expressions, not rejected as invalid single patterns
        if looks_like_pattern(range_str):
            try:
                pages = parse_pattern_expression(range_str, self.pdf_path, self.total_pages)
                description = create_pattern_description(range_str)
                groups = [PageGroup(pages, len(pages) > 1, range_str)]
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Pattern error: {e}")
        
        return None
    
    def _parse_comma_separated_parts_ordered(self, range_str: str):
        """Parse comma-separated parts while preserving order if needed."""
        parts = [p.strip() for p in range_str.split(',')]
        
        for part in parts:
            try:
                # File selectors should already be expanded at this point
                if self.file_selector and self.file_selector.is_file_selector(part):
                    raise ValueError(f"Unexpanded file selector found: '{part}'. This should not happen.")
                
                # Parse each part and add to ordered groups
                group_pages, group_spec = self._parse_single_part_for_group(part)
                if group_pages:
                    # Create group with order preservation if needed
                    group = create_ordered_group(
                        pages=group_pages,
                        original_spec=group_spec,
                        preserve_order=self.preserve_comma_order
                    )
                    self.ordered_groups.append(group)
            except ValueError as e:
                raise ValueError(f"Invalid page range '{part}': {str(e)}")
    
    def _parse_single_part_for_group(self, part: str) -> tuple[list[int], str]:
        """Parse a single range part and return pages in the intended order."""
        part = part.strip()
        
        # Try as special keyword first
        result = self._try_special_keywords(part)
        if result:
            pages_set, _, groups = result
            return sorted(list(pages_set)), part
        
        # Try as advanced pattern BEFORE numeric (if PDF available)
        # This ensures boolean expressions are caught before individual patterns
        if self.pdf_path:
            result = self._try_advanced_patterns(part)
            if result:
                pages_set, _, groups = result
                # Flatten groups to get ordered pages
                if groups:
                    ordered_pages = self._get_ordered_pages_from_groups(groups, pages_set)
                    return ordered_pages, part
                else:
                    return sorted(list(pages_set)), part
        
        # Parse as numeric range (fallback)
        return self._parse_numeric_range_for_group(part)
    
    def _get_ordered_pages_from_groups(self, groups: list[PageGroup], fallback_pages: set[int] = None) -> list[int]:
        """
        Extract pages in the correct order from PageGroup objects.
        
        This is a local implementation since we can't import from operations.py here.
        """
        if not groups:
            return sorted(fallback_pages) if fallback_pages else []
        
        ordered_pages = []
        for group in groups:
            # For ranges, always preserve the order as specified in the pages list
            # For comma-separated preserve_order groups, also preserve order
            # For other groups, sort for backward compatibility
            if (hasattr(group, 'is_range') and group.is_range) or \
               (hasattr(group, 'preserve_order') and getattr(group, 'preserve_order', False)):
                # Preserve the exact order from this group
                ordered_pages.extend(group.pages)
            else:
                # Use sorted order for this group (backward compatibility)
                ordered_pages.extend(sorted(group.pages))
        
        return ordered_pages
    
    def _parse_numeric_range_for_group(self, part: str) -> tuple[list[int], str]:
        """Parse a numeric range part and return pages in order."""
        part = part.strip()
        
        try:
            # Single number
            if part.isdigit():
                page_num = int(part)
                if 1 <= page_num <= self.total_pages:
                    return [page_num], part
                else:
                    raise ValueError(f"Page {page_num} out of range (1-{self.total_pages})")
            
            # Negative indexing
            if part.startswith('-') and part[1:].isdigit():
                offset = int(part[1:])
                page_num = self.total_pages - offset + 1
                if page_num >= 1:
                    return [page_num], part
                else:
                    raise ValueError(f"Negative offset {offset} too large for {self.total_pages} pages")
            
            # Range with dash: "5-10" or "10-5" (reverse)
            if '-' in part and not part.startswith('-'):
                return self._parse_dash_range(part)
            
            # Colon-based ranges and slices
            if ':' in part:
                return self._parse_colon_range(part)
            
            # Double-dot range: "5..10"
            if '..' in part:
                return self._parse_doubledot_range(part)
            
            # First/last patterns
            if part.lower().startswith(('first', 'last')):
                return self._parse_first_last_pattern(part)
            
            # If we get here, it's an unrecognized pattern
            raise ValueError(f"Unrecognized numeric pattern: '{part}'")
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error parsing numeric range '{part}': {e}")
    
    def _parse_dash_range(self, part: str) -> tuple[list[int], str]:
        """Parse dash ranges like '5-10' or '10-5' (reverse)."""
        if part.count('-') != 1:
            raise ValueError(f"Invalid range format: '{part}'")
        
        start_str, end_str = part.split('-')
        
        # Handle open-ended ranges
        if not start_str:  # "-10" (start to 10)
            start = 1
            end = int(end_str)
        elif not end_str:  # "5-" (5 to end)
            start = int(start_str)
            end = self.total_pages
        else:  # "5-10" or "10-5"
            start = int(start_str)
            end = int(end_str)
        
        # Validate range
        if not (1 <= start <= self.total_pages and 1 <= end <= self.total_pages):
            raise ValueError(f"Range {start}-{end} out of bounds (1-{self.total_pages})")
        
        # Generate pages (forward or reverse)
        if start <= end:
            pages = list(range(start, end + 1))
        else:
            pages = list(range(start, end - 1, -1))
        
        return pages, part
    
    def _parse_colon_range(self, part: str) -> tuple[list[int], str]:
        """Parse colon-based ranges and slices."""
        if part.startswith('::'):
            # Slicing pattern: "::2" (every 2nd page)
            step = int(part[2:]) if part[2:] else 1
            pages = list(range(1, self.total_pages + 1, step))
            return pages, part
        
        elif part.endswith('::'):
            # Pattern like "5::" (from page 5, every page)
            start = int(part[:-2])
            pages = list(range(start, self.total_pages + 1))
            return pages, part
        
        elif '::' in part:
            # Pattern like "5::2" or "2::2"
            parts_split = part.split('::')
            start = int(parts_split[0])
            step = int(parts_split[1]) if parts_split[1] else 1
            pages = list(range(start, self.total_pages + 1, step))
            return pages, part
        
        else:
            # Standard colon range: "5:10" or "5:10:2"
            parts_split = part.split(':')
            
            if len(parts_split) == 2:
                start_str, end_str = parts_split
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else self.total_pages
                pages = list(range(start, end + 1))
                return pages, part
            
            elif len(parts_split) == 3:
                start_str, end_str, step_str = parts_split
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else self.total_pages
                step = int(step_str) if step_str else 1
                pages = list(range(start, end + 1, step))
                return pages, part
            
            else:
                raise ValueError(f"Invalid colon range format: '{part}'")
    
    def _parse_doubledot_range(self, part: str) -> tuple[list[int], str]:
        """Parse double-dot ranges like '5..10'."""
        if part.count('..') != 1:
            raise ValueError(f"Invalid double-dot range: '{part}'")
        
        start_str, end_str = part.split('..')
        start = int(start_str)
        end = int(end_str)
        
        if not (1 <= start <= self.total_pages and 1 <= end <= self.total_pages):
            raise ValueError(f"Range {start}..{end} out of bounds (1-{self.total_pages})")
        
        pages = list(range(start, end + 1))
        return pages, part
    
    def _parse_first_last_pattern(self, part: str) -> tuple[list[int], str]:
        """Parse first/last patterns like 'first 3' or 'last-2'."""
        part_lower = part.lower()
        
        if part_lower.startswith('first'):
            # Extract number after 'first'
            num_str = part[5:].strip().lstrip('-').strip()
            num = int(num_str)
            pages = list(range(1, min(num + 1, self.total_pages + 1)))
            return pages, part
        
        elif part_lower.startswith('last'):
            # Extract number after 'last'
            num_str = part[4:].strip().lstrip('-').strip()
            num = int(num_str)
            start = max(1, self.total_pages - num + 1)
            pages = list(range(start, self.total_pages + 1))
            return pages, part
        
        else:
            raise ValueError(f"Invalid first/last pattern: '{part}'")
    
    def _finalize_result_ordered(self) -> tuple[set[int], str, list[PageGroup]]:
        """Finalize results with proper ordering and validation."""
        if not self.ordered_groups:
            raise ValueError("No valid pages found in range specification")
        
        # Collect all pages
        all_pages = set()
        for group in self.ordered_groups:
            all_pages.update(group.pages)
        
        # Create description
        if len(self.ordered_groups) == 1:
            description = self.ordered_groups[0].original_spec
        else:
            specs = [group.original_spec for group in self.ordered_groups]
            description = ','.join(specs)
        
        # Sanitize description for filename use
        description = sanitize_filename(description)
        
        return all_pages, description, self.ordered_groups


# Backward compatibility helper functions
def parse_page_range(range_str: str, total_pages: int, pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Backward compatibility function for existing code.
    
    This maintains the same interface as the original parse_page_range function
    while providing all the enhanced functionality.
    """
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)


def validate_page_range_syntax(range_str: str) -> tuple[bool, str]:
    """
    Validate page range syntax without requiring PDF or total pages.
    
    Args:
        range_str: Range string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use a dummy parser for syntax validation
        parser = PageRangeParser(total_pages=100)  # Dummy total for validation
        parser.parse(range_str)
        return True, "Valid syntax"
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {e}"


def get_page_range_description(range_str: str, total_pages: int = 100) -> str:
    """
    Get a human-readable description of what a page range represents.
    
    Args:
        range_str: Range string to describe
        total_pages: Total pages for context (defaults to 100)
        
    Returns:
        Human-readable description
    """
    try:
        parser = PageRangeParser(total_pages)
        pages_set, description, groups = parser.parse(range_str)
        
        # Create detailed description
        if len(groups) == 1:
            group = groups[0]
            if group.is_range:
                return f"Range: {description} ({len(pages_set)} pages)"
            else:
                return f"Individual pages: {description} ({len(pages_set)} pages)"
        else:
            return f"Multiple groups: {description} ({len(pages_set)} total pages)"
            
    except Exception as e:
        return f"Invalid range: {e}"


# End of file #
