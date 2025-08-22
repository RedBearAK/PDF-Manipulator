"""
Enhanced Page Range Parser with Fixed Architecture
File: pdf_manipulator/core/page_range/page_range_parser.py

ARCHITECTURE FIX: Comma parsing happens FIRST, before any type detection.
This eliminates circular dependencies and quote handling conflicts.

Features:
- Numeric arbitrary reordering: "10,5,15,2" → [10, 5, 15, 2]
- Reverse ranges: "10-7" → [10, 9, 8, 7]  
- File selectors: "file:pages.txt" → loads from file
- Smart selector comma support: "1-5,contains:'Chapter',type:image,10-15"
- Boolean expression comma support: "contains:'A' & type:text,5-10"
- Range pattern comma support: "1-3,contains:'Start' to contains:'End',20"
- All existing syntax preserved
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.utils import (
    create_pattern_description, create_boolean_description, sanitize_filename)

from pdf_manipulator.core.page_range.patterns import (
    parse_pattern_expression,
    split_comma_respecting_quotes
)

from pdf_manipulator.core.page_range.boolean import (
    evaluate_boolean_expression_with_groups
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
    Enhanced page range parser with fixed architecture.
    
    ARCHITECTURE FIX: Comma parsing happens FIRST, before any type detection.
    This eliminates circular dependencies and quote handling conflicts.
    
    Key principle: Comma parsing → Type detection → Processing
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
        """Reset parser state for fresh parsing."""
        self.ordered_groups = []
        self.preserve_comma_order = False
    
    def parse(self, range_str: str) -> tuple[set[int], str, list[PageGroup]]:
        """
        Main entry point with fixed architecture.
        
        ARCHITECTURE FIX: Comma parsing happens FIRST, before any type detection.
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

        # ARCHITECTURE FIX: Check for comma-separated FIRST
        if ',' in range_str:
            return self._parse_comma_separated_arguments(range_str)
        else:
            return self._parse_single_argument(range_str)
    
    def _parse_comma_separated_arguments(self, range_str: str) -> tuple[set[int], str, list[PageGroup]]:
        """
        Parse comma-separated arguments.
        
        FIXED: This happens at the TOP LEVEL, before any type detection.
        """
        # Split on commas respecting quotes
        arguments = split_comma_respecting_quotes(range_str)
        
        # Determine if we should preserve order
        self.preserve_comma_order = self._should_preserve_order(arguments)
        
        all_pages = set()
        descriptions = []
        
        # Process each argument independently
        for arg in arguments:
            arg = arg.strip()
            if not arg:
                continue
                
            try:
                pages, desc, groups = self._parse_single_argument(arg)
                
                # Mark groups with comma order preservation if needed
                if self.preserve_comma_order:
                    for group in groups:
                        group.preserve_order = True
                
                all_pages.update(pages)
                descriptions.append(desc)
                self.ordered_groups.extend(groups)
                
            except Exception as e:
                raise ValueError(f"Error parsing argument '{arg}': {e}")
        
        # Create combined description
        if len(descriptions) == 1:
            combined_desc = descriptions[0]
        else:
            combined_desc = "Comma-separated: " + ", ".join(descriptions)
        
        return all_pages, combined_desc, self.ordered_groups
    
    def _parse_single_argument(self, arg: str) -> tuple[set[int], str, list[PageGroup]]:
        """
        Parse a single argument (no commas).
        
        This is where type detection happens - AFTER comma splitting.
        """
        # Handle special keywords first
        result = self._try_special_keywords(arg)
        if result:
            return result
        
        # Try advanced patterns (only if PDF available)
        if self.pdf_path:
            result = self._try_advanced_patterns(arg)
            if result:
                return result
        
        # Try simple numeric ranges
        result = self._try_numeric_range(arg)
        if result:
            return result
        
        # If nothing else works, raise error
        raise ValueError(f"Could not parse argument: '{arg}'")
    
    def _should_preserve_order(self, arguments: list[str]) -> bool:
        """
        Determine if comma-separated arguments should preserve order.
        
        FIXED: Now operates on already-split arguments, no circular dependencies.
        """
        # If any argument is non-numeric, preserve order for mixed smart selectors
        for arg in arguments:
            arg = arg.strip()
            if not self._is_simple_numeric_spec(arg):
                return True
        
        # All numeric - check if any are out of order (for arbitrary reordering)
        return self._has_arbitrary_numeric_order(arguments)
    
    def _is_simple_numeric_spec(self, arg: str) -> bool:
        """Check if argument is a simple numeric specification."""
        arg = arg.strip()
        
        # Single number
        if arg.isdigit():
            return True
        
        # Simple range like "5-10"
        if re.match(r'^\d+-\d+$', arg):
            return True
        
        # Special keywords that don't need order preservation
        if arg.lower() in ['all', 'odd', 'even']:
            return True
        
        # First/last patterns
        if re.match(r'^(first|last)\s+\d+$', arg.lower()):
            return True
        
        return False
    
    def _has_arbitrary_numeric_order(self, arguments: list[str]) -> bool:
        """Check if numeric arguments are in arbitrary (non-ascending) order."""
        numeric_values = []
        
        for arg in arguments:
            arg = arg.strip()
            if arg.isdigit():
                numeric_values.append(int(arg))
            elif re.match(r'^\d+-\d+$', arg):
                # For ranges, use the start value
                start = int(arg.split('-')[0])
                numeric_values.append(start)
        
        # If we have numeric values, check if they're not in ascending order
        return len(numeric_values) >= 2 and numeric_values != sorted(numeric_values)
    
    def _try_special_keywords(self, arg: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """Try to parse special keywords like 'all'."""
        arg_lower = arg.lower().strip()
        
        if arg_lower == 'all':
            pages = list(range(1, self.total_pages + 1))
            group = PageGroup(pages, True, arg)
            return set(pages), "All pages", [group]
        
        if arg_lower == 'odd':
            pages = list(range(1, self.total_pages + 1, 2))
            group = PageGroup(pages, False, arg)
            return set(pages), "Odd pages", [group]
        
        if arg_lower == 'even':
            pages = list(range(2, self.total_pages + 1, 2))
            group = PageGroup(pages, False, arg)
            return set(pages), "Even pages", [group]
        
        return None
    
    def _try_advanced_patterns(self, arg: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """
        Try to parse advanced patterns.
        
        FIXED: No comma detection here - that already happened at top level.
        """
        # Check for boolean expressions FIRST
        if self._looks_like_boolean_expression_no_comma_check(arg):
            try:
                pages, groups = evaluate_boolean_expression_with_groups(arg, self.pdf_path, self.total_pages)
                description = create_boolean_description(arg)
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Boolean expression error: {e}")
        
        # Check for range patterns
        if self._looks_like_range_pattern_no_comma_check(arg):
            try:
                from pdf_manipulator.core.page_range.patterns import parse_range_pattern_with_groups
                pages, groups = parse_range_pattern_with_groups(arg, self.pdf_path, self.total_pages)
                description = create_pattern_description(arg)
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Range pattern error: {e}")
        
        # Check for single patterns
        if self._looks_like_pattern_no_comma_check(arg):
            try:
                pages = parse_pattern_expression(arg, self.pdf_path, self.total_pages)
                description = create_pattern_description(arg)
                groups = [PageGroup(pages, len(pages) > 1, arg)]
                return set(pages), description, groups
            except Exception as e:
                raise ValueError(f"Pattern error: {e}")
        
        return None
    
    def _try_numeric_range(self, arg: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """Try to parse as numeric range."""
        arg = arg.strip()
        
        # Single number
        if arg.isdigit():
            page_num = int(arg)
            if 1 <= page_num <= self.total_pages:
                group = PageGroup([page_num], False, arg)
                return {page_num}, f"Page {page_num}", [group]
            else:
                raise ValueError(f"Page number {page_num} out of range (1-{self.total_pages})")
        
        # Range like "5-10" or "10-5" (reverse)
        if re.match(r'^\d+-\d+$', arg):
            try:
                start_str, end_str = arg.split('-')
                start, end = int(start_str), int(end_str)
                
                # Validate range
                if not (1 <= start <= self.total_pages and 1 <= end <= self.total_pages):
                    raise ValueError(f"Page numbers out of range: {arg}")
                
                # Create range (forward or reverse)
                if start <= end:
                    pages = list(range(start, end + 1))
                    desc = f"Pages {start}-{end}"
                else:
                    pages = list(range(start, end - 1, -1))
                    desc = f"Pages {start}-{end} (reverse)"
                
                group = PageGroup(pages, True, arg)
                return set(pages), desc, [group]
                
            except ValueError as e:
                if "out of range" in str(e):
                    raise e
                pass
        
        # First/last patterns
        first_match = re.match(r'^first\s+(\d+)$', arg.lower())
        if first_match:
            count = min(int(first_match.group(1)), self.total_pages)
            pages = list(range(1, count + 1))
            group = PageGroup(pages, True, arg)
            return set(pages), f"First {count} pages", [group]
        
        last_match = re.match(r'^last\s+(\d+)$', arg.lower())
        if last_match:
            count = min(int(last_match.group(1)), self.total_pages)
            start = max(1, self.total_pages - count + 1)
            pages = list(range(start, self.total_pages + 1))
            group = PageGroup(pages, True, arg)
            return set(pages), f"Last {count} pages", [group]
        
        # Slicing patterns like "::2" (every 2nd page)
        if re.match(r'^::\d+$', arg):
            step = int(arg[2:])
            pages = list(range(1, self.total_pages + 1, step))
            group = PageGroup(pages, False, arg)
            return set(pages), f"Every {step} pages", [group]
        
        return None
    
    def _looks_like_boolean_expression_no_comma_check(self, arg: str) -> bool:
        """
        Check if argument looks like boolean expression.
        
        FIXED: No comma checking - that already happened at top level.
        """
        # Check for boolean operators outside quotes
        operators = [' & ', ' | ', '!']
        has_operators = any(op in arg for op in operators)
        
        if not has_operators:
            # Check for parentheses (also indicates boolean)
            return self._has_unquoted_parentheses(arg)
        
        # Has operators - now validate that operators are not all inside quotes
        return not self._all_operators_are_quoted(arg)
    
    def _looks_like_pattern_no_comma_check(self, arg: str) -> bool:
        """
        Check if argument looks like pattern expression.
        
        FIXED: No comma checking - that already happened at top level.
        """
        # Simple pattern detection - no comma checking needed
        return any([
            arg.startswith(('contains:', 'regex:', 'line-starts:', 'type:', 'size:')),
            ':' in arg and any(arg.lower().startswith(p + ':') for p in ['contains', 'regex', 'line-starts', 'type', 'size']),
        ])
    
    def _looks_like_range_pattern_no_comma_check(self, arg: str) -> bool:
        """
        Check if argument looks like range pattern.
        
        FIXED: No comma checking - that already happened at top level.
        """
        return self._contains_unquoted_text(arg, ' to ')
    
    def _has_unquoted_parentheses(self, text: str) -> bool:
        """Check if text contains parentheses outside quoted strings."""
        in_quotes = False
        quote_char = None
        
        for char in text:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char in ['(', ')'] and not in_quotes:
                return True
        
        return False
    
    def _all_operators_are_quoted(self, text: str) -> bool:
        """Check if all boolean operators are inside quoted strings."""
        operators = [' & ', ' | ', '!']
        
        for op in operators:
            if op in text and not self._is_text_fully_quoted(text, op):
                return False
        
        return True
    
    def _is_text_fully_quoted(self, text: str, search_text: str) -> bool:
        """Check if search_text appears only inside quotes."""
        if search_text not in text:
            return True
        
        # Find all occurrences of search_text
        start = 0
        while True:
            pos = text.find(search_text, start)
            if pos == -1:
                break
            
            # Check if this occurrence is inside quotes
            if not self._is_position_quoted(text, pos):
                return False
            
            start = pos + len(search_text)
        
        return True
    
    def _is_position_quoted(self, text: str, pos: int) -> bool:
        """Check if position is inside quoted string."""
        in_quotes = False
        quote_char = None
        
        for i, char in enumerate(text):
            if i == pos:
                return in_quotes
            
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
        
        return False
    
    def _contains_unquoted_text(self, text: str, search_text: str) -> bool:
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
            if not self._is_position_quoted(text, pos):
                return True
            
            start = pos + len(search_text)
        
        return False


# Backward compatibility functions that other modules may depend on
def parse_page_range(range_str: str, total_pages: int, pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Parse page range string and return pages, description, and groups.
    
    This is the main public API function that other modules use.
    """
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)


def get_ordered_pages_from_groups(groups: list[PageGroup], fallback_pages: set[int] = None) -> list[int]:
    """
    Extract ordered pages from page groups, respecting order preservation flags.
    
    This function is used by other modules to get the final page order.
    """
    if not groups:
        return sorted(list(fallback_pages)) if fallback_pages else []
    
    ordered_pages = []
    for group in groups:
        # For ranges or preserve_order groups, maintain exact order
        # For other groups, sort for backward compatibility
        if (hasattr(group, 'is_range') and getattr(group, 'is_range', False)) or \
           (hasattr(group, 'preserve_order') and getattr(group, 'preserve_order', False)):
            # Preserve the exact order from this group
            ordered_pages.extend(group.pages)
        else:
            # Use sorted order for this group (backward compatibility)
            ordered_pages.extend(sorted(group.pages))
    
    return ordered_pages


# End of file #
