"""
Corrected Page Range Parser with Proper Separation of Concerns
File: pdf_manipulator/core/page_range/page_range_parser_corrected.py

FIXED: Comma parsing happens FIRST, before any type detection.

Architecture:
1. TOP LEVEL: Split on commas (respecting quotes)
2. MIDDLE LEVEL: For each argument, detect type 
3. BOTTOM LEVEL: Process each argument by type

This prevents the circular dependencies and quote handling issues.
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


class CorrectedPageRangeParser:
    """
    Page range parser with proper separation of concerns.
    
    Key principle: Comma parsing happens FIRST, before any type detection.
    
    Architecture:
    1. Split input on commas (respecting quotes) → individual arguments
    2. For each argument, detect its type (boolean, pattern, simple range)
    3. Process each argument according to its type
    4. Combine results preserving order when appropriate
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
        Main entry point with corrected architecture.
        
        FIXED: Comma parsing happens FIRST, before any type detection.
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
        
        # Add other special keywords as needed
        
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
                
            except ValueError:
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
        
        # Has operators - validate that operators are not all inside quotes
        return not self._all_operators_are_quoted(arg)
    
    def _looks_like_range_pattern_no_comma_check(self, arg: str) -> bool:
        """
        Check if argument looks like range pattern.
        
        FIXED: No comma checking - that already happened at top level.
        """
        return self._contains_unquoted_text(arg, ' to ')
    
    def _looks_like_pattern_no_comma_check(self, arg: str) -> bool:
        """
        Check if argument looks like pattern expression.
        
        FIXED: No comma checking - that already happened at top level.
        """
        return any([
            arg.startswith(('contains', 'regex', 'line-starts', 'type', 'size')),
            ':' in arg and any(arg.lower().startswith(p) for p in ['contains', 'regex', 'line-starts', 'type', 'size']),
        ])
    
    def _has_unquoted_parentheses(self, text: str) -> bool:
        """Check if text contains parentheses outside quoted strings."""
        in_quote = False
        quote_char = None
        i = 0
        
        while i < len(text):
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
            elif char in ['(', ')'] and not in_quote:
                return True
            
            i += 1
        
        return False
    
    def _all_operators_are_quoted(self, text: str) -> bool:
        """Check if ALL boolean operators are inside quoted strings."""
        operators = [' & ', ' | ', '!']
        
        for operator in operators:
            if operator not in text:
                continue
            if self._operator_outside_quotes(text, operator):
                return False
        
        return True
    
    def _operator_outside_quotes(self, text: str, operator: str) -> bool:
        """Check if operator appears outside quoted strings."""
        in_quote = False
        quote_char = None
        i = 0
        
        while i <= len(text) - len(operator):
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
                if text[i:i+len(operator)] == operator:
                    return True
            
            i += 1
        
        return False
    
    def _contains_unquoted_text(self, text: str, search_text: str) -> bool:
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


# End of file #
