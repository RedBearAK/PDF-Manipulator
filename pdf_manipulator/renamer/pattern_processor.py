"""
Enhanced compact pattern syntax processor with Phase 4 start/end trimming support.
File: pdf_manipulator/renamer/pattern_processor.py

PHASE 4 UPDATES:
- Start/end trimming system using ^ and $ symbols
- Enhanced flag system with _ for space exclusion
- Multiple trimmer operations per block
- Backward compatible with all previous phases
- Clean regex import from dedicated patterns module
"""

from pathlib import Path
from rich.console import Console

from pdf_manipulator.renamer.renamer_regex_patterns import (
    COMPACT_PATTERN_RGX,
    STRAY_START_TRIMMER_RGX, 
    STRAY_END_TRIMMER_RGX,
    PYTHON_IDENTIFIER_RGX
)
from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor
from pdf_manipulator.scraper.processors.pypdf_processor import PyPDFProcessor
from pdf_manipulator.scraper.extractors.trimming import (
    parse_trimmer_block, 
    apply_trimmers, 
    validate_trimming_feasibility,
    TrimmingError
)
from pdf_manipulator.renamer.sanitizer import auto_generate_variable_name, sanitize_content_for_filename


console = Console()


class CompactPatternError(Exception):
    """Exception for compact pattern parsing errors."""
    pass


class PatternProcessor:
    """
    Process enhanced compact pattern syntax with Phase 4 start/end trimming support.
    
    PHASE 4 ENHANCEMENTS:
    - Start trimming blocks: ^ch5wd1nb2 (trim chars, words, numbers from start)
    - End trimming blocks: $wd2ch3ln1 (trim words, chars, lines from end)
    - Enhanced flag system: _ excludes spaces from extraction
    - Multiple operations per trimmer block processed sequentially
    - Comprehensive validation and error handling
    
    Enhanced Syntax: [var=]keyword:movements+extraction_type+count[flags][^start_trimmers][$end_trimmers][pg<pages>][mt<matches>]
    
    Core Movements (unchanged):
    - u/d + 1-99: up/down lines
    - l/r + 1-99: left/right words
    - Maximum 2 movements, no conflicting directions
    
    Extraction Types (unchanged):
    - wd + 0-99: words (0 = until end of line)
    - ln + 0-99: lines (0 = until end of document)
    - nb + 0-99: numbers (0 = until non-numeric)
    
    NEW: Enhanced Flags:
    - _: Exclude spaces from extracted content (before trimming)
    - -: Cross newlines during extraction (Phase 3 feature)
    
    NEW: Trimming Operations:
    - ^chN: Trim N characters from start
    - ^wdN: Trim N words from start  
    - ^lnN: Trim N lines from start
    - ^nbN: Trim N numbers from start
    - $chN: Trim N characters from end
    - $wdN: Trim N words from end
    - $lnN: Trim N lines from end
    - $nbN: Trim N numbers from end
    - Multiple trimmers: ^ch5wd1$nb2ch3
    
    Page/Match Range Syntax (unchanged from Phase 3):
    - N: Specific number (pg3, mt2)
    - N-M: Range N through M (pg2-4, mt1-3)
    - N-: N through end (pg3-, mt2-)
    - -N: Last N items (pg-3, mt-2)
    - 0: All items (pg0, mt0)
    
    Examples:
    - "Invoice:r1wd1^ch4" - Basic with start trimming
    - "Company:r1wd3_^ch8$ch12" - Spaces excluded, both end trimming
    - "Amount:r1nb1_^ch1" - Number without currency symbol
    - "Reference:r1wd4_^wd2ch3$wd1pg2" - Complex trimming with page spec
    """
    
    def __init__(self):
        self.extractor = PatternExtractor()
        self.processor = PyPDFProcessor(suppress_warnings=True)
        
    def parse_pattern_string(self, pattern_str: str) -> tuple[str, str, dict]:
        """
        Parse full pattern string into variable name, keyword, and extraction spec.
        
        Args:
            pattern_str: Full pattern like "invoice=Invoice Number:r1wd1_^ch4$ch2pg2-4mt2"
            
        Returns:
            Tuple of (variable_name, keyword, extraction_spec)
            
        Raises:
            CompactPatternError: For invalid syntax
        """
        # Check for explicit variable name
        if '=' in pattern_str:
            var_part, pattern_part = pattern_str.split('=', 1)
            variable_name = var_part.strip()
            
            # Validate variable name using regex pattern
            if not PYTHON_IDENTIFIER_RGX.match(variable_name):
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
        Parse enhanced extraction specification with Phase 4 trimming support.
        
        Args:
            spec: Enhanced spec like "r1wd1_^ch4$ch2pg2-4mt3-"
            
        Returns:
            Dictionary with parsed movement, extraction, trimming, page, and match details
            
        Raises:
            CompactPatternError: For invalid syntax
        """
        spec = spec.strip()
        
        # Check for invalid stray ^ or $ characters using dedicated patterns
        if '^' in spec and not STRAY_START_TRIMMER_RGX.search(spec):
            raise CompactPatternError(f"Invalid '^' character without valid trimmer operations in: '{spec}'")
        
        if '$' in spec and not STRAY_END_TRIMMER_RGX.search(spec):
            raise CompactPatternError(f"Invalid '$' character without valid trimmer operations in: '{spec}'")
        
        # Match using the main compact pattern regex
        match = COMPACT_PATTERN_RGX.match(spec)
        if not match:
            raise CompactPatternError(
                f"Invalid enhanced syntax: '{spec}'. "
                f"Expected format: [movements][type][count][flags][^start_trimmers][$end_trimmers][pg<pages>][mt<matches>]"
            )
        
        groups = match.groups()
        
        # Extract and validate movements
        movements = self._extract_movements(groups[0], groups[1])
        
        # Extract type and count
        extract_type = groups[2]
        extract_count = int(groups[3])
        
        # Parse enhanced flags
        flags = self._parse_enhanced_flags(groups[4])
        
        # Parse trimmer blocks
        start_trimmers = []
        end_trimmers = []
        
        if groups[5]:  # Start trimmer block
            start_block = groups[5][1:]  # Remove ^ prefix
            try:
                start_trimmers = parse_trimmer_block(start_block)
            except TrimmingError as e:
                raise CompactPatternError(f"Invalid start trimmer block '^{start_block}': {e}")
        
        if groups[6]:  # End trimmer block  
            end_block = groups[6][1:]  # Remove $ prefix
            try:
                end_trimmers = parse_trimmer_block(end_block)
            except TrimmingError as e:
                raise CompactPatternError(f"Invalid end trimmer block '${end_block}': {e}")
        
        # Parse page and match specifications
        page_spec = self._parse_range_spec_group(groups[7], 'page') if groups[7] else None
        match_spec = self._parse_range_spec_group(groups[8], 'match') if groups[8] else None
        
        return {
            'movements': movements,
            'extract_type': extract_type,
            'extract_count': extract_count,
            'flags': flags,
            'start_trimmers': start_trimmers,
            'end_trimmers': end_trimmers,
            'page_spec': page_spec,
            'match_spec': match_spec
        }
    
    def _extract_movements(self, move1: str, move2: str) -> list[tuple[str, int]]:
        """Extract and validate movements."""
        movements = []
        
        if move1:
            direction = move1[0]
            distance = int(move1[1:])
            movements.append((direction, distance))
        
        if move2:
            direction = move2[0]
            distance = int(move2[1:])
            
            # Validate no conflicting directions
            if movements and self._directions_conflict(movements[0][0], direction):
                raise CompactPatternError(
                    f"Conflicting movement directions: {movements[0][0]} and {direction}"
                )
            
            movements.append((direction, distance))
        
        return movements
    
    def _directions_conflict(self, dir1: str, dir2: str) -> bool:
        """Check if two movement directions conflict."""
        conflicts = {
            ('u', 'd'), ('d', 'u'),
            ('l', 'r'), ('r', 'l')
        }
        return (dir1, dir2) in conflicts
    
    def _parse_enhanced_flags(self, flag_str: str) -> dict:
        """
        Parse enhanced flags including Phase 4 space exclusion.
        
        Args:
            flag_str: Flag string like "_-" or "-_"
            
        Returns:
            Dictionary with flag settings
        """
        flags = {
            'flexible': False,        # Phase 2 flexible extraction (- at end)
            'cross_newlines': False,  # Phase 3 cross-newline support
            'exclude_spaces': False   # Phase 4 space exclusion
        }
        
        if not flag_str:
            return flags
        
        for char in flag_str:
            if char == '-':
                flags['cross_newlines'] = True
                flags['flexible'] = True  # For backward compatibility
            elif char == '_':
                flags['exclude_spaces'] = True
            else:
                raise CompactPatternError(f"Unknown flag character: '{char}'")
        
        return flags
    
    def _parse_range_spec_group(self, range_group: str, spec_type: str) -> dict:
        """Parse page or match range specification."""
        if not range_group:
            return None
        
        # Remove prefix (pg or mt)
        range_str = range_group[2:]
        return self._parse_range_spec(range_str, spec_type)
    
    def _parse_range_spec(self, range_str: str, spec_type: str) -> dict:
        """Parse range specification."""
        if range_str == '0':
            return {'type': 'all'}
        
        if '-' not in range_str:
            # Single number
            try:
                value = int(range_str)
                if value < 1:
                    raise CompactPatternError(f"Invalid {spec_type} number: {value}")
                return {'type': 'single', 'value': value}
            except ValueError:
                raise CompactPatternError(f"Invalid {spec_type} specification: {range_str}")
        
        if range_str.startswith('-'):
            # Last N items: -3
            try:
                count = int(range_str[1:])
                if count < 1:
                    raise CompactPatternError(f"Invalid last {spec_type} count: {count}")
                return {'type': 'last', 'count': count}
            except ValueError:
                raise CompactPatternError(f"Invalid last {spec_type} specification: {range_str}")
        
        if range_str.endswith('-'):
            # From N to end: 3-
            try:
                start = int(range_str[:-1])
                if start < 1:
                    raise CompactPatternError(f"Invalid {spec_type} start: {start}")
                return {'type': 'from', 'start': start}
            except ValueError:
                raise CompactPatternError(f"Invalid from {spec_type} specification: {range_str}")
        
        # Range: N-M
        parts = range_str.split('-')
        if len(parts) != 2:
            raise CompactPatternError(f"Invalid {spec_type} range: {range_str}")
        
        try:
            start = int(parts[0])
            end = int(parts[1])
            
            if start < 1 or end < 1:
                raise CompactPatternError(f"Invalid {spec_type} range values: {start}-{end}")
            
            if start > end:
                raise CompactPatternError(f"Backwards {spec_type} range: {start}-{end}")
            
            return {'type': 'range', 'start': start, 'end': end}
        
        except ValueError:
            raise CompactPatternError(f"Invalid {spec_type} range specification: {range_str}")
    
    def validate_pattern_list(self, patterns: list[str]) -> list[dict]:
        """
        Validate list of pattern strings and check for duplicates.
        
        Returns:
            List of parsed pattern dictionaries
        """
        parsed_patterns = []
        variable_names = set()
        
        for pattern_str in patterns:
            var_name, keyword, extraction_spec = self.parse_pattern_string(pattern_str)
            
            if var_name in variable_names:
                raise CompactPatternError(f"Duplicate variable name: '{var_name}'")
            
            variable_names.add(var_name)
            
            parsed_patterns.append({
                'variable_name': var_name,
                'keyword': keyword,
                'extraction_spec': extraction_spec,
                'original_pattern': pattern_str
            })
        
        return parsed_patterns
    
    def get_enhanced_pattern_examples(self) -> dict:
        """Get examples of Phase 4 enhanced pattern syntax."""
        return {
            'basic_trimming': {
                'pattern': 'invoice=Invoice Number:r1wd1^ch4',
                'description': 'Extract invoice number, trim 4 characters from start'
            },
            'space_exclusion': {
                'pattern': 'company=Company:r1wd3_^ch8$ch12',
                'description': 'Extract company name, exclude spaces, trim both ends'
            },
            'currency_removal': {
                'pattern': 'amount=Total:r1nb1_^ch1',
                'description': 'Extract amount, exclude spaces, remove currency symbol'
            },
            'complex_cleanup': {
                'pattern': 'ref=Reference:r1wd4_^wd2ch3$wd1pg2',
                'description': 'Complex reference cleanup with multi-level trimming'
            },
            'number_extraction': {
                'pattern': 'code=Code:r1wd1$nb1',
                'description': 'Extract code, trim numeric suffix'
            },
            'multi_page_trimmed': {
                'pattern': 'title=Title:u1ln1^ch5$ch3pg2-4mt2',
                'description': 'Multi-page title extraction with character trimming'
            }
        }
    
    def process_pdf_with_patterns(self, pdf_path: Path, patterns: list[str]) -> dict:
        """
        Process PDF file with multiple patterns and return extracted data.
        
        Args:
            pdf_path: Path to PDF file
            patterns: List of pattern strings
            
        Returns:
            Dictionary with extracted variable values
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Validate and parse patterns
        parsed_patterns = self.validate_pattern_list(patterns)
        
        # Extract text from PDF
        try:
            pdf_text = self.processor.extract_text_simple(pdf_path)
        except Exception as e:
            raise CompactPatternError(f"Failed to extract text from PDF: {e}")
        
        # Process each pattern
        results = {}
        for pattern_info in parsed_patterns:
            var_name = pattern_info['variable_name']
            keyword = pattern_info['keyword']
            extraction_spec = pattern_info['extraction_spec']
            
            try:
                # Use PatternExtractor to extract content
                extracted_value = self.extractor.extract_pattern_enhanced(
                    pdf_path, 
                    {
                        'keyword': keyword,
                        **extraction_spec
                    }
                )
                
                # Apply trimming if specified
                if extraction_spec.get('start_trimmers') or extraction_spec.get('end_trimmers'):
                    if extracted_value and 'result' in extracted_value:
                        content = extracted_value['result']
                        
                        # Apply space exclusion flag if set
                        if extraction_spec.get('flags', {}).get('exclude_spaces'):
                            content = content.replace(' ', '')
                        
                        # Apply trimming
                        trimmed_content = apply_trimmers(
                            content,
                            extraction_spec.get('start_trimmers', []),
                            extraction_spec.get('end_trimmers', [])
                        )
                        
                        extracted_value['result'] = trimmed_content
                
                results[var_name] = extracted_value
                
            except Exception as e:
                results[var_name] = {
                    'error': str(e),
                    'pattern': pattern_info['original_pattern']
                }
        
        return results


# End of file #
