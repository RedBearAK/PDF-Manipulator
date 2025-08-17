"""
Enhanced pattern-based text extraction with Phase 3 multi-page and multi-match support.
File: pdf_manipulator/scraper/extractors/pattern_extractor.py

PHASE 3 ENHANCEMENTS:
- Multi-page search capability with range specifications
- Multi-match selection and filtering
- Enhanced result structure with metadata
- PDF page count analysis for range calculations
- Comprehensive error handling and warnings
"""

import re

from pathlib import Path

from pdf_manipulator.scraper.processors.pypdf_processor import PyPDFProcessor


class PatternExtractor:
    """
    Extract text based on patterns with advanced multi-page and multi-match capabilities.
    
    PHASE 3 ENHANCEMENTS:
    - Search across multiple pages with flexible range syntax
    - Select specific matches from multiple occurrences
    - Detailed result metadata and debugging information
    - Graceful handling of out-of-bounds conditions
    """
    
    def __init__(self):
        # Common number patterns for extraction
        self.number_pattern = re.compile(r'-?\d+(?:[.,]\d+)*')
        self.word_pattern = re.compile(r'\S+')
        self.pdf_processor = PyPDFProcessor(suppress_warnings=True)
    
    def extract_pattern_enhanced(self, pdf_path: Path, pattern: dict, 
                               page_spec: dict = None) -> dict:
        """
        Extract pattern with Phase 3 multi-page and multi-match support.
        
        Args:
            pdf_path: Path to PDF file
            pattern: Enhanced pattern dictionary with movements, extraction spec
            page_spec: Page specification for multi-page search
            
        Returns:
            Dictionary with comprehensive extraction results and metadata
        """
        # Determine pages to search
        if page_spec:
            pages_to_search = self._resolve_page_range(pdf_path, page_spec)
        else:
            pages_to_search = [1]  # Default to first page for backward compatibility
        
        if not pages_to_search:
            return {
                'success': False,
                'matches': [],
                'selected_match': "No_Match",
                'pages_searched': [],
                'warnings': ["No valid pages to search"],
                'debug_info': {'page_spec': page_spec}
            }
        
        # Extract text from specified pages and find all matches
        all_matches = []
        pages_with_text = []
        
        for page_num in pages_to_search:
            try:
                page_text = self._extract_page_text(pdf_path, page_num)
                if page_text.strip():  # Only process pages with content
                    pages_with_text.append(page_num)
                    page_matches = self.find_all_keyword_matches(page_text, pattern['keyword'])
                    
                    # Add page context and extract content from each match
                    for match in page_matches:
                        match['page'] = page_num
                        match['page_text'] = page_text
                        
                        # Extract content from this match position
                        extracted_content = self._extract_from_match_position(page_text, match, pattern)
                        match['extracted_content'] = extracted_content
                        
                        all_matches.append(match)
                        
            except Exception as e:
                # Continue with other pages if one fails
                continue
        
        if not all_matches:
            return {
                'success': False,
                'matches': [],
                'selected_match': "No_Match",
                'pages_searched': pages_with_text,
                'warnings': [f"Keyword '{pattern['keyword']}' not found on any searched page"],
                'debug_info': {
                    'total_pages_searched': len(pages_to_search),
                    'pages_with_content': len(pages_with_text),
                    'requested_pages': pages_to_search
                }
            }
        
        # Apply match selection
        match_spec = pattern.get('match_spec', {'type': 'single', 'value': 1})
        selected_matches, warnings = self._select_matches(all_matches, match_spec)
        
        if not selected_matches:
            return {
                'success': False,
                'matches': all_matches,
                'selected_match': "No_Match",
                'pages_searched': pages_with_text,
                'warnings': warnings,
                'debug_info': {
                    'total_matches_found': len(all_matches),
                    'match_spec': match_spec
                }
            }
        
        # Process selected matches
        if len(selected_matches) == 1:
            # Single match - return extracted content
            match = selected_matches[0]
            return {
                'success': True,
                'matches': all_matches,
                'selected_match': match['extracted_content'],
                'pages_searched': pages_with_text,
                'warnings': warnings,
                'debug_info': {
                    'matches_found': len(all_matches),
                    'matches_selected': 1,
                    'selected_from_page': match['page'],
                    'match_position': f"Line {match['line']}, Word {match['word_index']}"
                }
            }
        else:
            # Multiple matches - return list for debugging
            results = [match['extracted_content'] for match in selected_matches]
            return {
                'success': True,
                'matches': all_matches,
                'selected_match': results,  # List for multiple matches
                'pages_searched': pages_with_text,
                'warnings': warnings + ["Multiple matches selected - use mt<N> for single match"],
                'debug_info': {
                    'matches_found': len(all_matches),
                    'matches_selected': len(selected_matches),
                    'selected_pages': [match['page'] for match in selected_matches]
                }
            }
    
    def _resolve_page_range(self, pdf_path: Path, page_spec: dict) -> list[int]:
        """
        Convert page specification to actual page numbers.
        
        Args:
            pdf_path: Path to PDF file
            page_spec: Page specification dictionary
            
        Returns:
            List of valid page numbers
        """
        try:
            # Get total page count
            total_pages = self._get_pdf_page_count(pdf_path)
            
            if page_spec['type'] == 'all':
                return list(range(1, total_pages + 1))
            elif page_spec['type'] == 'single':
                page_num = page_spec['value']
                return [page_num] if 1 <= page_num <= total_pages else []
            elif page_spec['type'] == 'range':
                start = page_spec['start']
                end = min(page_spec['end'], total_pages)
                return list(range(start, end + 1)) if start <= total_pages else []
            elif page_spec['type'] == 'from':
                start = page_spec['start']
                return list(range(start, total_pages + 1)) if start <= total_pages else []
            elif page_spec['type'] == 'last':
                count = page_spec['count']
                start = max(1, total_pages - count + 1)
                return list(range(start, total_pages + 1))
            
            return []  # Fallback for unknown types
            
        except Exception:
            return []  # Fallback on any error
    
    def _get_pdf_page_count(self, pdf_path: Path) -> int:
        """
        Get the total number of pages in a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages, or 1 if unable to determine
        """
        try:
            import pypdf
            with open(pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                return len(reader.pages)
        except Exception:
            return 1  # Conservative fallback
    
    def _extract_page_text(self, pdf_path: Path, page_num: int) -> str:
        """
        Extract text from a specific page.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            
        Returns:
            Extracted text or empty string on error
        """
        try:
            return self.pdf_processor.extract_page(pdf_path, page_num)
        except Exception:
            return ""
    
    def _select_matches(self, matches: list, match_spec: dict) -> tuple[list, list]:
        """
        Select specific matches based on match specification.
        
        Args:
            matches: List of all found matches
            match_spec: Match selection specification
            
        Returns:
            Tuple of (selected_matches, warnings)
        """
        warnings = []
        
        if match_spec['type'] == 'all':
            return matches, warnings
        elif match_spec['type'] == 'single':
            idx = match_spec['value'] - 1  # Convert to 0-based
            if 0 <= idx < len(matches):
                return [matches[idx]], warnings
            else:
                warnings.append(f"Match {match_spec['value']} not found (only {len(matches)} matches)")
                return [], warnings
        elif match_spec['type'] == 'last':
            count = match_spec['count']
            if count > len(matches):
                warnings.append(f"Requested last {count} matches, only {len(matches)} available")
                return matches, warnings
            return matches[-count:], warnings
        elif match_spec['type'] == 'range':
            start_idx = match_spec['start'] - 1
            end_idx = match_spec['end']
            if start_idx >= len(matches):
                warnings.append(f"Match range {match_spec['start']}-{match_spec['end']} out of bounds")
                return [], warnings
            selected = matches[start_idx:end_idx]
            if not selected:
                warnings.append(f"No matches in range {match_spec['start']}-{match_spec['end']}")
            return selected, warnings
        elif match_spec['type'] == 'from':
            start_idx = match_spec['start'] - 1
            if start_idx >= len(matches):
                warnings.append(f"Match {match_spec['start']} and beyond not found")
                return [], warnings
            return matches[start_idx:], warnings
        
        return [matches[0]] if matches else [], warnings  # Fallback to first match
    
    def _extract_from_match_position(self, page_text: str, match_info: dict, pattern: dict) -> str:
        """
        Extract content from a specific match position using pattern movements.
        
        Args:
            page_text: Full page text
            match_info: Match position information
            pattern: Pattern specification with movements and extraction
            
        Returns:
            Extracted content or None if extraction fails
        """
        try:
            # Use existing enhanced extraction method
            return self._extract_content_enhanced(
                page_text,
                match_info,
                pattern['extract_type'],
                pattern['extract_count'],
                pattern.get('flexible', False),
                pattern.get('movements', [])
            )
        except Exception:
            return None
    
    # ========== BACKWARD COMPATIBILITY METHODS (from Phase 2) ==========
    
    def extract_pattern(self, text, pattern):
        """
        Legacy method for backward compatibility with Phase 2 patterns.
        """
        # Convert to single-page, single-match format for legacy callers
        if isinstance(pattern, dict) and 'keyword' in pattern:
            # Enhanced pattern format
            keyword_pos = self.find_keyword(text, pattern['keyword'])
            if keyword_pos is None:
                return None
            
            movements = pattern.get('movements', [])
            target_pos = self._calculate_target_position_chained(text, keyword_pos, movements)
            
            return self._extract_content_enhanced(
                text, target_pos, 
                pattern['extract_type'], 
                pattern['extract_count'],
                pattern.get('flexible', False)
            )
        else:
            # Legacy pattern format - delegate to original logic
            keyword = pattern.get('keyword', '')
            movement_direction = pattern.get('movement_direction', '')
            movement_distance = pattern.get('movement_distance', 0)
            extract_type = pattern.get('extract_type', 'word')
            
            keyword_pos = self.find_keyword(text, keyword)
            if keyword_pos is None:
                return None
            
            target_pos = self._calculate_target_position(text, keyword_pos, movement_direction, movement_distance)
            return self._extract_content(text, target_pos, extract_type)
    
    def find_keyword(self, text, keyword):
        """
        Find the position of a keyword in text.
        Enhanced to handle multi-word keywords and punctuation.
        """
        if not text or not keyword:
            return None
        
        lines = text.split('\n')
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        
        # If single word keyword, use original logic but handle punctuation
        if len(keyword_words) == 1:
            for line_idx, line in enumerate(lines):
                words = line.split()
                for word_idx, word in enumerate(words):
                    # Remove punctuation for comparison
                    clean_word = ''.join(c for c in word.lower() if c.isalnum())
                    clean_keyword = ''.join(c for c in keyword_lower if c.isalnum())
                    
                    if clean_keyword in clean_word:
                        return {
                            'line': line_idx,
                            'word_index': word_idx,
                            'word': word,
                            'line_text': line
                        }
        
        # Multi-word keyword matching
        else:
            for line_idx, line in enumerate(lines):
                words = line.split()
                for word_idx in range(len(words) - len(keyword_words) + 1):
                    # Check if consecutive words match the keyword
                    match = True
                    for i, kw in enumerate(keyword_words):
                        if word_idx + i >= len(words):
                            match = False
                            break
                        
                        word = words[word_idx + i]
                        # Remove punctuation for comparison
                        clean_word = ''.join(c for c in word.lower() if c.isalnum())
                        clean_keyword = ''.join(c for c in kw if c.isalnum())
                        
                        if clean_keyword not in clean_word:
                            match = False
                            break
                    
                    if match:
                        # Return position of the last word in the keyword phrase
                        return {
                            'line': line_idx,
                            'word_index': word_idx + len(keyword_words) - 1,
                            'word': words[word_idx + len(keyword_words) - 1],
                            'line_text': line
                        }
        
        return None

    def find_all_keyword_matches(self, text, keyword):
        """
        Find all occurrences of a keyword in the text.
        Enhanced for Phase 3 to return comprehensive match information.
        """
        if not text or not keyword:
            return []
        
        matches = []
        lines = text.split('\n')
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        
        # Single word keyword matching
        if len(keyword_words) == 1:
            for line_idx, line in enumerate(lines):
                words = line.split()
                for word_idx, word in enumerate(words):
                    # Remove punctuation for comparison
                    clean_word = ''.join(c for c in word.lower() if c.isalnum())
                    clean_keyword = ''.join(c for c in keyword_lower if c.isalnum())
                    
                    if clean_keyword in clean_word:
                        matches.append({
                            'line': line_idx,
                            'word_index': word_idx,
                            'word': word,
                            'line_text': line,
                            'match_text': word,
                            'keyword': keyword
                        })
        
        # Multi-word keyword matching
        else:
            for line_idx, line in enumerate(lines):
                words = line.split()
                for word_idx in range(len(words) - len(keyword_words) + 1):
                    # Check if consecutive words match the keyword
                    match = True
                    matched_words = []
                    
                    for i, kw in enumerate(keyword_words):
                        if word_idx + i >= len(words):
                            match = False
                            break
                        
                        word = words[word_idx + i]
                        # Remove punctuation for comparison
                        clean_word = ''.join(c for c in word.lower() if c.isalnum())
                        clean_keyword = ''.join(c for c in kw if c.isalnum())
                        
                        if clean_keyword not in clean_word:
                            match = False
                            break
                        
                        matched_words.append(word)
                    
                    if match:
                        # Use position of the last word in the keyword phrase
                        matches.append({
                            'line': line_idx,
                            'word_index': word_idx + len(keyword_words) - 1,
                            'word': words[word_idx + len(keyword_words) - 1],
                            'line_text': line,
                            'match_text': ' '.join(matched_words),
                            'keyword': keyword
                        })
        
        return matches

    def _calculate_target_position_chained(self, text, keyword_pos, movements):
        """
        Calculate target position using chained movements.
        Enhanced for Phase 3 with better error handling.
        """
        if not keyword_pos:
            return None
        
        lines = text.split('\n')
        current_line = keyword_pos['line']
        current_word = keyword_pos['word_index']
        
        # Apply each movement in sequence
        for direction, distance in movements:
            if direction == 'u':
                current_line = max(0, current_line - distance)
                # Reset word position to start of line
                current_word = 0
            elif direction == 'd':
                current_line = min(len(lines) - 1, current_line + distance)
                # Reset word position to start of line
                current_word = 0
            elif direction == 'l':
                # Move left within current line
                if current_line < len(lines):
                    words_in_line = len(lines[current_line].split())
                    current_word = max(0, current_word - distance)
            elif direction == 'r':
                # Move right within current line
                if current_line < len(lines):
                    words_in_line = len(lines[current_line].split())
                    current_word = min(words_in_line - 1, current_word + distance)
        
        # Validate final position
        if current_line >= len(lines):
            return None
        
        words_in_line = lines[current_line].split()
        if current_word >= len(words_in_line):
            return None
        
        return {
            'line': current_line,
            'word_index': current_word,
            'line_text': lines[current_line]
        }

    def _extract_content_enhanced(self, text, target_pos, extract_type, extract_count, flexible, movements=None):
        """
        Enhanced content extraction with Phase 2/3 features.
        """
        if not target_pos:
            return None
        
        lines = text.split('\n')
        start_line = target_pos['line']
        start_word = target_pos.get('word_index', 0)
        
        # Apply movements if provided (for direct calls)
        if movements:
            adjusted_pos = self._calculate_target_position_chained(text, target_pos, movements)
            if not adjusted_pos:
                return None
            start_line = adjusted_pos['line']
            start_word = adjusted_pos.get('word_index', 0)
        
        if extract_type == 'wd':
            return self._extract_words_enhanced(lines, start_line, start_word, extract_count, flexible)
        elif extract_type == 'ln':
            return self._extract_lines_enhanced(lines, start_line, extract_count, flexible)
        elif extract_type == 'nb':
            return self._extract_numbers_enhanced(lines, start_line, start_word, extract_count, flexible)
        
        return None

    def _extract_words_enhanced(self, lines, start_line, start_word, count, flexible):
        """Extract words with Phase 2/3 enhancements."""
        if start_line >= len(lines):
            return None
        
        if count == 0:
            # Zero-count: extract until end of line
            words = lines[start_line].split()
            if start_word >= len(words):
                return None
            result_words = words[start_word:]
            return ' '.join(result_words) if result_words else None
        
        # Non-zero count: extract specific number of words
        result_words = []
        current_line = start_line
        current_word = start_word
        words_needed = count
        
        while words_needed > 0 and current_line < len(lines):
            words = lines[current_line].split()
            
            # Extract words from current line
            while current_word < len(words) and words_needed > 0:
                result_words.append(words[current_word])
                current_word += 1
                words_needed -= 1
            
            # Move to next line if needed and flexible mode allows it
            if words_needed > 0 and flexible:
                current_line += 1
                current_word = 0
            else:
                break
        
        return ' '.join(result_words) if result_words else None

    def _extract_lines_enhanced(self, lines, start_line, count, flexible):
        """Extract lines with Phase 2/3 enhancements."""
        if start_line >= len(lines):
            return None
        
        if count == 0:
            # Zero-count: extract until end of document
            result_lines = lines[start_line:]
            return '\n'.join(result_lines) if result_lines else None
        
        # Non-zero count: extract specific number of lines
        end_line = min(start_line + count, len(lines))
        result_lines = lines[start_line:end_line]
        
        # In flexible mode, skip blank lines
        if flexible:
            result_lines = [line for line in result_lines if line.strip()]
        
        return '\n'.join(result_lines) if result_lines else None

    def _extract_numbers_enhanced(self, lines, start_line, start_word, count, flexible):
        """Extract numbers with Phase 2/3 enhancements."""
        if start_line >= len(lines):
            return None
        
        words = lines[start_line].split()
        if start_word >= len(words):
            return None
        
        if count == 0:
            # Zero-count: extract until non-numeric
            result_numbers = []
            for word in words[start_word:]:
                # Check if word contains numbers
                numbers = self.number_pattern.findall(word)
                if numbers:
                    result_numbers.extend(numbers)
                else:
                    break
            return ' '.join(result_numbers) if result_numbers else None
        
        # Non-zero count: extract specific number of numeric values
        result_numbers = []
        current_line = start_line
        current_word = start_word
        numbers_needed = count
        
        while numbers_needed > 0 and current_line < len(lines):
            words = lines[current_line].split()
            
            while current_word < len(words) and numbers_needed > 0:
                word = words[current_word]
                numbers = self.number_pattern.findall(word)
                
                for number in numbers:
                    if numbers_needed > 0:
                        result_numbers.append(number)
                        numbers_needed -= 1
                
                current_word += 1
            
            # Move to next line if needed and flexible mode allows it
            if numbers_needed > 0 and flexible:
                current_line += 1
                current_word = 0
            else:
                break
        
        return ' '.join(result_numbers) if result_numbers else None

    # Legacy methods for backward compatibility
    def _calculate_target_position(self, text, keyword_pos, direction, distance):
        """Legacy method - delegates to chained version."""
        direction_map = {
            'above': 'u', 'below': 'd',
            'left': 'l', 'right': 'r'
        }
        
        if direction in direction_map and distance > 0:
            movements = [(direction_map[direction], distance)]
        else:
            movements = []
        
        return self._calculate_target_position_chained(text, keyword_pos, movements)
    
    def _extract_content(self, text, target_pos, extract_type):
        """Legacy method - delegates to enhanced extraction."""
        type_map = {
            'word': ('wd', 1),
            'text': ('wd', 0),
            'line': ('ln', 1), 
            'number': ('nb', 1)
        }
        
        compact_type, count = type_map.get(extract_type, ('wd', 1))
        return self._extract_content_enhanced(text, target_pos, compact_type, count, False)
    
    def extract_multiple_patterns(self, text, patterns):
        """Extract multiple patterns from the same text."""
        results = []
        for pattern in patterns:
            result = self.extract_pattern(text, pattern)
            results.append(result)
        return results
    
    def debug_extraction(self, text, pattern):
        """Debug extraction process with detailed information."""
        debug_info = {
            'pattern': pattern,
            'success': False,
            'error': None,
            'keyword_found': False,
            'keyword_position': None,
            'target_position': None,
            'extracted': None
        }
        
        try:
            keyword = pattern.get('keyword', '')
            debug_info['keyword'] = keyword
            
            # Find keyword
            keyword_pos = self.find_keyword(text, keyword)
            if keyword_pos:
                debug_info['keyword_found'] = True
                debug_info['keyword_position'] = keyword_pos
                
                # Calculate target position
                movements = pattern.get('movements', [])
                target_pos = self._calculate_target_position_chained(text, keyword_pos, movements)
                debug_info['target_position'] = target_pos
                
                if target_pos:
                    # Extract content
                    extracted = self._extract_content_enhanced(
                        text, target_pos,
                        pattern.get('extract_type', 'wd'),
                        pattern.get('extract_count', 1),
                        pattern.get('flexible', False)
                    )
                    debug_info['extracted'] = extracted
                    debug_info['success'] = extracted is not None
                else:
                    debug_info['error'] = "Invalid target position after movements"
            else:
                debug_info['error'] = f"Keyword '{keyword}' not found"
                
        except Exception as e:
            debug_info['error'] = str(e)
        
        return debug_info


# End of file #
