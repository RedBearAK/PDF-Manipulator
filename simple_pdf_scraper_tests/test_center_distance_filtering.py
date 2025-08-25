#!/usr/bin/env python3
"""
Test center-distance filtering for PDF text extraction.
File: tests/test_center_distance_filtering.py

Tests the approach of using character center positions to remove spurious 
spaces and add missing spaces based on spatial relationships.
"""

import sys

from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def test_center_distance_filtering(pdf_path):
    """Test center-distance filtering on a specific PDF."""
    
    if pdfplumber is None:
        print("Error: pdfplumber not available")
        return False
    
    print("CENTER DISTANCE FILTERING TEST")
    print("=" * 50)
    print(f"Testing file: {Path(pdf_path).name}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Test first page
            page = pdf.pages[0]
            
            # Get all characters with positions
            chars = page.chars
            
            print(f"Found {len(chars)} characters")
            
            # Group characters by line (same Y coordinate within tolerance)
            lines = group_characters_by_line(chars, line_tolerance=2.0)
            
            print(f"Grouped into {len(lines)} lines")
            
            # Process each line
            for line_num, line_chars in enumerate(lines[:5], 1):  # Show first 5 lines
                print(f"\nLINE {line_num}:")
                
                # Show original text
                original_text = ''.join(char['text'] for char in line_chars)
                print(f"  Original: '{original_text}'")
                
                # Apply center-distance filtering
                filtered_text = apply_center_distance_filtering(
                    line_chars, 
                    min_space_distance=6.0,
                    add_space_distance=15.0
                )
                print(f"  Filtered: '{filtered_text}'")
                
                # Show character positions for debugging
                if line_num == 3:  # Focus on the problematic line
                    print("  Character details:")
                    for i, char in enumerate(line_chars):
                        x0, x1 = char['x0'], char['x1']
                        center = (x0 + x1) / 2
                        text = repr(char['text'])
                        print(f"    {i:2}: center={center:6.1f} {text:4} (x={x0:.1f}-{x1:.1f})")
        
        return True
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False


def group_characters_by_line(chars, line_tolerance=2.0):
    """
    Group characters into lines based on Y coordinate.
    
    Args:
        chars (list): List of character dictionaries with x0, x1, y0, y1, text
        line_tolerance (float): Y-coordinate tolerance for grouping
        
    Returns:
        list: List of character groups (lines)
    """
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


def apply_center_distance_filtering(line_chars, min_space_distance=6.0, add_space_distance=15.0):
    """
    Apply center-distance filtering to remove spurious spaces and add missing ones.
    
    Args:
        line_chars (list): Characters in a line, sorted by X position
        min_space_distance (float): Minimum distance to keep a space
        add_space_distance (float): Distance threshold to add missing spaces
        
    Returns:
        str: Filtered text with proper spacing
    """
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
    
    # Process characters to build filtered text
    result_chars = []
    i = 0
    
    while i < len(char_data):
        current_char = char_data[i]
        
        if current_char['is_space']:
            # This is a space character - decide whether to keep it
            if should_keep_space(char_data, i, min_space_distance):
                result_chars.append(' ')
        else:
            # This is a non-space character - always add it
            result_chars.append(current_char['text'])
            
            # Check if we need to add a space after this character
            if should_add_space_after(char_data, i, add_space_distance):
                result_chars.append(' ')
        
        i += 1
    
    return ''.join(result_chars)


def should_keep_space(char_data, space_index, min_space_distance):
    """
    Determine if a space character should be kept based on adjacent character distances.
    
    Args:
        char_data (list): List of character data with centers
        space_index (int): Index of the space character
        min_space_distance (float): Minimum distance to keep space
        
    Returns:
        bool: True if space should be kept
    """
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


def should_add_space_after(char_data, char_index, add_space_distance):
    """
    Determine if a space should be added after a character.
    
    Args:
        char_data (list): List of character data with centers
        char_index (int): Index of current character
        add_space_distance (float): Distance threshold to add space
        
    Returns:
        bool: True if space should be added
    """
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


def main():
    """Main test runner."""
    if len(sys.argv) != 2:
        print("Usage: python test_center_distance_filtering.py <pdf_file>")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    success = test_center_distance_filtering(pdf_file)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

# End of file #
