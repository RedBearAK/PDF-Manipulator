"""
Enhanced page range parser with order preservation and file selector support.
File: pdf_manipulator/core/page_range/page_range_parser.py

Complete replacement module that integrates:
- Numeric arbitrary reordering with order preservation
- Reverse range support (10-7 → [10, 9, 8, 7])
- File selector support (file:pages.txt)
- State management fixes
- All existing functionality preserved
- Smart selector chaining ready architecture
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.utils import (
    create_pattern_description, create_boolean_description)

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
    Enhanced page range parser with order preservation and file selector support.
    
    Features:
    - Numeric arbitrary reordering: "10,5,15,2" → [10, 5, 15, 2]
    - Reverse ranges: "10-7" → [10, 9, 8, 7]
    - File selectors: "file:pages.txt" → loads from file
    - All existing syntax preserved
    - Smart selector chaining ready
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
        
        Enables order preservation for comma-separated numeric specifications.
        Future: Will be expanded to handle smart selector chaining.
        """
        if ',' not in range_str:
            return False
            
        # Check if all parts are numeric (ranges or individual numbers)
        parts = [p.strip() for p in range_str.split(',')]
        for part in parts:
            # Skip file selectors (they're expanded at this point)
            if self.file_selector and self.file_selector.is_file_selector(part):
                continue
                
            if not self._is_numeric_specification(part):
                # For now, only preserve order for pure numeric specs
                # TODO: Expand this when implementing smart selector chaining
                return False
        
        return True
    
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
        
        # Try range patterns first
        if looks_like_range_pattern(range_str):
            try:
                from pdf_manipulator.core.page_range.patterns import parse_range_pattern_with_groups
                pages, description, groups = parse_range_pattern_with_groups(range_str, self.pdf_path, self.total_pages)
                return pages, description, groups
            except ImportError:
                # Fallback if advanced patterns not available
                pass
        
        # Try boolean expressions
        if looks_like_boolean_expression(range_str):
            try:
                pages = parse_boolean_expression(range_str, self.pdf_path, self.total_pages)
                groups = self._create_consecutive_groups(pages, range_str, preserve_order=False)
                description = create_boolean_description(range_str, len(pages))
                return set(pages), description, groups
            except ImportError:
                # Fallback if boolean parsing not available
                pass
        
        # Try single patterns
        if looks_like_pattern(range_str):
            try:
                pages = parse_pattern_expression(range_str, self.pdf_path, self.total_pages)
                groups = self._create_consecutive_groups(pages, range_str, preserve_order=False)
                description = create_pattern_description(range_str, len(pages))
                return set(pages), description, groups
            except ImportError:
                # Fallback if pattern parsing not available
                pass
        
        return None

    def _parse_comma_separated_parts_ordered(self, range_str: str):
        """Parse comma-separated range parts while preserving order."""
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
        
        # Handle various numeric patterns
        if part.isdigit():
            # Single page
            page = int(part)
            if 1 <= page <= self.total_pages:
                return [page], part
            else:
                raise ValueError(f"Page {page} out of range (1-{self.total_pages})")
        
        elif '-' in part and not part.startswith('-') and not part.endswith('-'):
            # Range like "5-10" or "10-5" (reverse) or "20-20" (single)
            try:
                start_str, end_str = part.split('-', 1)
                start = int(start_str)
                end = int(end_str)
                
                if start < 1 or end > self.total_pages:
                    raise ValueError(f"Range out of bounds (1-{self.total_pages})")
                
                # Handle equal start/end (single page)
                if start == end:
                    pages = [start]
                elif start < end:
                    # Forward range: 5-10 → [5, 6, 7, 8, 9, 10]
                    pages = list(range(start, end + 1))
                else:
                    # Reverse range: 10-5 → [10, 9, 8, 7, 6, 5]
                    pages = list(range(start, end - 1, -1))
                
                return pages, part
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid range format: '{part}'")
                raise

        elif part.startswith('-') and part[1:].isdigit():
            # Negative indexing: "-5" means last 5 pages
            count = int(part[1:])
            start_page = max(1, self.total_pages - count + 1)
            pages = list(range(start_page, self.total_pages + 1))
            return pages, f"last{count}"
        
        elif part.endswith('-') and part[:-1].isdigit():
            # Open-ended: "5-" means page 5 to end
            start = int(part[:-1])
            if start < 1:
                raise ValueError(f"Start page {start} must be >= 1")
            pages = list(range(start, self.total_pages + 1))
            return pages, f"{start}-end"
        
        elif part.lower().startswith('first'):
            # "first 3" or "first-3"
            match = re.match(r'first[-\s]+(\d+)', part.lower())
            if match:
                count = int(match.group(1))
                pages = list(range(1, min(count + 1, self.total_pages + 1)))
                return pages, f"first{count}"
        
        elif part.lower().startswith('last'):
            # "last 3" or "last-3"  
            match = re.match(r'last[-\s]+(\d+)', part.lower())
            if match:
                count = int(match.group(1))
                start_page = max(1, self.total_pages - count + 1)
                pages = list(range(start_page, self.total_pages + 1))
                return pages, f"last{count}"
        
        elif ':' in part:
            # Slicing patterns: "5:10", "::2", "2::2", etc.
            return self._parse_slice_pattern(part)
        
        elif '..' in part:
            # Double-dot range syntax: "5..10"
            try:
                start_str, end_str = part.split('..', 1)
                start = int(start_str)
                end = int(end_str)
                
                if start < 1 or end > self.total_pages:
                    raise ValueError(f"Range out of bounds (1-{self.total_pages})")
                
                if start <= end:
                    pages = list(range(start, end + 1))
                else:
                    pages = list(range(start, end - 1, -1))
                
                return pages, part
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"Invalid range format: '{part}'")
                raise
        
        # If nothing matched, it's invalid
        raise ValueError(f"Unrecognized page specification: '{part}'")
    
    def _parse_slice_pattern(self, part: str) -> tuple[list[int], str]:
        """Parse slice patterns like '5:10', '::2', '2::2', etc."""
        
        if part.count(':') == 1:
            # Simple slice: "5:10"
            start_str, end_str = part.split(':', 1)
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else self.total_pages
            
            if start < 1 or end > self.total_pages:
                raise ValueError(f"Slice out of bounds (1-{self.total_pages})")
            
            pages = list(range(start, end + 1))
            return pages, part
            
        elif part.count(':') == 2:
            # Step slice: "5:10:2" or "::2"
            parts_list = part.split(':')
            start_str, end_str, step_str = parts_list
            
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else self.total_pages
            step = int(step_str) if step_str else 1
            
            if start < 1 or end > self.total_pages:
                raise ValueError(f"Slice out of bounds (1-{self.total_pages})")
            
            pages = list(range(start, end + 1, step))
            return pages, part
        
        else:
            raise ValueError(f"Invalid slice pattern: '{part}'")
    
    def _create_consecutive_groups(self, pages: list[int], original_spec: str, preserve_order: bool = False) -> list[PageGroup]:
        """Convert a list of pages into consecutive run groups."""
        if not pages:
            return []
        
        if preserve_order:
            # Preserve input order - don't sort
            working_pages = pages[:]
        else:
            # Standard behavior - sort and deduplicate
            working_pages = sorted(set(pages))
        
        groups = []
        current_run = [working_pages[0]]
        
        for i in range(1, len(working_pages)):
            if working_pages[i] == working_pages[i-1] + 1:
                # Consecutive - extend current run
                current_run.append(working_pages[i])
            else:
                # Gap found - finalize current run and start new one
                groups.append(self._create_group_from_run(current_run, preserve_order))
                current_run = [working_pages[i]]
        
        # Don't forget the final run
        groups.append(self._create_group_from_run(current_run, preserve_order))
        
        return groups

    def _create_group_from_run(self, run: list[int], preserve_order: bool = False) -> PageGroup:
        """Create appropriate PageGroup for a consecutive run."""
        if len(run) == 1:
            # Single page: not a range
            return PageGroup(run, False, str(run[0]), preserve_order)
        else:
            # Consecutive range: is a range
            start, end = run[0], run[-1]
            spec = f"{start}-{end}"
            return PageGroup(run, True, spec, preserve_order)

    def _finalize_result_ordered(self) -> tuple[set[int], str, list[PageGroup]]:
        """Finalize parsing result with proper order preservation."""
        if not self.ordered_groups:
            raise ValueError("No valid pages found")
        
        # Collect all pages (preserving order within each group)
        all_pages = set()
        descriptions = []
        
        for group in self.ordered_groups:
            all_pages.update(group.pages)
            descriptions.append(group.original_spec)
        
        # Create description
        if len(descriptions) == 1:
            description = descriptions[0]
        else:
            # Multiple groups - create combined description
            if self.preserve_comma_order:
                description = f"ordered-{len(self.ordered_groups)}groups"
            else:
                description = f"{len(self.ordered_groups)}groups"
        
        return all_pages, description, self.ordered_groups


# Backward compatibility functions for existing code
def parse_page_range(range_str: str, total_pages: int, pdf_path: Path = None) -> tuple[set[int], str, list[PageGroup]]:
    """
    Backward compatibility function for existing code.
    
    This maintains the same interface as the original parse_page_range function
    while providing all the enhanced functionality.
    """
    parser = PageRangeParser(total_pages, pdf_path)
    return parser.parse(range_str)


# Helper functions for external use
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
