"""
File selector implementation for page range parsing.
File: pdf_manipulator/core/page_range/file_selector.py

Implements "file:" selector syntax for loading page specifications from text files.
Uses central parsing logic from patterns.py instead of duplicating validation.
"""

import re
from pathlib import Path
from rich.console import Console

console = Console()


class FileSelector:
    """Handles loading and parsing page specifications from files."""
    
    def __init__(self, base_path: Path = None):
        """
        Initialize file selector.
        
        Args:
            base_path: Base path for resolving relative file paths (defaults to current directory)
        """
        self.base_path = base_path or Path.cwd()
        self._file_cache = {}  # Cache for loaded files to avoid re-reading
    
    def is_file_selector(self, spec: str) -> bool:
        """Check if a specification is a file selector."""
        return spec.strip().lower().startswith('file:')
    
    def parse_file_selector(self, spec: str) -> list[str]:
        """
        Parse a file selector and return list of page specifications.
        
        Args:
            spec: File selector like "file:pages.txt" or "file:/path/to/pages.txt"
            
        Returns:
            List of page specification strings loaded from file
            
        Raises:
            ValueError: If file doesn't exist, can't be read, or contains invalid content
        """
        # Extract file path from "file:path" format
        if not self.is_file_selector(spec):
            raise ValueError(f"Not a file selector: '{spec}'")
        
        file_path_str = spec[5:].strip()  # Remove "file:" prefix
        if not file_path_str:
            raise ValueError("File selector missing file path: 'file:'")
        
        # Resolve file path
        file_path = self._resolve_file_path(file_path_str)
        
        # Load and parse file contents
        return self._load_page_specs_from_file(file_path)
    
    def _resolve_file_path(self, file_path_str: str) -> Path:
        """Resolve file path relative to base path."""
        file_path = Path(file_path_str)
        
        if file_path.is_absolute():
            return file_path
        else:
            return self.base_path / file_path
    
    def _load_page_specs_from_file(self, file_path: Path) -> list[str]:
        """
        Load page specifications from file.
        
        File format:
        - One page specification per line
        - Empty lines ignored
        - Lines starting with # are comments (ignored)
        - Supports all standard page spec formats: 1-5, 10,20,30, first 3, etc.
        - Supports all pattern formats: contains:, regex:, contains/i:, regex/i:, etc.
        
        Args:
            file_path: Path to file containing page specifications
            
        Returns:
            List of page specification strings
        """
        # Check cache first
        cache_key = str(file_path.resolve())
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]
        
        # Validate file exists and is readable
        if not file_path.exists():
            raise ValueError(f"Page specification file not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            raise ValueError(f"Cannot read page specification file {file_path}: {e}")
        
        # Parse file contents - just extract non-comment lines
        page_specs = []
        for line_num, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # FIXED: Use central validation instead of local patterns
            if self._is_valid_page_spec_using_central_logic(line):
                page_specs.append(line)
            else:
                console.print(f"[yellow]Warning: Invalid page spec on line {line_num} in {file_path}: '{line}'[/yellow]")
        
        if not page_specs:
            raise ValueError(f"No valid page specifications found in file: {file_path}")
        
        # Cache results
        self._file_cache[cache_key] = page_specs
        
        console.print(f"[dim]Loaded {len(page_specs)} page specifications from {file_path.name}[/dim]")
        return page_specs
    
    def _is_valid_page_spec_using_central_logic(self, line: str) -> bool:
        """
        Validate page specification using the central parsing logic.
        
        FIXED: Instead of duplicating pattern recognition, use the functions 
        from patterns.py that already handle all cases correctly.
        
        Args:
            line: Line from file to validate
            
        Returns:
            True if line appears to be a valid page specification
        """
        line = line.strip()
        
        # Try to import central parsing functions
        try:
            from pdf_manipulator.core.page_range.patterns import looks_like_pattern, looks_like_range_pattern
            from pdf_manipulator.core.page_range.boolean import looks_like_boolean_expression
        except ImportError:
            # Fallback to basic validation if imports fail
            return self._basic_validation_fallback(line)
        
        # Check if it's a pattern (this handles contains:, regex:, contains/i:, regex/i:, etc.)
        if looks_like_pattern(line):
            return True
        
        # Check if it's a range pattern (contains:"A" to contains:"B")
        if looks_like_range_pattern(line):
            return True
        
        # Check if it's a boolean expression (patterns with &, |, !)
        if looks_like_boolean_expression(line):
            return True
        
        # Check basic numeric patterns
        if self._is_basic_numeric_spec(line):
            return True
        
        return False
    
    def _is_basic_numeric_spec(self, line: str) -> bool:
        """Check for basic numeric specifications."""
        line = line.strip()
        
        # Single number
        if line.isdigit():
            return True
        
        # Simple range like "5-10"
        if re.match(r'^\d+-\d+$', line):
            return True
        
        # Special keywords
        if line.lower() in ['all', 'odd', 'even']:
            return True
        
        # First/last patterns
        if re.match(r'^(first|last)\s+\d+$', line.lower()):
            return True
        
        # Slicing patterns
        if re.match(r'^::\d+$', line) or re.match(r'^\d+::\d*$', line) or re.match(r'^\d+:\d+:\d+$', line):
            return True
        
        # Complex comma-separated (basic check)
        if re.match(r'^[\d,\-:.\s]+$', line):
            return True
        
        return False
    
    def _basic_validation_fallback(self, line: str) -> bool:
        """
        Basic validation fallback when central parsing functions aren't available.
        
        This is a simplified check that should accept most valid patterns,
        even if we can't validate them perfectly.
        """
        line = line.strip()
        
        # If it contains common pattern keywords, assume it's valid
        pattern_keywords = ['contains:', 'regex:', 'type:', 'size:', 'line-starts:']
        for keyword in pattern_keywords:
            if keyword in line.lower():
                return True
        
        # Check for case-insensitive patterns
        case_insensitive_patterns = ['contains/i:', 'regex/i:', 'line-starts/i:']
        for pattern in case_insensitive_patterns:
            if pattern in line.lower():
                return True
        
        # Boolean expressions
        if any(op in line for op in [' & ', ' | ', '!']):
            return True
        
        # Parentheses indicate boolean grouping
        if '(' in line and ')' in line:
            return True
        
        # Basic numeric specs
        return self._is_basic_numeric_spec(line)
    
    def expand_file_selectors(self, range_str: str) -> str:
        """
        Expand any file selectors in a range string to their contents.
        
        This replaces file:path.txt with the contents of the file,
        joining multiple lines with commas for comma-separated parsing.
        
        Args:
            range_str: Range string that may contain file selectors
            
        Returns:
            Range string with file selectors expanded to their contents
            
        Raises:
            ValueError: If file selector parsing fails
        """
        if 'file:' not in range_str:
            return range_str
        
        # Process all file selectors in the string
        result = range_str
        expanded_files = []  # Track what files were expanded for pretty output
        
        # Find all file: patterns
        file_pattern = re.compile(r'file:([^\s,]+)', re.IGNORECASE)
        
        for match in file_pattern.finditer(range_str):
            file_selector = match.group(0)
            try:
                # Parse the file selector
                page_specs = self.parse_file_selector(file_selector)
                # Join with commas for comma-separated parsing
                replacement = ','.join(page_specs)
                result = result.replace(file_selector, replacement)
                
                # Store for pretty output
                expanded_files.append({
                    'selector': file_selector,
                    'specs': page_specs,
                    'count': len(page_specs)
                })
            except ValueError as e:
                raise ValueError(f"Error expanding {file_selector}: {e}")
        
        # Show expansion with nice formatting
        if expanded_files and range_str != result:
            self._show_file_expansion_summary(expanded_files)
        
        return result
    
    def _show_file_expansion_summary(self, expanded_files: list) -> None:
        """Show a complete summary of file expansions for troubleshooting."""
        console.print(f"[dim]📁 File Selector Expansion:[/dim]")
        
        for file_info in expanded_files:
            selector = file_info['selector']
            count = file_info['count']
            specs = file_info['specs']
            
            # Show file and count
            console.print(f"[dim]  {selector} → {count} patterns:[/dim]")
            
            # Show ALL patterns for troubleshooting - no truncation
            for i, spec in enumerate(specs, 1):
                console.print(f"[dim]    {i:2d}. {spec}[/dim]")
        
        console.print()  # Empty line for spacing


# End of file #
