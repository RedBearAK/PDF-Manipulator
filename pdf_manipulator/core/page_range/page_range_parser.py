import re

from pathlib import Path
from rich.console import Console
# from dataclasses import dataclass

from pdf_manipulator.core.page_range.utils import (
    create_pattern_description, create_boolean_description)

from pdf_manipulator.core.page_range.patterns import (
    looks_like_pattern,
    looks_like_range_pattern,
    parse_pattern_expression,
    # parse_range_pattern
)

from pdf_manipulator.core.page_range.boolean import (
    looks_like_boolean_expression,
    parse_boolean_expression
)

from pdf_manipulator.core.page_range.page_group import PageGroup
console = Console()


# @dataclass
# class PageGroup:
#     pages: list[int]
#     is_range: bool
#     original_spec: str


class PageRangeParser:
    """Clean, modular page range parser."""
    
    def __init__(self, total_pages: int, pdf_path: Path = None):
        self.total_pages = total_pages
        self.pdf_path = pdf_path
        self.pages = set()
        self.descriptions = []
        self.groups = []
    
    def parse(self, range_str: str) -> tuple[set[int], str, list[PageGroup]]:
        """Main entry point for parsing page ranges."""

        # console.print(f"[dim]PARSE DEBUG: Input='{range_str}', pdf_path={self.pdf_path is not None}[/dim]")

        # Clean input
        # range_str = range_str.strip().strip('"\'')
        # Fix for incorrectly stripping a single quote symbol by itself
        if ((range_str.startswith('"') and range_str.endswith('"')) or
            (range_str.startswith("'") and range_str.endswith("'"))):
            range_str = range_str[1:-1]  # Only removes MATCHING pairs

        # console.print(f"[dim]PARSE DEBUG: After cleaning='{range_str}'[/dim]")

        # Try advanced patterns first (if PDF available)
        if self.pdf_path:
            result = self._try_advanced_patterns(range_str)
            if result:
                return result
        
        # Handle special keywords
        result = self._try_special_keywords(range_str)
        if result:
            return result
        
        # Parse comma-separated parts
        self._parse_comma_separated_parts(range_str)
        
        # Validate and format result
        return self._finalize_result()
    
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
    

    def _create_consecutive_groups(self, pages: list[int], original_spec: str) -> list[PageGroup]:
        """Convert a list of pages into consecutive run groups."""
        if not pages:
            return []
        
        sorted_pages = sorted(set(pages))  # Remove duplicates and sort
        groups = []
        current_run = [sorted_pages[0]]
        
        for i in range(1, len(sorted_pages)):
            if sorted_pages[i] == sorted_pages[i-1] + 1:
                # Consecutive - extend current run
                current_run.append(sorted_pages[i])
            else:
                # Gap found - finalize current run and start new one
                groups.append(self._create_group_from_run(current_run))
                current_run = [sorted_pages[i]]
        
        # Don't forget the final run
        groups.append(self._create_group_from_run(current_run))
        
        return groups

    def _create_group_from_run(self, run: list[int]) -> PageGroup:
        """Create appropriate PageGroup for a consecutive run."""
        if len(run) == 1:
            # Single page: not a range
            return PageGroup(run, False, str(run[0]))
        else:
            # Consecutive range: is a range
            start, end = run[0], run[-1]
            return PageGroup(run, True, f"{start}-{end}")

    def _parse_comma_separated_parts(self, range_str: str):
        """Parse comma-separated range parts."""
        parts = [p.strip() for p in range_str.split(',')]
        
        for part in parts:
            try:
                self._parse_single_part(part)
            except ValueError as e:
                raise ValueError(f"Invalid page range '{part}': {str(e)}")
    
    def _parse_single_part(self, part: str):
        """Parse a single range part (no commas)."""
        group_pages = []
        
        # Try each parsing strategy in order
        if self._try_parse_slicing(part, group_pages):
            return
        elif self._try_parse_first_last(part, group_pages):
            return
        elif self._try_parse_range(part, group_pages):
            return
        elif self._try_parse_single_page(part, group_pages):
            return
        else:
            raise ValueError(f"Unrecognized format: {part}")
    
    def _try_parse_slicing(self, part: str, group_pages: list) -> bool:
        """Parse slicing syntax: start:stop:step"""
        if not ('::' in part or (part.count(':') == 2)):
            return False
        
        slice_parts = part.split(':')
        start = int(slice_parts[0]) if slice_parts[0] else 1
        stop = int(slice_parts[1]) if slice_parts[1] else self.total_pages
        step = int(slice_parts[2]) if len(slice_parts) > 2 and slice_parts[2] else 1
        
        for p in range(start, stop + 1, step):
            if 1 <= p <= self.total_pages:
                self.pages.add(p)
                group_pages.append(p)
        
        self.groups.append(PageGroup(group_pages, True, part))
        
        # Generate description
        if not slice_parts[0] and not slice_parts[1]:
            if step == 2:
                desc = "odd" if start == 1 else "even"
            else:
                desc = f"every-{step}"
        else:
            desc = f"{start}-{stop}-step{step}"
        
        self.descriptions.append(desc)
        return True
    
    def _try_parse_first_last(self, part: str, group_pages: list) -> bool:
        """Parse 'first N' or 'last N' syntax."""
        if part.lower().startswith('first'):
            match = re.match(r'first[\s-]?(\d+)', part, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                for p in range(1, min(n + 1, self.total_pages + 1)):
                    self.pages.add(p)
                    group_pages.append(p)
                self.groups.append(PageGroup(group_pages, True, part))
                self.descriptions.append(f"first{n}")
                return True
        
        elif part.lower().startswith('last'):
            match = re.match(r'last[\s-]?(\d+)', part, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                for p in range(max(1, self.total_pages - n + 1), self.total_pages + 1):
                    self.pages.add(p)
                    group_pages.append(p)
                self.groups.append(PageGroup(group_pages, True, part))
                self.descriptions.append(f"last{n}")
                return True
        
        return False
    
    def _try_parse_range(self, part: str, group_pages: list) -> bool:
        """Parse range syntax: start-end, start:end, start..end"""
        separators = ['-', ':', '..']
        sep = next((s for s in separators if s in part), None)
        if not sep:
            return False
        
        if sep == '..':
            start_str, end_str = part.split('..')
        else:
            parts_split = part.split(sep, 1)
            start_str = parts_split[0]
            end_str = parts_split[1] if len(parts_split) > 1 else ''
        
        start = int(start_str) if start_str else 1
        end = int(end_str) if end_str else self.total_pages
        
        if start > end:
            raise ValueError(f"Invalid range: {start} > {end}")
        
        for p in range(start, end + 1):
            if 1 <= p <= self.total_pages:
                self.pages.add(p)
                group_pages.append(p)
        
        self.groups.append(PageGroup(group_pages, True, part))
        self.descriptions.append(f"{start}-{end}")
        return True
    
    def _try_parse_single_page(self, part: str, group_pages: list) -> bool:
        """Parse single page number."""
        try:
            page_num = int(part)
            if 1 <= page_num <= self.total_pages:
                self.pages.add(page_num)
                group_pages.append(page_num)
                self.groups.append(PageGroup(group_pages, False, part))
                self.descriptions.append(str(page_num))
                return True
            else:
                raise ValueError(f"Page {page_num} out of range (1-{self.total_pages})")
        except ValueError:
            return False
    
    def _finalize_result(self) -> tuple[set[int], str, list[PageGroup]]:
        """Validate and format final result."""
        if not self.pages:
            raise ValueError("No valid pages in range")
        
        # Create description for filename
        if len(self.descriptions) == 1:
            desc = self.descriptions[0]
        else:
            desc = ",".join(self.descriptions)
            if len(desc) > 20:  # Keep filename reasonable
                desc = f"{min(self.pages)}-{max(self.pages)}-selected"
        
        # Format description
        if ',' in desc:
            desc = f"pages{desc}"
        elif any(d in desc for d in ['odd', 'even', 'every', 'first', 'last']):
            desc = desc  # Keep as is
        elif '-' in desc and not desc.startswith('pages'):
            desc = f"pages{desc}"
        else:
            desc = f"page{desc}"
        
        return self.pages, desc, self.groups
    
    # def _try_advanced_patterns(self, range_str: str) -> tuple[set[int], str, list[PageGroup]] | None:
    #     """Try boolean expressions, range patterns, and single patterns."""
        
    #     # Boolean expressions: "contains:'A' & contains:'B'" or "all & !contains:'DRAFT'"
    #     if looks_like_boolean_expression(range_str):
    #         try:
    #             matching_pages = parse_boolean_expression(range_str, self.pdf_path, self.total_pages)
    #             # Always return boolean results, even if empty (empty is a valid result)
    #             pages = set(matching_pages)
    #             desc = create_boolean_description(range_str)
    #             # groups = [PageGroup(list(pages), True, range_str)]
    #             groups = self._create_consecutive_groups(list(pages), range_str)
    #             return pages, desc, groups
    #         except ValueError as e:
    #             # Boolean pattern was recognized but parsing failed (syntax error, etc.)
    #             raise ValueError(f"Boolean expression error: {e}")
        
    #     # Range patterns: "contains:'A' to contains:'B'"
    #     if looks_like_range_pattern(range_str):
    #         try:
    #             matching_pages = parse_range_pattern(range_str, self.pdf_path, self.total_pages)
    #             # Always return range results, even if empty (empty is a valid result)
    #             pages = set(matching_pages)
    #             desc = f"range-{min(pages)}-{max(pages)}" if pages else "range-empty"
    #             # groups = [PageGroup(list(pages), True, range_str)]
    #             # Redundant because this should be a range (already consecutive group)
    #             groups = self._create_consecutive_groups(list(pages), range_str)
    #             return pages, desc, groups
    #         except ValueError as e:
    #             # Range pattern was recognized but parsing failed (syntax error, etc.)
    #             raise ValueError(f"Range pattern error: {e}")
        
    #     # Single patterns: "contains:'text'", "type:image", "size:>1MB"
    #     if looks_like_pattern(range_str):
    #         try:
    #             matching_pages = parse_pattern_expression(range_str, self.pdf_path, self.total_pages)
    #             # Always return pattern results, even if empty (empty is a valid result)
    #             pages = set(matching_pages)
    #             desc = create_pattern_description(range_str)
    #             # groups = [PageGroup(list(pages), True, range_str)]
    #             groups = self._create_consecutive_groups(list(pages), range_str)
    #             return pages, desc, groups
    #         except ValueError as e:
    #             # Pattern was recognized but parsing failed (syntax error, etc.)
    #             raise ValueError(f"Pattern error: {e}")
        
    #     # No advanced pattern recognized - continue with normal page range parsing
    #     return None

    def _try_advanced_patterns(self, range_str: str) -> tuple[set[int], str, list[PageGroup]] | None:
        """Try boolean expressions, range patterns, and single patterns."""
        
        # Boolean expressions: "contains:'A' & contains:'B'" or "all & !contains:'DRAFT'"
        if looks_like_boolean_expression(range_str):
            try:
                matching_pages = parse_boolean_expression(range_str, self.pdf_path, self.total_pages)
                # Always return boolean results, even if empty (empty is a valid result)
                pages = set(matching_pages)
                desc = create_boolean_description(range_str)
                groups = self._create_consecutive_groups(list(pages), range_str)
                return pages, desc, groups
            except ValueError as e:
                # Boolean pattern was recognized but parsing failed (syntax error, etc.)
                raise ValueError(f"Boolean expression error: {e}")
        
        # Range patterns: "contains:'A' to contains:'B'" - FIXED to find all sections
        if looks_like_range_pattern(range_str):
            try:
                from pdf_manipulator.core.page_range.patterns import parse_range_pattern_with_groups
                matching_pages, section_groups = parse_range_pattern_with_groups(
                                                    range_str, self.pdf_path, self.total_pages)
                # Always return range results, even if empty (empty is a valid result)
                pages = set(matching_pages)
                desc = f"sections-{len(section_groups)}" if section_groups else "sections-empty"
                # Use the section groups directly instead of consecutive grouping
                return pages, desc, section_groups
            except ValueError as e:
                # Range pattern was recognized but parsing failed (syntax error, etc.)
                raise ValueError(f"Range pattern error: {e}")
        
        # Single patterns: "contains:'text'", "type:image", "size:>1MB"
        if looks_like_pattern(range_str):
            try:
                matching_pages = parse_pattern_expression(range_str, self.pdf_path, self.total_pages)
                # Always return pattern results, even if empty (empty is a valid result)
                pages = set(matching_pages)
                desc = create_pattern_description(range_str)
                groups = self._create_consecutive_groups(list(pages), range_str)
                return pages, desc, groups
            except ValueError as e:
                # Pattern was recognized but parsing failed (syntax error, etc.)
                raise ValueError(f"Pattern error: {e}")
        
        # No advanced pattern recognized - continue with normal page range parsing
        return None


def apply_boundary_detection(groups: list[PageGroup], start_pattern: str, end_pattern: str, 
                            pdf_path: Path, total_pages: int) -> list[PageGroup]:
    """
    Split existing groups at boundary points using pattern matching.
    
    Args:
        groups: Existing PageGroup objects to split
        start_pattern: Pattern for starting new groups (e.g., "contains:'Chapter'")
        end_pattern: Pattern for ending current groups (e.g., "contains:'Summary'")
        pdf_path: PDF file path for pattern matching
        total_pages: Total pages in PDF
        
    Returns:
        New list of PageGroup objects split at boundaries
    """
    from pdf_manipulator.core.page_range.patterns import parse_pattern_expression
    
    # Find boundary pages using existing pattern matching
    start_pages = set()
    if start_pattern:
        try:
            start_pages = set(parse_pattern_expression(start_pattern, pdf_path, total_pages))
        except ValueError as e:
            raise ValueError(f"Invalid start boundary pattern: {e}")
    
    end_pages = set()
    if end_pattern:
        try:
            end_pages = set(parse_pattern_expression(end_pattern, pdf_path, total_pages))
        except ValueError as e:
            raise ValueError(f"Invalid end boundary pattern: {e}")
    
    # Split each group at boundary points
    new_groups = []
    for group in groups:
        new_groups.extend(_split_group_at_boundaries(group, start_pages, end_pages))
    
    return new_groups


def _split_group_at_boundaries(group: PageGroup, start_pages: set[int], 
                                end_pages: set[int]) -> list[PageGroup]:
    """
    Split a single group at boundary points.
    
    Args:
        group: PageGroup to split
        start_pages: Pages that start new groups
        end_pages: Pages that end current groups
        
    Returns:
        List of new PageGroup objects
    """
    if not group.pages:
        return [group]
    
    # Sort pages to process sequentially
    sorted_pages = sorted(group.pages)
    groups = []
    current_group_pages = []
    
    for page in sorted_pages:
        # Check if this page ends the current group
        if page in end_pages and current_group_pages:
            # End current group (inclusive - include the end page)
            current_group_pages.append(page)
            groups.append(_create_boundary_group(current_group_pages, group.original_spec))
            current_group_pages = []
            continue
        
        # Check if this page starts a new group
        if page in start_pages:
            # Start new group (finish current group first if it has pages)
            if current_group_pages:
                groups.append(_create_boundary_group(current_group_pages, group.original_spec))
                current_group_pages = []
            # Start new group with this page
            current_group_pages = [page]
        else:
            # Regular page - add to current group
            current_group_pages.append(page)
    
    # Don't forget the final group
    if current_group_pages:
        groups.append(_create_boundary_group(current_group_pages, group.original_spec))
    
    return groups if groups else [group]  # Return original if no splits occurred


def _create_boundary_group(pages: list[int], original_spec: str) -> PageGroup:
    """Create a PageGroup from boundary-split pages."""
    if not pages:
        return PageGroup([], False, original_spec)
    
    if len(pages) == 1:
        return PageGroup(pages, False, f"page{pages[0]}")
    else:
        # Check if consecutive
        sorted_pages = sorted(pages)
        is_consecutive = all(sorted_pages[i] == sorted_pages[i-1] + 1 for i in range(1, len(sorted_pages)))
        
        if is_consecutive:
            spec = f"pages{sorted_pages[0]}-{sorted_pages[-1]}"
            return PageGroup(pages, True, spec)
        else:
            # Non-consecutive - create a grouped spec
            spec = f"pages{','.join(map(str, sorted(pages)))}"
            return PageGroup(pages, True, spec)
