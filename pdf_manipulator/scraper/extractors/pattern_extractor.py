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
        
        Enhanced to handle multi-word keywords and punctuation.
        
        Args:
            text: Source text to search
            keyword: Keyword to find (can be multiple words)
            
        Returns:
            dict or None: Position info with line, word_index, line_text
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

    def _calculate_target_position_chained(self, text, keyword_pos, movements):
        """
        Calculate target position using chained movements.
        
        NEW: Supports multiple movements in sequence: [('u', 1), ('r', 2)]
        
        Args:
            text: Source text
            keyword_pos: Starting position from keyword
            movements: List of (direction, distance) tuples
            
        Returns:
            dict or None: Final target position
        """
        if not keyword_pos:
            return None
        
        lines = text.split('\n')
        current_line = keyword_pos['line']
        current_word = keyword_pos['word_index']
        
        # Handle zero movements (extract the word AFTER the keyword)
        if not movements:
            # For zero movement, extract the word after the keyword
            words_in_line = len(lines[current_line].split())
            if current_word + 1 < words_in_line:
                return {
                    'line': current_line,
                    'word_index': current_word + 1,
                    'line_text': lines[current_line]
                }
            else:
                # If no word after keyword on same line, return None
                return None
        
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
            lines: All text lines
            current_line: Current line index
            current_word: Current word index within line
            direction: 'u', 'd', 'l', 'r'
            distance: How far to move
            
        Returns:
            dict or None: New position or None if out of bounds
        """
        if current_line >= len(lines):
            return None
        
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
            words_in_line = len(lines[current_line].split()) if current_line < len(lines) else 0
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
            
            # Skip empty lines when moving up
            lines_skipped = 0
            check_line = current_line - 1
            while lines_skipped < distance and check_line >= 0:
                if lines[check_line].strip():  # Non-empty line
                    lines_skipped += 1
                    if lines_skipped == distance:
                        target_line = check_line
                        break
                check_line -= 1
            
            if target_line < 0 or lines_skipped < distance:
                return None
            return {
                'line': target_line,
                'word_index': 0,  # Start of line for vertical movement
                'line_text': lines[target_line]
            }
        
        elif direction == 'd':  # below
            target_line = current_line + distance
            
            # Skip empty lines when moving down
            lines_skipped = 0
            check_line = current_line + 1
            while lines_skipped < distance and check_line < len(lines):
                if lines[check_line].strip():  # Non-empty line
                    lines_skipped += 1
                    if lines_skipped == distance:
                        target_line = check_line
                        break
                check_line += 1
            
            if target_line >= len(lines) or lines_skipped < distance:
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
        
        NEW: Supports zero-count extraction (wd0, ln0, nb0) and flexible mode
        
        Args:
            text: Source text
            target_pos: Position to extract from
            extract_type: 'wd', 'ln', 'nb'
            extract_count: Number to extract (0 = until end)
            flexible: Skip line breaks and formatting
            
        Returns:
            str or None: Extracted content
        """
        if not target_pos or target_pos['line'] >= len(text.split('\n')):
            return None
        
        lines = text.split('\n')
        line_idx = target_pos['line']
        word_idx = target_pos['word_index']
        
        if extract_type == 'wd':  # words
            return self._extract_words(lines, line_idx, word_idx, extract_count, flexible)
        elif extract_type == 'ln':  # lines
            return self._extract_lines(lines, line_idx, extract_count, flexible)
        elif extract_type == 'nb':  # numbers
            return self._extract_numbers(lines, line_idx, word_idx, extract_count, flexible)
        
        return None

    def _extract_words(self, lines, line_idx, word_idx, count, flexible):
        """Extract words from target position."""
        if line_idx >= len(lines):
            return None
        
        words = lines[line_idx].split()
        
        if word_idx >= len(words):
            return None
        
        if count == 0:  # Extract until end of line
            result_words = words[word_idx:]
            return ' '.join(result_words) if result_words else None
        
        # Extract specific number of words starting from word_idx
        end_idx = min(word_idx + count, len(words))
        result_words = words[word_idx:end_idx]
        
        if flexible and len(result_words) < count:
            # Try to get more words from next lines
            remaining = count - len(result_words)
            next_line = line_idx + 1
            
            while remaining > 0 and next_line < len(lines):
                next_words = lines[next_line].split()
                take = min(remaining, len(next_words))
                if take > 0:
                    result_words.extend(next_words[:take])
                    remaining -= take
                next_line += 1
        
        return ' '.join(result_words) if result_words else None

    def _extract_lines(self, lines, line_idx, count, flexible):
        """Extract lines from target position."""
        if line_idx >= len(lines):
            return None
        
        if count == 0:  # Extract until end of document
            result_lines = lines[line_idx:]
            return '\n'.join(result_lines) if result_lines else None
        
        # Extract specific number of lines
        end_idx = min(line_idx + count, len(lines))
        result_lines = lines[line_idx:end_idx]
        
        return '\n'.join(result_lines) if result_lines else None

    def _extract_numbers(self, lines, line_idx, word_idx, count, flexible):
        """Extract numbers from target position."""
        if line_idx >= len(lines):
            return None
        
        words = lines[line_idx].split()
        
        if word_idx >= len(words):
            return None
        
        # Start collecting numbers from target position
        numbers = []
        current_line = line_idx
        current_word = word_idx
        
        while len(numbers) < count or count == 0:
            if current_line >= len(lines):
                break
            
            line_words = lines[current_line].split()
            
            # Start from current_word position, then 0 for subsequent lines
            start_word = current_word if current_line == line_idx else 0
            
            for i in range(start_word, len(line_words)):
                word = line_words[i]
                
                # Check if word contains numbers
                number_match = self.number_pattern.search(word)
                if number_match:
                    numbers.append(number_match.group())
                    if count > 0 and len(numbers) >= count:
                        break
                elif numbers and not flexible:
                    # Stop at first non-number if not flexible and we have numbers
                    break
            
            if count > 0 and len(numbers) >= count:
                break
            
            if not flexible and numbers:
                # In non-flexible mode, stop at end of line if we have numbers
                break
            
            # Move to next line
            current_line += 1
            current_word = 0
        
        return ' '.join(numbers) if numbers else None

    # LEGACY METHODS - preserved for backward compatibility
    def _calculate_target_position(self, text, keyword_pos, direction, distance):
        """Legacy method - delegates to new chained movement system."""
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
    
    # EXISTING METHODS - preserved unchanged
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
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        
        # If single word keyword
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
                            'line_text': line
                        })
        
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
                        matches.append({
                            'line': line_idx,
                            'word_index': word_idx + len(keyword_words) - 1,
                            'word': ' '.join(words[word_idx:word_idx + len(keyword_words)]),
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
