"""
Updated compact pattern syntax processor for enhanced content extraction.
File: pdf_manipulator/renamer/pattern_processor.py

PHASE 2 UPDATES:
- Now uses enhanced PatternExtractor with chained movements
- Full support for zero-count extraction (wd0, ln0, nb0)
- Flexible extraction mode with '-' suffix
- No more legacy bridge - direct enhanced format usage
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
    
    PHASE 2 ENHANCEMENTS:
    - Direct use of enhanced PatternExtractor (no legacy bridge needed)
    - Full chained movement support: [('u', 1), ('r', 2)]
    - Zero-count extraction: wd0, ln0, nb0 with "until end" semantics
    - Flexible extraction mode for format tolerance
    
    Compact Syntax: [var=]keyword:movements+extraction_type+count[-]
    
    Movements:
    - u/d + 1-99: up/down lines
    - l/r + 1-99: left/right words
    - Maximum 2 movements, no conflicting directions
    - Zero movements supported (extract at keyword location)
    
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
        self.extractor = PatternExtractor()  # Now uses enhanced version
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
    
    def convert_to_enhanced_pattern(self, keyword: str, extraction_spec: dict) -> dict:
        """
        Convert compact specification to enhanced PatternExtractor format.
        
        PHASE 2: Now creates enhanced format directly (no legacy bridge).
        
        Args:
            keyword: The keyword to search for
            extraction_spec: Parsed compact specification
            
        Returns:
            Enhanced pattern dictionary for PatternExtractor
        """
        movements = extraction_spec['movements']
        extract_type = extraction_spec['extract_type']
        extract_count = extraction_spec['extract_count']
        flexible = extraction_spec['flexible']
        
        return {
            'keyword': keyword,
            'movements': movements,
            'extract_type': extract_type,
            'extract_count': extract_count,
            'flexible': flexible
        }
    
    def extract_content_from_pdf(self, pdf_path: Path, patterns: list[tuple[str, str, dict]], 
                                source_page: int = 1) -> dict[str, str]:
        """
        Extract content from PDF using multiple patterns.
        
        PHASE 2: Uses enhanced PatternExtractor directly.
        
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
                    # Convert to enhanced format
                    enhanced_pattern = self.convert_to_enhanced_pattern(keyword, extraction_spec)
                    
                    # Extract content using enhanced PatternExtractor
                    raw_content = self.extractor.extract_pattern(page_text, enhanced_pattern)
                    
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
    
    def debug_pattern_extraction(self, pdf_path: Path, pattern_string: str, source_page: int = 1) -> dict:
        """
        Debug a single pattern extraction with detailed output.
        
        PHASE 2: New debugging method using enhanced extraction.
        
        Args:
            pdf_path: Path to PDF file
            pattern_string: Single pattern string to debug
            source_page: Page to extract from
            
        Returns:
            Detailed debugging information
        """
        debug_info = {
            'pattern_string': pattern_string,
            'parsing_success': False,
            'extraction_success': False,
            'parsing_error': None,
            'extraction_error': None,
            'variable_name': None,
            'keyword': None,
            'extraction_spec': None,
            'enhanced_pattern': None,
            'page_text_preview': None,
            'extractor_debug': None,
            'final_result': None
        }
        
        try:
            # Parse pattern
            variable_name, keyword, extraction_spec = self.parse_pattern_string(pattern_string)
            debug_info.update({
                'parsing_success': True,
                'variable_name': variable_name,
                'keyword': keyword,
                'extraction_spec': extraction_spec
            })
            
            # Convert to enhanced pattern
            enhanced_pattern = self.convert_to_enhanced_pattern(keyword, extraction_spec)
            debug_info['enhanced_pattern'] = enhanced_pattern
            
            # Extract page text
            page_text = self.processor.extract_page(pdf_path, source_page)
            debug_info['page_text_preview'] = page_text[:500] + "..." if len(page_text) > 500 else page_text
            
            # Debug extraction process
            extractor_debug = self.extractor.debug_extraction(page_text, enhanced_pattern)
            debug_info['extractor_debug'] = extractor_debug
            
            if extractor_debug['success']:
                raw_result = extractor_debug['extracted']
                clean_result = sanitize_content_for_filename(
                    raw_result,
                    self._infer_content_type(extraction_spec['extract_type'])
                ) if raw_result else None
                
                debug_info.update({
                    'extraction_success': True,
                    'raw_result': raw_result,
                    'final_result': clean_result
                })
            else:
                debug_info['extraction_error'] = extractor_debug['error']
            
        except Exception as e:
            debug_info['parsing_error'] = str(e)
        
        return debug_info
    
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
    
    def get_pattern_examples(self) -> dict[str, dict]:
        """
        Get examples of valid patterns for documentation and testing.
        
        Returns:
            Dictionary of pattern examples with descriptions
        """
        return {
            'basic_patterns': {
                'Invoice Number:r1wd1': 'Get 1 word to the right of "Invoice Number"',
                'Total:d1nb1': 'Get 1 number 1 line down from "Total"',
                'Company:u1ln1': 'Get 1 line above "Company"',
                'Description:wd0': 'Get all words from "Description" to end of line'
            },
            'chained_movements': {
                'Invoice:u1r2wd1': 'Go up 1 line, then right 2 words, get 1 word',
                'Total:d2r1nb1': 'Go down 2 lines, then right 1 word, get 1 number',
                'Header:u1l1ln1': 'Go up 1 line, then left 1 word, get 1 line'
            },
            'zero_count_extraction': {
                'Amount:nb0': 'Get all consecutive numbers from "Amount"',
                'Description:d1wd0': 'Go down 1 line, get all words to end',
                'Details:u1ln0': 'Go up 1 line, get all lines to end of document'
            },
            'flexible_extraction': {
                'Amount:r1nb1-': 'Get 1 number to the right (format tolerant)',
                'Company:u1ln1-': 'Get 1 line above (skip line breaks)',
                'Total:d1r2wd0-': 'Chained movement with flexible word extraction'
            },
            'variable_naming': {
                'invoice=Invoice Number:r1wd1': 'Named variable "invoice"',
                'company=Company Name:u1ln1': 'Named variable "company"',
                'total=Grand Total:d1nb1-': 'Named variable with flexible extraction'
            }
        }


# End of file #
