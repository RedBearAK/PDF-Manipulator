"""
File selector implementation for page range parsing.
File: pdf_manipulator/core/page_range/file_selector.py

Implements "file:" selector syntax for loading page specifications from text files.
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
        
        # Parse file contents
        page_specs = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Validate line format
            if self._is_valid_page_spec_line(line):
                page_specs.append(line)
            else:
                console.print(f"[yellow]Warning: Invalid page spec on line {line_num} in {file_path}: '{line}'[/yellow]")
        
        if not page_specs:
            raise ValueError(f"No valid page specifications found in file: {file_path}")
        
        # Cache results
        self._file_cache[cache_key] = page_specs
        
        console.print(f"[dim]Loaded {len(page_specs)} page specifications from {file_path.name}[/dim]")
        return page_specs
    
    def _is_valid_page_spec_line(self, line: str) -> bool:
        """
        Validate that a line contains a valid page specification.
        
        Args:
            line: Line from file to validate
            
        Returns:
            True if line appears to be a valid page specification
        """
        line = line.strip()
        
        # Basic patterns that indicate valid page specs
        valid_patterns = [
            r'^\d+$',                           # Single number: "5"
            r'^\d+[-:]\d*$',                    # Range: "5-10", "5:", "5-"
            r'^-\d+$',                          # Negative: "-5"
            r'^\d*[-:]\d+$',                    # Range: ":10", "-10"
            r'^\d+\.\.\d+$',                    # Double dot: "5..10"
            r'^(first|last)[-\s]+\d+$',         # First/last: "first 3", "last-2"
            r'^all$',                           # Special: "all"
            r'^::\d+$',                         # Slicing: "::2"
            r'^\d+::\d*$',                      # Slicing: "2::2"
            r'^\d+:\d+:\d+$',                   # Slicing: "1:10:2"
            r'^[\d,\-:.\s]+$',                  # Complex comma-separated
            r'^contains:[\'"].*[\'"]',          # Smart patterns
            r'^regex:[\'"].*[\'"]',             # Regex patterns
            r'^type:\w+',                       # Type patterns
            r'^size:[<>=]\d+[KMG]?B?',          # Size patterns
        ]
        
        # Check if line matches any valid pattern
        for pattern in valid_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        
        # Check for more complex boolean expressions
        if any(op in line for op in [' & ', ' | ', '!']):
            return True
        
        # Check for parentheses (boolean grouping)
        if '(' in line and ')' in line:
            return True
        
        return False
    
    def expand_file_selectors(self, range_str: str) -> str:
        """
        Expand any file selectors in a range string to their contents.
        
        Args:
            range_str: Range string that may contain file selectors
            
        Returns:
            Expanded range string with file contents substituted
            
        Example:
            Input: "1-5,file:pages.txt,20-25"
            File contents: ["10-15", "30,35,40"]
            Output: "1-5,10-15,30,35,40,20-25"
        """
        if 'file:' not in range_str:
            return range_str
        
        # Split by commas and process each part
        parts = [part.strip() for part in range_str.split(',')]
        expanded_parts = []
        
        for part in parts:
            if self.is_file_selector(part):
                try:
                    file_specs = self.parse_file_selector(part)
                    expanded_parts.extend(file_specs)
                except ValueError as e:
                    console.print(f"[red]Error processing {part}: {e}[/red]")
                    raise
            else:
                expanded_parts.append(part)
        
        return ','.join(expanded_parts)


# Integration with existing page range parser
def integrate_file_selector_with_parser():
    """
    Integration code to add file selector support to existing PageRangeParser.
    
    This shows how to modify the existing parser to support file selectors.
    """
    
    # Add this to PageRangeParser.__init__:
    def __init__(self, total_pages: int, pdf_path: Path = None):
        self.total_pages = total_pages
        self.pdf_path = pdf_path
        self.file_selector = FileSelector(base_path=pdf_path.parent if pdf_path else None)  # NEW
        self._reset_state()
    
    # Add this to PageRangeParser.parse() at the beginning:
    def parse(self, range_str: str) -> tuple[set[int], str, list]:
        """Enhanced parse method with file selector support."""
        # Reset state for fresh parsing
        self._reset_state()

        # Clean input - remove matching quote pairs only
        if ((range_str.startswith('"') and range_str.endswith('"')) or
            (range_str.startswith("'") and range_str.endswith("'"))):
            range_str = range_str[1:-1]

        # NEW: Expand any file selectors before processing
        try:
            range_str = self.file_selector.expand_file_selectors(range_str)
        except ValueError as e:
            raise ValueError(f"File selector error: {e}")

        # Continue with existing parse logic...
        # (rest of method unchanged)


# Example usage and file formats
EXAMPLE_USAGE = """
# Example file selector usage:

## Command line usage:
pdf-manipulator document.pdf --extract-pages="file:important_pages.txt"
pdf-manipulator document.pdf --extract-pages="1-5,file:chapters.txt,50-45"
pdf-manipulator report.pdf --extract-pages="file:executive_summary.txt,file:appendices.txt"

## File format examples:

### pages.txt (simple numeric ranges):
1-5
10,15,20
30-25
last 3

### chapters.txt (mixed specifications):
# Chapter 1: Introduction
1-10

# Chapter 2: Methodology  
contains:'Methodology' to contains:'Results'

# Chapter 3: Results
type:mixed & size:>1MB

# Appendices
50-40

### complex_selection.txt (advanced patterns):
# Executive summary
contains:'Executive Summary'

# Financial tables
type:mixed & contains:'Table'

# Specific important pages
5,10,15,25

# Reverse document order for review
100-1
"""


# End of file #
