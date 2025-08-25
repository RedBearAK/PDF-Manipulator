#!/usr/bin/env python3
"""
Enhanced adaptive filtering test with configurable insertion characters.
File: tests/test_enhanced_adaptive_filtering.py

Tests improved adaptive filtering with separate thresholds for space vs tab insertion
and shows more comprehensive results across many lines.
"""

import sys

from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def test_enhanced_adaptive_filtering(pdf_path, max_lines=20):
    """Test enhanced adaptive filtering with tab support."""
    
    if pdfplumber is None:
        print("Error: pdfplumber not available")
        return False
    
    print("ENHANCED ADAPTIVE FILTERING TEST")
    print("=" * 70)
    print(f"Testing file: {Path(pdf_path).name}")
    print(f"Showing first {max_lines} lines")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Test first page
            page = pdf.pages[0]
            
            # Get all characters with positions
            chars = page.chars
            
            print(f"Found {len(chars)} characters")
            
            # Group characters by line
            lines = group_characters_by_line(chars, line_tolerance=2.0)
            
            print(f"Grouped into {len(lines)} lines")
            print()
            
            # Process each line with enhanced adaptive filtering
            for line_num, line_chars in enumerate(lines[:max_lines], 1):
                print(f"LINE {line_num}:")
                
                # Show original text
                original_text = ''.join(char['text'] for char in line_chars)
                print(f"  Original: '{original_text}'")
                
                # Calculate character data
                char_data = []
                for char in line_chars:
                    center = (char['x0'] + char['x1']) / 2
                    char_data.append({
                        'text': char['text'],
                        'center': center,
                        'is_space': char['text'] == ' '
                    })
                
                # Calculate adaptive parameters for this line
                avg_char_spacing = calculate_average_character_spacing(char_data)
                
                # Enhanced thresholds (much more aggressive)
                min_space_distance = avg_char_spacing * 1.3  # Remove spurious spaces
                # add_space_distance = avg_char_spacing * 0.54  # Add missing spaces (0.9× space width)  
                add_space_distance = avg_char_spacing * 1.1
                # add_tab_distance = avg_char_spacing * 1.20    # Add tabs (2.0× space width)
                add_tab_distance = avg_char_spacing * 1.3
                
                print(f"  Font analysis:")
                print(f"    Avg char spacing: {avg_char_spacing:.1f} pts")
                print(f"    Min space threshold: {min_space_distance:.1f} pts (remove spurious)")
                print(f"    Add space threshold: {add_space_distance:.1f} pts (0.9× space width)")
                print(f"    Add tab threshold: {add_tab_distance:.1f} pts (2.0× space width)")
                
                # Apply enhanced filtering with different insertion characters
                space_filtered = apply_enhanced_adaptive_filtering(
                    char_data, 
                    min_space_distance=min_space_distance,
                    add_space_distance=add_space_distance,
                    add_tab_distance=add_tab_distance,
                    space_char=' ',
                    tab_char='\t'
                )
                
                # Also test with custom separator
                pipe_filtered = apply_enhanced_adaptive_filtering(
                    char_data, 
                    min_space_distance=min_space_distance,
                    add_space_distance=add_space_distance,
                    add_tab_distance=add_tab_distance,
                    space_char=' ',
                    tab_char='|'  # Use pipe for visual clarity in testing
                )
                
                print(f"  Space+Tab: '{space_filtered}'")
                print(f"  Space+Pipe: '{pipe_filtered}'")
                
                # Show effectiveness
                if original_text != space_filtered:
                    print(f"  >>> CHANGED")
                else:
                    print(f"  >>> NO CHANGE NEEDED")
                print()
        
        return True
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False


def group_characters_by_line(chars, line_tolerance=2.0):
    """Group characters into lines based on Y coordinate."""
    if not chars:
        return []
    
    # Sort by Y coordinate (top to bottom), then X coordinate (left to right)
    sorted_chars = sorted(chars, key=lambda c: (-c['y1'], c['x0']))
    
    lines = []
    current_line = [sorted_chars[0]]
    current_y = sorted_chars[0]['y1']
    
    for char in sorted_chars[1:]:
        if abs(char['y1'] - current_y) <= line_tolerance:
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


def calculate_average_character_spacing(char_data):
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


def apply_enhanced_adaptive_filtering(char_data, min_space_distance, add_space_distance, 
                                     add_tab_distance, space_char=' ', tab_char='\t'):
    """Apply enhanced adaptive filtering with configurable insertion characters."""
    if not char_data:
        return ""
    
    result_chars = []
    i = 0
    
    while i < len(char_data):
        current_char = char_data[i]
        
        if current_char['is_space']:
            # This is a space character - decide whether to keep it
            if should_keep_space_enhanced(char_data, i, min_space_distance):
                result_chars.append(space_char)
        else:
            # This is a non-space character - always add it
            result_chars.append(current_char['text'])
            
            # Check if we need to add a separator after this character
            separator = get_separator_to_add(char_data, i, add_space_distance, 
                                           add_tab_distance, space_char, tab_char)
            if separator:
                result_chars.append(separator)
        
        i += 1
    
    return ''.join(result_chars)


def should_keep_space_enhanced(char_data, space_index, min_space_distance):
    """Determine if a space should be kept using adaptive threshold."""
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


def get_separator_to_add(char_data, char_index, add_space_distance, 
                        add_tab_distance, space_char, tab_char):
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
        return tab_char  # Large gap = structural boundary
    elif distance >= add_space_distance:
        return space_char  # Medium gap = missing space
    else:
        return None  # Small gap = no separator needed


def main():
    """Main test runner."""
    if len(sys.argv) not in [2, 3]:
        print("Usage: python test_enhanced_adaptive_filtering.py <pdf_file> [max_lines]")
        return 1
    
    pdf_file = sys.argv[1]
    max_lines = int(sys.argv[2]) if len(sys.argv) == 3 else 20
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    success = test_enhanced_adaptive_filtering(pdf_file, max_lines)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

# End of file #
