"""
Compact pattern syntax processor for content extraction.
File: pdf_manipulator/renamer/pattern_processor.py

Handles the new compact syntax: [var=]keyword:movements+extraction_type+count[-]
Examples: "Invoice Number:r1wd1", "company=Company Name:u1ln1", "Total:d1r1nb1-"
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor
from pdf_manipulator.scraper.processors.pypdf_processor import PyPDFProcessor
from pdf_manipulator.renamer.sanitizer import auto_generate_variable_name, sanitize_content_for_filename


console = Console()


class CompactPatternError(Exception):
    """Exception for compact pattern parsing errors."""
    pass


class PatternProcessor:
    """
    Process compact pattern syntax and extract content from PDFs.
    
    Compact Syntax: [var=]keyword:movements+extraction_type+count[-]
    
    Movements:
    - u/d + 1-99: up/down lines
    - l/r + 1-99: left/right words
    - Maximum 2 movements, no conflicting directions
    
    Extraction Types:
    - wd + 0-99: words (0 = until end of line)
    - ln + 0-99: lines (0 = until end of document)
    - nb + 0-99: numbers (0 = until non-numeric)
    
    Flexibility:
    - Optional '-' suffix for format-tolerant extraction
    """
    
    # Regex for compact syntax validation (movements are optional)
    COMPACT_PATTERN = re.compile(r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})(-?)$')
    
    def __init__(self):
        self.extractor = PatternExtractor()
        self.processor = PyPDFProcessor(suppress_warnings=True)
        
    def parse_pattern_string(self, pattern_str: str) -> tuple[str, str, dict]:
        """
        Parse full pattern string into variable name, keyword, and extraction spec.
        
        Args:
            pattern_str: Full pattern like "invoice=Invoice Number:r1wd1" or "Company:u1ln1"
            
        Returns:
            Tuple of (variable_name, keyword, extraction_spec)
            
        Raises:
            CompactPatternError: For invalid syntax
        """
        # Check for explicit variable name
        if '=' in pattern_str:
            var_part, pattern_part = pattern_str.split('=', 1)
            variable_name = var_part.strip()
            
            # Validate variable name
            if not variable_name.isidentifier():
                raise CompactPatternError(f"Invalid variable name: '{variable_name}'")
        else:
            pattern_part = pattern_str
            variable_name = None  # Will be auto-generated from keyword
        
        # Split keyword and compact extraction spec
        if ':' not in pattern_part:
            raise CompactPatternError(f"Pattern must contain ':' separator: {pattern_part}")
        
        keyword, compact_spec = pattern_part.rsplit(':', 1)
        keyword = keyword.strip()
        
        if not keyword:
            raise CompactPatternError("Keyword cannot be empty")
        
        # Parse compact extraction specification
        extraction_spec = self.parse_compact_spec(compact_spec)
        
        # Generate variable name if not provided
        if variable_name is None:
            variable_name = auto_generate_variable_name(keyword)
        
        return variable_name, keyword, extraction_spec
    
    def parse_compact_spec(self, spec: str) -> dict:
        """
        Parse compact movement and extraction specification.
        
        Args:
            spec: Compact spec like "r1wd1", "u1r2wd3", "d5ln0-"
            
        Returns:
            Dictionary with parsed movement and extraction details
            
        Raises:
            CompactPatternError: For invalid syntax or constraints
        """
        spec = spec.strip()
        
        # Check for flexibility suffix
        flexible = spec.endswith('-')
        if flexible:
            spec = spec[:-1]
        
        # Match the pattern
        match = self.COMPACT_PATTERN.match(spec)
        if not match:
            raise CompactPatternError(
                f"Invalid compact syntax: '{spec}'. "
                f"Expected format: [movement][movement]extraction_type+count"
            )
        
        # Parse movements
        movements = []
        
        # First movement (optional)
        if match.group(1):
            move1 = match.group(1)
            direction1, distance1 = self._parse_movement(move1)
            movements.append((direction1, distance1))
        
        # Second movement (optional)
        if match.group(2):
            move2 = match.group(2)
            direction2, distance2 = self._parse_movement(move2)
            movements.append((direction2, distance2))
        
        # Parse extraction type and count
        extract_type = match.group(3)
        extract_count = int(match.group(4))
        
        # Validate constraints
        self._validate_constraints(movements, extract_type, extract_count)
        
        return {
            'movements': movements,
            'extract_type': extract_type,
            'extract_count': extract_count,
            'flexible': flexible
        }
    
    def _parse_movement(self, move_str: str) -> tuple[str, int]:
        """Parse single movement like 'u1' or 'r15'."""
        direction = move_str[0]
        distance = int(move_str[1:])
        return direction, distance
    
    def _validate_constraints(self, movements: list, extract_type: str, extract_count: int):
        """Validate pattern constraints and logical consistency."""
        
        # Check movement distances (1-99)
        for direction, distance in movements:
            if distance < 1 or distance > 99:
                raise CompactPatternError(
                    f"Movement distance must be 1-99: {direction}{distance}"
                )
        
        # Check extraction count (0-99)
        if extract_count < 0 or extract_count > 99:
            raise CompactPatternError(
                f"Extraction count must be 0-99: {extract_count}"
            )
        
        # Check for conflicting directions
        directions = [direction for direction, _ in movements]
        if 'u' in directions and 'd' in directions:
            raise CompactPatternError("Conflicting directions: cannot go both up and down")
        if 'l' in directions and 'r' in directions:
            raise CompactPatternError("Conflicting directions: cannot go both left and right")
        
        # Maximum 2 movements
        if len(movements) > 2:
            raise CompactPatternError(f"Too many movements (max 2): {len(movements)}")
        
        # Validate extraction type
        if extract_type not in ['wd', 'ln', 'nb']:
            raise CompactPatternError(f"Invalid extraction type: {extract_type}")
    
    def convert_to_legacy_pattern(self, keyword: str, extraction_spec: dict) -> dict:
        """
        Convert compact specification to legacy PatternExtractor format.
        
        This bridges the new compact syntax with the existing scraper infrastructure.
        """
        movements = extraction_spec['movements']
        extract_type = extraction_spec['extract_type']
        extract_count = extraction_spec['extract_count']
        flexible = extraction_spec['flexible']
        
        # Map extraction types
        type_mapping = {
            'wd': 'word' if extract_count == 1 else 'text',
            'ln': 'line',
            'nb': 'number'
        }
        
        # Map directions
        direction_mapping = {
            'u': 'above',
            'd': 'below', 
            'l': 'left',
            'r': 'right'
        }
        
        # For now, use single movement (we'll enhance PatternExtractor later for chaining)
        if len(movements) == 0:
            # No movement - extract right at keyword location
            return {
                'keyword': keyword,
                'direction': 'right',  # Use 'right' with distance 0 as default
                'distance': 0,
                'extract_type': legacy_type,
                'extract_count': extract_count,
                'flexible': flexible
            }
        elif len(movements) == 1:
            direction, distance = movements[0]
            legacy_direction = direction_mapping[direction]
            legacy_type = type_mapping[extract_type]
            
            return {
                'keyword': keyword,
                'direction': legacy_direction,
                'distance': distance,
                'extract_type': legacy_type,
                'extract_count': extract_count,
                'flexible': flexible
            }
        else:
            # Complex movement - we'll need to enhance this later
            # For now, use the last movement
            direction, distance = movements[-1]
            legacy_direction = direction_mapping[direction]
            legacy_type = type_mapping[extract_type]
            
            console.print(f"[yellow]Warning: Complex movement not fully supported yet, using final movement only[/yellow]")
            
            return {
                'keyword': keyword,
                'direction': legacy_direction,
                'distance': distance,
                'extract_type': legacy_type,
                'extract_count': extract_count,
                'flexible': flexible
            }
    
    def extract_content_from_pdf(self, pdf_path: Path, patterns: list[tuple[str, str, dict]], 
                                source_page: int = 1) -> dict[str, str]:
        """
        Extract content from PDF using multiple patterns.
        
        Args:
            pdf_path: Path to PDF file
            patterns: List of (variable_name, keyword, extraction_spec) tuples
            source_page: Page number to extract from (1-indexed)
            
        Returns:
            Dictionary mapping variable names to extracted content
        """
        results = {}
        
        try:
            # Extract text from specified page
            page_text = self.processor.extract_page(pdf_path, source_page)
            
            for variable_name, keyword, extraction_spec in patterns:
                try:
                    # Convert to legacy format for now
                    legacy_pattern = self.convert_to_legacy_pattern(keyword, extraction_spec)
                    
                    # Extract content using existing PatternExtractor
                    raw_content = self.extractor.extract_pattern(page_text, legacy_pattern)
                    
                    if raw_content is not None:
                        # Sanitize for filename use
                        clean_content = sanitize_content_for_filename(
                            raw_content, 
                            self._infer_content_type(extraction_spec['extract_type'])
                        )
                        results[variable_name] = clean_content
                    else:
                        results[variable_name] = None
                        
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to extract '{variable_name}': {e}[/yellow]")
                    results[variable_name] = None
            
        except Exception as e:
            console.print(f"[red]Error extracting from {pdf_path}: {e}[/red]")
            # Return empty results for all variables
            for variable_name, _, _ in patterns:
                results[variable_name] = None
        
        return results
    
    def _infer_content_type(self, extract_type: str) -> str:
        """Infer content type for sanitization."""
        type_mapping = {
            'wd': 'text',
            'ln': 'text', 
            'nb': 'number'
        }
        return type_mapping.get(extract_type, 'text')
    
    def validate_pattern_list(self, pattern_strings: list[str]) -> list[tuple[str, str, dict]]:
        """
        Validate and parse a list of pattern strings.
        
        Args:
            pattern_strings: List of pattern strings to validate
            
        Returns:
            List of validated (variable_name, keyword, extraction_spec) tuples
            
        Raises:
            CompactPatternError: If any pattern is invalid
        """
        parsed_patterns = []
        variable_names = set()
        
        for i, pattern_str in enumerate(pattern_strings):
            try:
                variable_name, keyword, extraction_spec = self.parse_pattern_string(pattern_str)
                
                # Check for duplicate variable names
                if variable_name in variable_names:
                    raise CompactPatternError(
                        f"Duplicate variable name '{variable_name}' in pattern {i+1}"
                    )
                
                variable_names.add(variable_name)
                parsed_patterns.append((variable_name, keyword, extraction_spec))
                
            except CompactPatternError as e:
                raise CompactPatternError(f"Pattern {i+1} error: {e}")
        
        return parsed_patterns


# End of file #
