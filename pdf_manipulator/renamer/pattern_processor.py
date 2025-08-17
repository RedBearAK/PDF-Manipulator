"""
Enhanced compact pattern syntax processor with Phase 3 multi-page and multi-match support.
File: pdf_manipulator/renamer/pattern_processor.py

PHASE 3 UPDATES:
- Enhanced syntax with pg<pages> and mt<matches> specifications
- Multi-page search capability with flexible range syntax
- Multi-match selection with range-based filtering
- Comprehensive range parsing: N, N-M, N-, -N, 0 (all)
- Backward compatible with Phase 2 syntax
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
    Process enhanced compact pattern syntax with multi-page and multi-match support.
    
    PHASE 3 ENHANCEMENTS:
    - Page specifications: pg3, pg2-4, pg3-, pg-2, pg0 (all pages)
    - Match specifications: mt2, mt1-3, mt2-, mt-2, mt0 (all matches)
    - Combined specifications: pattern+pg2-4mt3
    - Range validation and semantic error checking
    
    Enhanced Syntax: [var=]keyword:movements+extraction_type+count[-][pg<pages>][mt<matches>]
    
    Core Movements (unchanged):
    - u/d + 1-99: up/down lines
    - l/r + 1-99: left/right words
    - Maximum 2 movements, no conflicting directions
    
    Extraction Types (unchanged):
    - wd + 0-99: words (0 = until end of line)
    - ln + 0-99: lines (0 = until end of document)
    - nb + 0-99: numbers (0 = until non-numeric)
    
    NEW: Page/Match Range Syntax:
    - N: Specific number (pg3, mt2)
    - N-M: Range N through M (pg2-4, mt1-3)
    - N-: N through end (pg3-, mt2-)
    - -N: Last N items (pg-3, mt-2)
    - 0: All items (pg0, mt0)
    
    Examples:
    - "Invoice:r1wd1" - Basic (unchanged)
    - "Invoice:r1wd1mt2" - Second match
    - "Invoice:r1wd1pg2-4" - Search pages 2-4
    - "Invoice:r1wd1pg2-4mt-2" - Pages 2-4, last 2 matches
    """
    
    # Enhanced regex for Phase 3 syntax with optional pg/mt specifications
    COMPACT_PATTERN = re.compile(
        r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})(-?)'
        r'(pg(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?'
        r'(mt(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?$'
    )
    
    def __init__(self):
        self.extractor = PatternExtractor()
        self.processor = PyPDFProcessor(suppress_warnings=True)
        
    def parse_pattern_string(self, pattern_str: str) -> tuple[str, str, dict]:
        """
        Parse full pattern string into variable name, keyword, and extraction spec.
        
        Args:
            pattern_str: Full pattern like "invoice=Invoice Number:r1wd1pg2-4mt2"
            
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
        
        # Parse enhanced compact extraction specification
        extraction_spec = self._parse_extraction_spec(compact_spec)
        
        # Generate variable name if not provided
        if variable_name is None:
            variable_name = auto_generate_variable_name(keyword)
        
        return variable_name, keyword, extraction_spec
    
    def _parse_extraction_spec(self, spec: str) -> dict:
        """
        Parse enhanced extraction specification with pg/mt support.
        
        Args:
            spec: Enhanced spec like "r1wd1pg2-4mt3-"
            
        Returns:
            Dictionary with parsed movement, extraction, page, and match details
            
        Raises:
            CompactPatternError: For invalid syntax
        """
        spec = spec.strip()
        
        # Match the enhanced pattern
        match = self.COMPACT_PATTERN.match(spec)
        if not match:
            raise CompactPatternError(
                f"Invalid enhanced syntax: '{spec}'. "
                f"Expected format: [movement][movement]extraction_type+count[-][pg<pages>][mt<matches>]"
            )
        
        # Parse base components (movements, extraction)
        result = self._parse_base_components(match)
        
        # Parse page specification (group 6)
        if match.group(6):
            pg_spec = match.group(6)[2:]  # Remove 'pg' prefix
            result['page_spec'] = self._parse_range_spec(pg_spec, 'page')
        
        # Parse match specification (group 7)
        if match.group(7):
            mt_spec = match.group(7)[2:]  # Remove 'mt' prefix
            result['match_spec'] = self._parse_range_spec(mt_spec, 'match')
        
        # Validate the complete specification
        self._validate_extraction_spec(result)
        
        return result
    
    def _parse_base_components(self, match: re.Match) -> dict:
        """Parse movement and extraction components from regex match."""
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
        flexible = bool(match.group(5))  # '-' suffix
        
        # Validate basic constraints
        self._validate_base_constraints(movements, extract_type, extract_count)
        
        return {
            'movements': movements,
            'extract_type': extract_type,
            'extract_count': extract_count,
            'flexible': flexible
        }
    
    def _parse_range_spec(self, range_str: str, spec_type: str) -> dict:
        """
        Parse range specifications: '2-4', '3-', '-2', '0'
        
        Args:
            range_str: Range specification string
            spec_type: Type for error messages ('page' or 'match')
            
        Returns:
            Dictionary describing the range
        """
        if range_str == '0':
            return {'type': 'all'}
        elif '-' not in range_str:
            # Single number: pg3, mt2
            value = int(range_str)
            if value < 1:
                raise CompactPatternError(f"Invalid {spec_type} number: {value} (must be >= 1)")
            return {'type': 'single', 'value': value}
        elif range_str.startswith('-'):
            # Last N: pg-3, mt-2
            count = int(range_str[1:])
            if count < 1:
                raise CompactPatternError(f"Invalid last {spec_type} count: {count} (must be >= 1)")
            return {'type': 'last', 'count': count}
        elif range_str.endswith('-'):
            # From N to end: pg3-, mt2-
            start = int(range_str[:-1])
            if start < 1:
                raise CompactPatternError(f"Invalid {spec_type} start: {start} (must be >= 1)")
            return {'type': 'from', 'start': start}
        else:
            # Range N-M: pg2-4, mt1-3
            try:
                start_str, end_str = range_str.split('-')
                start = int(start_str)
                end = int(end_str)
                
                if start < 1 or end < 1:
                    raise CompactPatternError(f"Invalid {spec_type} range: {start}-{end} (both must be >= 1)")
                if start > end:
                    raise CompactPatternError(f"Backwards {spec_type} range: {start}-{end} (start > end)")
                
                return {'type': 'range', 'start': start, 'end': end}
            except ValueError:
                raise CompactPatternError(f"Invalid {spec_type} range format: {range_str}")
    
    def _parse_movement(self, move_str: str) -> tuple[str, int]:
        """Parse single movement like 'u1' or 'r15'."""
        direction = move_str[0]
        distance = int(move_str[1:])
        return direction, distance
    
    def _validate_base_constraints(self, movements: list, extract_type: str, extract_count: int):
        """Validate basic pattern constraints (unchanged from Phase 2)."""
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
    
    def _validate_extraction_spec(self, spec: dict) -> None:
        """Validate complete extraction specification for semantic correctness."""
        # Page specification validation
        if 'page_spec' in spec:
            page_spec = spec['page_spec']
            if page_spec['type'] == 'range':
                # Already validated during parsing
                pass
            elif page_spec['type'] == 'single':
                if page_spec['value'] > 999:  # Reasonable upper limit
                    raise CompactPatternError(f"Page number too large: {page_spec['value']}")
            elif page_spec['type'] == 'last':
                if page_spec['count'] > 100:  # Reasonable upper limit
                    raise CompactPatternError(f"Last page count too large: {page_spec['count']}")
        
        # Match specification validation
        if 'match_spec' in spec:
            match_spec = spec['match_spec']
            if match_spec['type'] == 'range':
                # Already validated during parsing
                pass
            elif match_spec['type'] == 'single':
                if match_spec['value'] > 999:  # Reasonable upper limit
                    raise CompactPatternError(f"Match number too large: {match_spec['value']}")
            elif match_spec['type'] == 'last':
                if match_spec['count'] > 100:  # Reasonable upper limit
                    raise CompactPatternError(f"Last match count too large: {match_spec['count']}")
    
    def convert_to_enhanced_pattern(self, keyword: str, extraction_spec: dict) -> dict:
        """
        Convert enhanced specification to PatternExtractor format.
        
        Args:
            keyword: Search keyword
            extraction_spec: Parsed extraction specification
            
        Returns:
            Dictionary compatible with enhanced PatternExtractor
        """
        return {
            'keyword': keyword,
            'movements': extraction_spec['movements'],
            'extract_type': extraction_spec['extract_type'],
            'extract_count': extraction_spec['extract_count'],
            'flexible': extraction_spec['flexible'],
            # Phase 3 additions
            'page_spec': extraction_spec.get('page_spec'),
            'match_spec': extraction_spec.get('match_spec')
        }
    
    def extract_from_pdf(self, pdf_path: Path, variable_name: str, keyword: str,
                         extraction_spec: dict, source_page: int = 1) -> dict:
        """
        Extract content using enhanced pattern with multi-page/multi-match support.
        
        Args:
            pdf_path: Path to PDF file
            variable_name: Variable name for this extraction
            keyword: Search keyword
            extraction_spec: Parsed extraction specification
            source_page: Fallback page if no page specification
            
        Returns:
            Dictionary with extraction results and metadata
        """
        try:
            # Convert to enhanced pattern format
            enhanced_pattern = self.convert_to_enhanced_pattern(keyword, extraction_spec)
            
            # Determine page specification for extractor
            if 'page_spec' in extraction_spec:
                page_spec = extraction_spec['page_spec']
            else:
                # Default to source_page for backward compatibility
                page_spec = {'type': 'single', 'value': source_page}
            
            # Use enhanced extractor with multi-page/multi-match support
            extractor_result = self.extractor.extract_pattern_enhanced(
                pdf_path, enhanced_pattern, page_spec
            )
            
            if extractor_result['success']:
                # Handle single vs multiple results
                selected_match = extractor_result['selected_match']
                if isinstance(selected_match, list):
                    # Multiple matches - use first for filename, warn about others
                    clean_result = sanitize_content_for_filename(
                        selected_match[0],
                        self._infer_content_type(extraction_spec['extract_type'])
                    )
                    warnings = extractor_result['warnings'] + [
                        f"Using first of {len(selected_match)} matches for filename"
                    ]
                else:
                    # Single match or No_Match
                    clean_result = sanitize_content_for_filename(
                        selected_match,
                        self._infer_content_type(extraction_spec['extract_type'])
                    ) if selected_match != "No_Match" else "No_Match"
                    warnings = extractor_result['warnings']
                
                return {
                    'variable_name': variable_name,
                    'keyword': keyword,
                    'success': True,
                    'selected_match': clean_result,
                    'raw_result': selected_match,
                    'pages_searched': extractor_result['pages_searched'],
                    'total_matches_found': len(extractor_result['matches']),
                    'warnings': warnings,
                    'debug_info': extractor_result['debug_info']
                }
            else:
                return {
                    'variable_name': variable_name,
                    'keyword': keyword,
                    'success': False,
                    'selected_match': extractor_result['selected_match'],
                    'pages_searched': extractor_result['pages_searched'],
                    'warnings': extractor_result['warnings'],
                    'debug_info': extractor_result['debug_info']
                }
                
        except Exception as e:
            return {
                'variable_name': variable_name,
                'keyword': keyword,
                'success': False,
                'selected_match': f"Error: {str(e)}",
                'warnings': [f"Extraction failed: {str(e)}"],
                'debug_info': {'exception': str(e)}
            }
    
    def validate_pattern_list(self, pattern_strings: list[str]) -> list[tuple[str, str, dict]]:
        """
        Validate and parse a list of enhanced pattern strings.
        
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
    
    def debug_enhanced_pattern(self, pdf_path: Path, pattern_string: str, 
                              source_page: int = 1) -> dict:
        """
        Debug enhanced pattern extraction with detailed analysis.
        
        Args:
            pdf_path: Path to PDF file
            pattern_string: Enhanced pattern string to debug
            source_page: Fallback page for patterns without pg specification
            
        Returns:
            Comprehensive debugging information
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
            'pages_to_search': None,
            'extractor_result': None,
            'final_result': None
        }
        
        try:
            # Parse enhanced pattern
            variable_name, keyword, extraction_spec = self.parse_pattern_string(pattern_string)
            debug_info.update({
                'parsing_success': True,
                'variable_name': variable_name,
                'keyword': keyword,
                'extraction_spec': extraction_spec
            })
            
            # Show what pages would be searched
            if 'page_spec' in extraction_spec:
                debug_info['pages_to_search'] = f"Pages as specified: {extraction_spec['page_spec']}"
            else:
                debug_info['pages_to_search'] = f"Default to page {source_page}"
            
            # Perform extraction
            result = self.extract_from_pdf(pdf_path, variable_name, keyword, extraction_spec, source_page)
            debug_info['extractor_result'] = result
            
            if result['success']:
                debug_info.update({
                    'extraction_success': True,
                    'final_result': result['selected_match']
                })
            else:
                debug_info['extraction_error'] = result.get('warnings', ['Unknown error'])
                
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
    
    def get_enhanced_pattern_examples(self) -> dict[str, dict]:
        """
        Get examples of valid enhanced patterns for documentation.
        
        Returns:
            Dictionary of example patterns with descriptions
        """
        return {
            # Basic patterns (unchanged)
            'basic_word': {
                'pattern': 'Invoice Number:r1wd1',
                'description': 'Extract 1 word to the right of "Invoice Number"'
            },
            'basic_line': {
                'pattern': 'company=Company:u1ln1',
                'description': 'Extract 1 line above "Company", store as "company"'
            },
            
            # Multi-match patterns
            'second_match': {
                'pattern': 'Invoice Number:r1wd1mt2',
                'description': 'Extract from second occurrence of "Invoice Number"'
            },
            'last_two_matches': {
                'pattern': 'Amount:r1nb1mt-2',
                'description': 'Extract from last 2 occurrences of "Amount"'
            },
            'all_matches': {
                'pattern': 'Item:r1wd2mt0',
                'description': 'Extract from all occurrences of "Item" (debug mode)'
            },
            
            # Multi-page patterns
            'specific_page': {
                'pattern': 'Total:r1nb1pg2',
                'description': 'Search for "Total" only on page 2'
            },
            'page_range': {
                'pattern': 'Contact:u1ln1pg2-4',
                'description': 'Search pages 2-4 for "Contact"'
            },
            'from_page': {
                'pattern': 'Summary:d1wd5pg3-',
                'description': 'Search from page 3 to end for "Summary"'
            },
            'last_pages': {
                'pattern': 'Signature:u1wd2pg-2',
                'description': 'Search last 2 pages for "Signature"'
            },
            
            # Combined specifications
            'complex_pattern': {
                'pattern': 'ref=Reference:r1wd1pg2-4mt3',
                'description': 'Third match of "Reference" from pages 2-4, store as "ref"'
            },
            'flexible_pattern': {
                'pattern': 'address=Address:d1wd0-pg1mt2',
                'description': 'Second "Address" match from page 1, extract all words flexibly'
            }
        }


# End of file #
