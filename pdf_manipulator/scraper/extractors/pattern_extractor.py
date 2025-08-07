"""
Pattern-based text extraction with directional search capabilities.
"""

import re


class PatternExtractor:
    """
    Extract text based on patterns and directional rules.
    
    Supports finding text relative to keywords in various directions
    and extracting different types of content (words, numbers, lines).
    """
    
    def __init__(self):
        # Common number patterns for extraction
        self.number_pattern = re.compile(r'-?\d+(?:[.,]\d+)*')
        self.word_pattern = re.compile(r'\S+')
    
    def extract_pattern(self, text, pattern):
        """
        Extract text based on a pattern specification.
        
        Args:
            text (str): The source text to search
            pattern (dict): Pattern specification with keys:
                - keyword: Text to search for
                - direction: 'left', 'right', 'above', 'below'
                - distance: Number of words/lines to move
                - extract_type: 'word', 'number', 'line', 'text'
        
        Returns:
            str or None: Extracted text, or None if pattern not found
        """
        keyword = pattern['keyword']
        direction = pattern['direction']
        distance = pattern['distance']
        extract_type = pattern['extract_type']
        
        # Find keyword position
        keyword_pos = self._find_keyword_position(text, keyword)
        if keyword_pos is None:
            return None
        
        # Calculate target position based on direction
        target_pos = self._calculate_target_position(
            text, keyword_pos, direction, distance
        )
        if target_pos is None:
            return None
        
        # Extract the requested content type
        return self._extract_content(text, target_pos, extract_type)
    
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
                
                # Find which words the keyword spans
                words = line.split()
                char_pos = 0
                keyword_start_word = None
                keyword_end_word = None
                
                for word_idx, word in enumerate(words):
                    word_start = char_pos
                    word_end = char_pos + len(word)
                    
                    # Check if keyword starts in this word
                    if keyword_start_word is None and start_pos >= word_start and start_pos < word_end + 1:
                        keyword_start_word = word_idx
                    
                    # Check if keyword ends in this word  
                    if end_pos <= word_end + 1:  # +1 for space after word
                        keyword_end_word = word_idx
                        break
                    
                    char_pos = word_end + 1  # +1 for space
                
                if keyword_start_word is not None and keyword_end_word is not None:
                    return {
                        'line': line_idx,
                        'word_index': keyword_start_word,  # Where keyword starts
                        'char_start': start_pos,
                        'char_end': end_pos,
                        'line_text': line,
                        'keyword_end_word': keyword_end_word  # Where keyword ends
                    }
        
        return None
    
    def _calculate_target_position(self, text, keyword_pos, direction, distance):
        """
        Calculate the target position based on direction and distance.
        
        Returns:
            dict or None: Target position info
        """
        lines = text.split('\n')
        current_line = keyword_pos['line']
        current_word = keyword_pos['word_index']
        
        if direction == 'left':
            target_word = current_word - distance
            if target_word < 0:
                return None
            return {
                'line': current_line,
                'word_index': target_word,
                'line_text': lines[current_line]
            }
        
        elif direction == 'right':
            words_in_line = len(lines[current_line].split())
            # Use keyword_end_word if available (for multi-word keywords)
            keyword_end = keyword_pos.get('keyword_end_word', current_word)
            target_word = keyword_end + distance + 1  # +1 to move past the keyword
            if target_word >= words_in_line:
                return None
            return {
                'line': current_line,
                'word_index': target_word,
                'line_text': lines[current_line]
            }
        
        elif direction == 'above':
            target_line = current_line - distance
            if target_line < 0:
                return None
            return {
                'line': target_line,
                'word_index': 0,  # Start of line for above/below
                'line_text': lines[target_line]
            }
        
        elif direction == 'below':
            target_line = current_line + distance
            if target_line >= len(lines):
                return None
            return {
                'line': target_line,
                'word_index': 0,  # Start of line for above/below
                'line_text': lines[target_line]
            }
        
        return None
    
    def _extract_content(self, text, target_pos, extract_type):
        """
        Extract content from the target position based on extract type.
        
        Returns:
            str or None: Extracted content
        """
        line_text = target_pos['line_text']
        words = line_text.split()
        
        if not words:
            return None
        
        if extract_type == 'line':
            return line_text.strip()
        
        elif extract_type == 'word':
            word_idx = target_pos['word_index']
            if word_idx < len(words):
                return words[word_idx]
            return None
        
        elif extract_type == 'number':
            # Look for a number starting from the target position
            word_idx = target_pos['word_index']
            
            # Check current word and next few words for numbers
            for i in range(word_idx, min(word_idx + 3, len(words))):
                if i < len(words):
                    number_match = self.number_pattern.search(words[i])
                    if number_match:
                        return number_match.group()
            
            return None
        
        elif extract_type == 'text':
            # Extract remaining text from target position to end of line
            word_idx = target_pos['word_index']
            if word_idx < len(words):
                return ' '.join(words[word_idx:])
            return None
        
        return None
    
    def extract_multiple_patterns(self, text, patterns):
        """
        Extract multiple patterns from the same text.
        
        Args:
            text (str): Source text
            patterns (list): List of pattern specifications
            
        Returns:
            list: List of extracted results, None for failed extractions
        """
        results = []
        for pattern in patterns:
            result = self.extract_pattern(text, pattern)
            results.append(result)
        return results
    
    def find_all_keyword_matches(self, text, keyword):
        """
        Find all occurrences of a keyword in the text.
        
        Useful for debugging or when a keyword appears multiple times.
        
        Returns:
            list: List of position dictionaries
        """
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
        """
        Debug helper to show the extraction process step by step.
        
        Returns:
            dict: Debug information about the extraction process
        """
        keyword = pattern['keyword']
        
        # Find keyword
        keyword_pos = self._find_keyword_position(text, keyword)
        if keyword_pos is None:
            return {
                'success': False,
                'error': f"Keyword '{keyword}' not found",
                'keyword_matches': self.find_all_keyword_matches(text, keyword)
            }
        
        # Calculate target
        target_pos = self._calculate_target_position(
            text, keyword_pos, pattern['direction'], pattern['distance']
        )
        if target_pos is None:
            return {
                'success': False,
                'error': f"Target position out of range",
                'keyword_pos': keyword_pos,
                'direction': pattern['direction'],
                'distance': pattern['distance']
            }
        
        # Extract content
        result = self._extract_content(text, target_pos, pattern['extract_type'])
        
        return {
            'success': True,
            'keyword_pos': keyword_pos,
            'target_pos': target_pos,
            'extracted': result,
            'pattern': pattern
        }
