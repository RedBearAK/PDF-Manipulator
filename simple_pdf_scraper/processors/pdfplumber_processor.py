"""
PDFPlumber processor with center-distance filtering for spurious spaces.
File: simple_pdf_scraper/processors/pdfplumber_processor.py

Uses character center positions to identify and remove spatially
impossible space characters, and add missing spaces where needed.
"""

import sys

from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from simple_pdf_scraper.processors.base import PDFProcessor


class PDFPlumberProcessor(PDFProcessor):
    """
    PDF processor using center-distance filtering for spurious spaces.
    
    Analyzes character center positions to remove space characters
    that are positioned too close to other characters, and adds
    missing spaces where characters are far apart.
    """
    
    def __init__(self, 
                 min_space_ratio=1.3, 
                 add_space_ratio=1.1,  # Empirically tested optimal value
                 add_tab_ratio=1.3,    # Empirically tested optimal value  
                 line_tolerance=2.0,
                 space_char=' ',
                 tab_char='\t',
                 min_space_distance=None,
                 add_space_distance=None):
        """
        Initialize the processor with adaptive or fixed spacing thresholds.
        
        Args:
            min_space_ratio (float): Minimum ratio of char spacing to keep spaces (adaptive mode)
            add_space_ratio (float): Ratio threshold to add missing spaces (adaptive mode)
            add_tab_ratio (float): Ratio threshold to add tabs for structural boundaries (adaptive mode)
            line_tolerance (float): Y-coordinate tolerance for same line grouping
            space_char (str): Character to insert for normal gaps (default: space)
            tab_char (str): Character to insert for large gaps (default: tab)
            min_space_distance (float): Fixed minimum distance (legacy, overrides adaptive)
            add_space_distance (float): Fixed distance threshold (legacy, overrides adaptive)
            
        Note: 
            Default ratios (1.1× and 1.3×) are empirically tested on real-world problematic PDFs:
            - add_space_ratio=1.1 prevents over-insertion while catching concatenated text
            - add_tab_ratio=1.3 creates structural boundaries for Excel "Text to Columns"  
            - Both values automatically adapt to any font size
        """
        if pdfplumber is None:
            raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
        
        # Support both adaptive (ratio-based) and legacy (fixed) modes
        self.adaptive_mode = min_space_distance is None and add_space_distance is None
        
        if self.adaptive_mode:
            # Use font-size-aware adaptive mode (recommended)
            self.min_space_ratio = min_space_ratio
            self.add_space_ratio = add_space_ratio
            self.add_tab_ratio = add_tab_ratio
        else:
            # Use legacy fixed thresholds (for backward compatibility)
            self.min_space_distance = min_space_distance or 6.0
            self.add_space_distance = add_space_distance or 5.3  # 1.1× for 4.8pt spacing
            self.add_tab_distance = 6.2  # 1.3× for 4.8pt spacing
        
        self.line_tolerance = line_tolerance
        self.space_char = space_char
        self.tab_char = tab_char
    
    def extract_pages(self, pdf_path):
        """Extract text from all pages using center-distance filtering."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        pages_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = self._extract_page_with_filtering(page)
                        pages_text.append(text)
                    except Exception as page_error:
                        pages_text.append("")
                        print(f"Warning: Failed to extract text from page {page_num + 1}: {page_error}", file=sys.stderr)
        
        except Exception as e:
            # Handle potential encryption or other PDF access issues
            error_msg = str(e).lower()
            if 'password' in error_msg or 'encrypted' in error_msg or 'decrypt' in error_msg:
                raise Exception(f"PDF {pdf_path} appears to be password protected and cannot be processed")
            elif 'damaged' in error_msg or 'corrupt' in error_msg:
                raise Exception(f"PDF {pdf_path} appears to be corrupted")
            else:
                raise Exception(f"Error reading PDF {pdf_path}: {e}")
        
        return pages_text
    
    def extract_page(self, pdf_path, page_number):
        """Extract text from a specific page using center-distance filtering."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_number < 1 or page_number > len(pdf.pages):
                    raise IndexError(f"Page {page_number} out of range (1-{len(pdf.pages)})")
                
                page = pdf.pages[page_number - 1]  # Convert to 0-based
                return self._extract_page_with_filtering(page)
                
        except (IndexError, FileNotFoundError):
            raise
        except Exception as e:
            # Handle potential encryption or other PDF access issues
            error_msg = str(e).lower()
            if 'password' in error_msg or 'encrypted' in error_msg or 'decrypt' in error_msg:
                raise Exception(f"PDF {pdf_path} appears to be password protected and cannot be processed")
            else:
                raise Exception(f"Error reading page {page_number} from PDF {pdf_path}: {e}")
    
    def get_page_count(self, pdf_path):
        """Get page count using pdfplumber."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
                
        except Exception as e:
            # Handle potential encryption or other PDF access issues
            error_msg = str(e).lower()
            if 'password' in error_msg or 'encrypted' in error_msg or 'decrypt' in error_msg:
                raise Exception(f"PDF {pdf_path} appears to be password protected and cannot be processed")
            else:
                raise Exception(f"Error reading PDF {pdf_path}: {e}")
    
    def validate_pdf(self, pdf_path):
        """
        Check if a file is a valid PDF that can be processed with pdfplumber.
        
        Returns:
            dict: Validation result with 'valid' (bool), 'error' (str), and 'info' (dict)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return {
                'valid': False,
                'error': 'File does not exist',
                'info': {}
            }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                info = {
                    'page_count': len(pdf.pages),
                    'processor': 'pdfplumber'
                }
                
                # Try to extract characters from first page to test readability
                if len(pdf.pages) > 0:
                    try:
                        chars = pdf.pages[0].chars
                        if not chars:
                            return {
                                'valid': False,
                                'error': 'No extractable text found',
                                'info': info
                            }
                    except Exception as extract_error:
                        # Check if this looks like an encryption error
                        error_msg = str(extract_error).lower()
                        if 'password' in error_msg or 'encrypted' in error_msg or 'decrypt' in error_msg:
                            return {
                                'valid': False,
                                'error': 'PDF appears to be password protected',
                                'info': info
                            }
                        else:
                            return {
                                'valid': False,
                                'error': f'Cannot extract characters: {extract_error}',
                                'info': info
                            }
                
                return {
                    'valid': True,
                    'error': None,
                    'info': info
                }
                
        except Exception as e:
            # Handle potential encryption or other PDF access issues
            error_msg = str(e).lower()
            if 'password' in error_msg or 'encrypted' in error_msg or 'decrypt' in error_msg:
                error = "PDF appears to be password protected"
            elif 'damaged' in error_msg or 'corrupt' in error_msg:
                error = "PDF appears to be corrupted"
            else:
                error = f'pdfplumber processing error: {e}'
            
            return {
                'valid': False,
                'error': error,
                'info': {}
            }
    
    def _extract_page_with_filtering(self, page):
        """Extract text from a page using font-aware or fixed center-distance filtering."""
        # Get all characters with positions
        chars = page.chars
        if not chars:
            return ""
        
        # Group characters by line (same Y coordinate within tolerance)
        lines = self._group_characters_by_line(chars)
        
        # Process each line with appropriate filtering mode
        processed_lines = []
        for line_chars in lines:
            if self.adaptive_mode:
                line_text = self._process_line_with_adaptive_filtering(line_chars)
            else:
                line_text = self._process_line_with_fixed_filtering(line_chars)
                
            if line_text.strip():  # Only keep non-empty lines
                processed_lines.append(line_text)
        
        return '\n'.join(processed_lines)
    
    def _group_characters_by_line(self, chars):
        """Group characters into lines based on Y coordinate."""
        if not chars:
            return []
        
        # Sort by Y coordinate (top to bottom), then X coordinate (left to right)
        sorted_chars = sorted(chars, key=lambda c: (-c['y1'], c['x0']))
        
        lines = []
        current_line = [sorted_chars[0]]
        current_y = sorted_chars[0]['y1']
        
        for char in sorted_chars[1:]:
            if abs(char['y1'] - current_y) <= self.line_tolerance:
                # Same line - add to current group
                current_line.append(char)
            else:
                # New line - start new group
                lines.append(current_line)
                current_line = [char]
                current_y = char['y1']
        
        # Don't forget the last line
        if current_line:
            lines.append(current_line)
        
        # Sort characters within each line by X coordinate
        for line in lines:
            line.sort(key=lambda c: c['x0'])
        
        return lines
    
    def _process_line_with_adaptive_filtering(self, line_chars):
        """Process a line using adaptive font-size-aware center-distance filtering."""
        if not line_chars:
            return ""
        
        # Calculate character centers and typical spacing
        char_data = []
        for char in line_chars:
            center = (char['x0'] + char['x1']) / 2
            char_data.append({
                'text': char['text'],
                'center': center,
                'is_space': char['text'] == ' '
            })
        
        # Calculate average character spacing for this line
        avg_char_spacing = self._calculate_average_character_spacing(char_data)
        
        # Calculate adaptive thresholds based on character spacing
        min_space_distance = avg_char_spacing * self.min_space_ratio
        add_space_distance = avg_char_spacing * self.add_space_ratio
        add_tab_distance = avg_char_spacing * self.add_tab_ratio
        
        # Apply center-distance filtering with adaptive thresholds
        return self._apply_enhanced_center_distance_filtering(
            char_data, min_space_distance, add_space_distance, add_tab_distance
        )
    
    def _process_line_with_fixed_filtering(self, line_chars):
        """Process a line using fixed center-distance filtering (legacy mode)."""
        if not line_chars:
            return ""
        
        # Calculate character centers
        char_data = []
        for char in line_chars:
            center = (char['x0'] + char['x1']) / 2
            char_data.append({
                'text': char['text'],
                'center': center,
                'is_space': char['text'] == ' '
            })
        
        # Apply center-distance filtering with fixed thresholds
        return self._apply_center_distance_filtering(char_data, self.min_space_distance, self.add_space_distance)
    
    def _calculate_average_character_spacing(self, char_data):
        """Calculate the average spacing between adjacent non-space characters."""
        non_space_chars = [c for c in char_data if not c['is_space']]
        
        if len(non_space_chars) < 2:
            return 4.8  # Fallback to typical 12pt font spacing
        
        # Calculate spacings between adjacent non-space characters
        spacings = []
        for i in range(1, len(non_space_chars)):
            spacing = non_space_chars[i]['center'] - non_space_chars[i-1]['center']
            # Only include reasonable spacings (filter out huge gaps)
            if spacing > 0 and spacing < 50:  # Reasonable character spacing range
                spacings.append(spacing)
        
        if not spacings:
            return 4.8  # Fallback
        
        # Use median to avoid being skewed by outliers
        spacings.sort()
        mid = len(spacings) // 2
        if len(spacings) % 2 == 0:
            return (spacings[mid-1] + spacings[mid]) / 2
        else:
            return spacings[mid]
    
    def _apply_center_distance_filtering(self, char_data, min_space_distance, add_space_distance):
        """Apply center-distance filtering with specified thresholds."""
        result_chars = []
        i = 0
        
        while i < len(char_data):
            current_char = char_data[i]
            
            if current_char['is_space']:
                # This is a space character - decide whether to keep it
                if self._should_keep_space(char_data, i, min_space_distance):
                    result_chars.append(' ')
            else:
                # This is a non-space character - always add it
                result_chars.append(current_char['text'])
                
                # Check if we need to add a space after this character
                if self._should_add_space_after(char_data, i, add_space_distance):
                    result_chars.append(' ')
            
            i += 1
        
        return ''.join(result_chars)
    
    def _apply_enhanced_center_distance_filtering(self, char_data, min_space_distance, add_space_distance, add_tab_distance):
        """Apply enhanced center-distance filtering with tab insertion."""
        result_chars = []
        i = 0
        
        while i < len(char_data):
            current_char = char_data[i]
            
            if current_char['is_space']:
                # This is a space character - decide whether to keep it
                if self._should_keep_space(char_data, i, min_space_distance):
                    result_chars.append(self.space_char)
            else:
                # This is a non-space character - always add it
                result_chars.append(current_char['text'])
                
                # Check what separator (if any) to add after this character
                separator = self._get_separator_to_add(char_data, i, add_space_distance, add_tab_distance)
                if separator:
                    result_chars.append(separator)
            
            i += 1
        
        return ''.join(result_chars)
    
    def _should_keep_space(self, char_data, space_index, min_space_distance):
        """Determine if a space should be kept based on adjacent character distances."""
        # Find the non-space characters before and after this space
        prev_char = None
        next_char = None
        
        # Look backwards for previous non-space character
        for i in range(space_index - 1, -1, -1):
            if not char_data[i]['is_space']:
                prev_char = char_data[i]
                break
        
        # Look forwards for next non-space character
        for i in range(space_index + 1, len(char_data)):
            if not char_data[i]['is_space']:
                next_char = char_data[i]
                break
        
        # If we can't find both adjacent characters, keep the space
        if prev_char is None or next_char is None:
            return True
        
        # Calculate center-to-center distance between adjacent non-space characters
        distance = next_char['center'] - prev_char['center']
        
        # Keep space if there's enough distance between the adjacent characters
        return distance >= min_space_distance
    
    def _should_add_space_after(self, char_data, char_index, add_space_distance):
        """Determine if a space should be added after a character."""
        # Don't add space after the last character
        if char_index >= len(char_data) - 1:
            return False
        
        current_char = char_data[char_index]
        next_char = char_data[char_index + 1]
        
        # Don't add space if next character is already a space
        if next_char['is_space']:
            return False
        
        # Calculate center-to-center distance
        distance = next_char['center'] - current_char['center']
        
        # Add space if distance is large enough
        return distance >= add_space_distance
    
    def _get_separator_to_add(self, char_data, char_index, add_space_distance, add_tab_distance):
        """Determine what separator (if any) should be added after a character."""
        # Don't add separator after the last character
        if char_index >= len(char_data) - 1:
            return None
        
        current_char = char_data[char_index]
        next_char = char_data[char_index + 1]
        
        # Don't add separator if next character is already a space
        if next_char['is_space']:
            return None
        
        # Calculate center-to-center distance
        distance = next_char['center'] - current_char['center']
        
        # Determine appropriate separator based on distance
        if distance >= add_tab_distance:
            return self.tab_char  # Large gap = structural boundary
        elif distance >= add_space_distance:
            return self.space_char  # Medium gap = missing space
        else:
            return None  # Small gap = no separator needed
    
    def get_processor_info(self):
        """Return information about this processor."""
        if self.adaptive_mode:
            return {
                'name': 'PDFPlumber-Enhanced-Adaptive',
                'library': 'pdfplumber',
                'features': ['character_positioning', 'font_size_aware', 'adaptive_thresholds', 'tab_insertion'],
                'best_for': 'mixed_font_sizes_and_structural_boundaries',
                'mode': 'adaptive',
                'min_space_ratio': self.min_space_ratio,
                'add_space_ratio': self.add_space_ratio,
                'add_tab_ratio': self.add_tab_ratio,
                'space_char': repr(self.space_char),
                'tab_char': repr(self.tab_char)
            }
        else:
            return {
                'name': 'PDFPlumber-Enhanced-Fixed',
                'library': 'pdfplumber',
                'features': ['character_positioning', 'center_distance_filtering', 'tab_insertion'],
                'best_for': 'consistent_font_pdfs_with_structural_boundaries',
                'mode': 'fixed',
                'min_space_distance': self.min_space_distance,
                'add_space_distance': self.add_space_distance,
                'add_tab_distance': self.add_tab_distance,
                'space_char': repr(self.space_char),
                'tab_char': repr(self.tab_char)
            }

# End of file #
