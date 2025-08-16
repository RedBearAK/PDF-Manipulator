"""
Enhanced pattern-based text extraction with chained movements and advanced features.
File: pdf_manipulator/scraper/extractors/pattern_extractor.py

ENHANCEMENTS FOR PHASE 2:
- Chained movement support: [('u', 1), ('r', 2)]
- Zero-count extraction: wd0, ln0, nb0 (until end semantics)
- Flexible extraction mode: skip line breaks with '-' suffix
- Backward compatibility with existing single-movement patterns
"""

import re


class PatternExtractor:
    """
    Extract text based on patterns with advanced movement and extraction capabilities.
    
    PHASE 2 ENHANCEMENTS:
    - Supports chained movements for complex navigation
    - Zero-count extraction with "until end" semantics
    - Flexible mode for format-tolerant extraction
    - Maintains full backward compatibility
    """
    
    def __init__(self):
        # Common number patterns for extraction
        self.number_pattern = re.compile(r'-?\d+(?:[.,]\d+)*')
        self.word_pattern = re.compile(r'\S+')
    
    def extract_pattern(self, text, pattern):
        """
        Extract text based on a pattern specification.
        
        ENHANCED to support both legacy and new compact pattern formats.
        
        Args:
            text (str): The source text to search
            pattern (dict): Pattern specification with keys:
                LEGACY FORMAT:
                - keyword: Text to search for
                - direction: 'left', 'right', 'above', 'below'
                - distance: Number of words/lines to move
                - extract_type: 'word', 'number', 'line', 'text'
                
                NEW ENHANCED FORMAT:
                - keyword: Text to search for
                - movements: List of (direction, distance) tuples [('u', 1), ('r', 2)]
                - extract_type: 'wd', 'ln', 'nb' (compact types)
                - extract_count: Number to extract (0 = until end)
                - flexible: Boolean for line-break tolerant extraction
        
        Returns:
            str or None: Extracted text, or None if pattern not found
        """
        keyword = pattern['keyword']
        
        # Detect pattern format and normalize
        if 'movements' in pattern:
            # New enhanced format
            movements = pattern['movements']
            extract_type = pattern['extract_type']
            extract_count = pattern.get('extract_count', 1)
            flexible = pattern.get('flexible', False)
        else:
            # Legacy format - convert to new format
            direction = pattern['direction']
            distance = pattern['distance']
            legacy_type = pattern['extract_type']
            
            # Convert legacy direction to movement tuple
            direction_map = {
                'above': 'u', 'below': 'd',
                'left': 'l', 'right': 'r'
            }
            
            if direction in direction_map and distance > 0:
                movements = [(direction_map[direction], distance)]
            else:
                movements = []  # No movement for distance 0
            
            # Convert legacy extract type
            type_map = {
                'word': ('wd', 1),
                'text': ('wd', 0),  # text = words until end
                'line': ('ln', 1),
                'number': ('nb', 1)
            }
            extract_type, extract_count = type_map.get(legacy_type, ('wd', 1))
            flexible = False
        
        # Find keyword position
        keyword_pos = self._find_keyword_position(text, keyword)
        if keyword_pos is None:
            return None
        
        # Calculate target position using chained movements
        target_pos = self._calculate_target_position_chained(
            text, keyword_pos, movements
        )
        if target_pos is None:
            return None
        
        # Extract content using enhanced extraction
        return self._extract_content_enhanced(
            text, target_pos, extract_type, extract_count, flexible
        )
    
    def _find_keyword_position(self, text, keyword):
        """
        Find the position of a keyword in the text.
        
        Returns:
            dict or None: Position info with 'line', 'word_index', 'char_start', 'char_end'
        """
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            # Case-insensitive search for keyword
            start_pos = line.lower().find(keyword.lower())
            if start_pos != -1:
                # Find the end position of the keyword
                end_pos = start_pos + len(keyword)
                
                # Split line into words and track positions
                words = line.split()
                char_pos = 0
                keyword_end_word = None
                
                # Find the word position AFTER the keyword ends
                for word_idx, word in enumerate(words):
                    word_start = char_pos
                    word_end = char_pos + len(word)
                    
                    # If keyword ends before or at this word's end, this is our reference point
                    if end_pos <= word_end:
                        keyword_end_word = word_idx
                        break
                    
                    char_pos = word_end + 1  # +1 for space
                
                # Default to last word if keyword extends beyond
                if keyword_end_word is None:
                    keyword_end_word = len(words) - 1
                
                return {
                    'line': line_idx,
                    'word_index': keyword_end_word,  # Position after keyword
                    'char_start': start_pos,
                    'char_end': end_pos,
                    'line_text': line,
                    'keyword_end_word': keyword_end_word
                }
        
        return None
    
    def _calculate_target_position_chained(self, text, keyword_pos, movements):
        """
        Calculate target position using chained movements.
        
        NEW: Supports multiple movements in sequence: [('u', 1), ('r', 2)]
        
        Args:
            text (str): Source text
            keyword_pos (dict): Starting position from keyword
            movements (list): List of (direction, distance) tuples
            
        Returns:
            dict or None: Final target position
        """
        lines = text.split('\n')
        current_line = keyword_pos['line']
        current_word = keyword_pos['word_index']
        
        # Handle zero movements (extract at position after keyword)
        if not movements:
            return {
                'line': current_line,
                'word_index': current_word,
                'line_text': lines[current_line] if current_line < len(lines) else ""
            }
        
        # Process each movement in sequence
        for direction, distance in movements:
            target_pos = self._apply_single_movement(
                lines, current_line, current_word, direction, distance
            )
            
            if target_pos is None:
                return None  # Movement went out of bounds
            
            # Update position for next movement
            current_line = target_pos['line']
            current_word = target_pos['word_index']
        
        # Return final position
        return {
            'line': current_line,
            'word_index': current_word,
            'line_text': lines[current_line] if current_line < len(lines) else ""
        }
    
    def _apply_single_movement(self, lines, current_line, current_word, direction, distance):
        """
        Apply a single movement from current position.
        
        Args:
            lines (list): All text lines
            current_line (int): Current line index
            current_word (int): Current word index
            direction (str): 'u', 'd', 'l', 'r'
            distance (int): How far to move
            
        Returns:
            dict or None: New position or None if out of bounds
        """
        if direction == 'l':  # left
            target_word = current_word - distance
            if target_word < 0:
                return None
            return {
                'line': current_line,
                'word_index': target_word,
                'line_text': lines[current_line]
            }
        
        elif direction == 'r':  # right
            words_in_line = len(lines[current_line].split())
            target_word = current_word + distance
            if target_word >= words_in_line:
                return None
            return {
                'line': current_line,
                'word_index': target_word,
                'line_text': lines[current_line]
            }
        
        elif direction == 'u':  # above
            target_line = current_line - distance
            if target_line < 0:
                return None
            return {
                'line': target_line,
                'word_index': 0,  # Start of line for vertical movement
                'line_text': lines[target_line]
            }
        
        elif direction == 'd':  # below
            target_line = current_line + distance
            if target_line >= len(lines):
                return None
            return {
                'line': target_line,
                'word_index': 0,  # Start of line for vertical movement
                'line_text': lines[target_line]
            }
        
        return None
    
    def _extract_content_enhanced(self, text, target_pos, extract_type, extract_count, flexible):
        """
        Extract content using enhanced extraction with zero-count and flexible modes.
        
        NEW FEATURES:
        - Zero-count extraction: wd0 = until end of line, ln0 = until end of document
        - Flexible mode: skip line breaks and formatting inconsistencies
        
        Args:
            text (str): Source text
            target_pos (dict): Where to extract from
            extract_type (str): 'wd', 'ln', 'nb'
            extract_count (int): How many to extract (0 = until end)
            flexible (bool): Whether to use flexible extraction
            
        Returns:
            str or None: Extracted content
        """
        line_text = target_pos['line_text']
        word_idx = target_pos['word_index']
        
        if not line_text.strip():
            return None
        
        words = line_text.split()
        
        if extract_type == 'ln':
            return self._extract_lines(text, target_pos, extract_count, flexible)
        elif extract_type == 'wd':
            return self._extract_words(words, word_idx, extract_count, flexible)
        elif extract_type == 'nb':
            return self._extract_numbers(words, word_idx, extract_count, flexible)
        
        return None
    
    def _extract_lines(self, text, target_pos, count, flexible):
        """Extract lines with zero-count and flexible support."""
        lines = text.split('\n')
        start_line = target_pos['line']
        
        if start_line >= len(lines):
            return None
        
        if count == 0:
            # Extract until end of document
            remaining_lines = lines[start_line:]
            if flexible:
                # Join with spaces, collapse whitespace
                result = ' '.join(' '.join(line.split()) for line in remaining_lines if line.strip())
                return result if result else None
            else:
                return '\n'.join(remaining_lines)
        else:
            # Extract specific number of lines
            end_line = min(start_line + count, len(lines))
            selected_lines = lines[start_line:end_line]
            
            if flexible:
                # Join with spaces, clean up formatting
                result = ' '.join(' '.join(line.split()) for line in selected_lines if line.strip())
                return result if result else None
            else:
                return '\n'.join(selected_lines)
    
    def _extract_words(self, words, word_idx, count, flexible):
        """Extract words with zero-count and flexible support."""
        if word_idx >= len(words):
            return None
        
        if count == 0:
            # Extract until end of line
            remaining_words = words[word_idx:]
            if not remaining_words:
                return None
            
            result = ' '.join(remaining_words)
            if flexible:
                # Normalize whitespace, remove line artifacts
                result = ' '.join(result.split())
            
            return result
        else:
            # Extract specific number of words
            end_idx = min(word_idx + count, len(words))
            selected_words = words[word_idx:end_idx]
            
            if not selected_words:
                return None
            
            result = ' '.join(selected_words)
            if flexible:
                # Clean up formatting artifacts
                result = ' '.join(result.split())
            
            return result
    
    def _extract_numbers(self, words, word_idx, count, flexible):
        """Extract numbers with zero-count and flexible support."""
        if word_idx >= len(words):
            return None
        
        found_numbers = []
        
        # Search for numbers starting from target position
        for i in range(word_idx, len(words)):
            word = words[i]
            
            # Find number in current word
            if flexible:
                # Flexible mode: extract any numeric content
                number_match = re.search(r'[\d.,]+', word)
            else:
                # Strict mode: use existing pattern
                number_match = self.number_pattern.search(word)
            
            if number_match:
                found_numbers.append(number_match.group())
                
                # Check if we have enough numbers
                if count > 0 and len(found_numbers) >= count:
                    break
            elif count == 0:
                # For nb0, stop at first non-numeric word
                break
        
        if not found_numbers:
            return None
        
        if count == 0:
            # Return all numbers found until non-numeric
            return ' '.join(found_numbers)
        else:
            # Return specific count
            return ' '.join(found_numbers[:count])
    
    # Legacy methods maintained for backward compatibility
    def _calculate_target_position(self, text, keyword_pos, direction, distance):
        """Legacy method - delegates to new chained movement logic."""
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
        """Legacy method - delegates to new enhanced extraction."""
        type_map = {
            'word': ('wd', 1),
            'text': ('wd', 0),
            'line': ('ln', 1), 
            'number': ('nb', 1)
        }
        
        compact_type, count = type_map.get(extract_type, ('wd', 1))
        return self._extract_content_enhanced(text, target_pos, compact_type, count, False)
    
    # Existing methods preserved unchanged
    def extract_multiple_patterns(self, text, patterns):
        """Extract multiple patterns from the same text."""
        results = []
        for pattern in patterns:
            result = self.extract_pattern(text, pattern)
            results.append(result)
        return results
    
    def find_all_keyword_matches(self, text, keyword):
        """Find all occurrences of a keyword in the text."""
        matches = []
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            words = line.split()
            for word_idx, word in enumerate(words):
                if keyword.lower() in word.lower():
                    matches.append({
                        'line': line_idx,
                        'word_index': word_idx,
                        'word': word,
                        'line_text': line
                    })
        
        return matches
    
    def debug_extraction(self, text, pattern):
        """Debug helper to show the extraction process step by step."""
        keyword = pattern['keyword']
        
        # Find keyword
        keyword_pos = self._find_keyword_position(text, keyword)
        if keyword_pos is None:
            return {
                'success': False,
                'error': f"Keyword '{keyword}' not found",
                'keyword_matches': self.find_all_keyword_matches(text, keyword)
            }
        
        # Handle both legacy and new pattern formats
        if 'movements' in pattern:
            movements = pattern['movements']
            extract_type = pattern['extract_type']
            extract_count = pattern.get('extract_count', 1)
            flexible = pattern.get('flexible', False)
        else:
            # Legacy format
            direction = pattern['direction']
            distance = pattern['distance']
            legacy_type = pattern['extract_type']
            
            direction_map = {
                'above': 'u', 'below': 'd',
                'left': 'l', 'right': 'r'
            }
            
            movements = [(direction_map[direction], distance)] if direction in direction_map and distance > 0 else []
            
            type_map = {
                'word': ('wd', 1),
                'text': ('wd', 0),
                'line': ('ln', 1),
                'number': ('nb', 1)
            }
            extract_type, extract_count = type_map.get(legacy_type, ('wd', 1))
            flexible = False
        
        # Calculate target
        target_pos = self._calculate_target_position_chained(text, keyword_pos, movements)
        if target_pos is None:
            return {
                'success': False,
                'error': f"Target position out of range",
                'keyword_pos': keyword_pos,
                'movements': movements
            }
        
        # Extract content
        result = self._extract_content_enhanced(text, target_pos, extract_type, extract_count, flexible)
        
        return {
            'success': True,
            'keyword_pos': keyword_pos,
            'target_pos': target_pos,
            'movements': movements,
            'extract_type': extract_type,
            'extract_count': extract_count,
            'flexible': flexible,
            'extracted': result,
            'pattern': pattern
        }


# End of file #
