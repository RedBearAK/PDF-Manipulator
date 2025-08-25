#!/usr/bin/env python3
"""
Debug the actual order text gets assembled by pdfplumber.
File: tests/debug_text_assembly_order.py

Shows characters in the order they actually appear in extracted text,
not in PDF internal order.
"""

import sys

from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not available")
    sys.exit(1)


def debug_actual_text_order(pdf_file):
    """Debug the actual text assembly order."""
    
    print(f"DEBUGGING ACTUAL TEXT ORDER: {Path(pdf_file).name}")
    print("=" * 60)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            
            # Get the actual extracted text
            extracted_text = page.extract_text()
            
            # Find the problematic line
            lines = extracted_text.splitlines()
            problem_line = None
            line_index = None
            
            for i, line in enumerate(lines):
                if "LINEAGE TRANSPORTATION LLC" in line:
                    problem_line = line
                    line_index = i
                    break
            
            if not problem_line:
                print("Problem line not found")
                return
            
            print(f"Problem line {line_index}: '{problem_line}'")
            print(f"Length: {len(problem_line)} characters")
            print()
            
            # Show each character in the actual extracted text
            print("Characters in extracted text order:")
            print("-" * 40)
            
            for i, char in enumerate(problem_line):
                print(f"  {i:2}: '{char}' ({ord(char):3}) {repr(char)}")
            
            # Now try to correlate with PDF character positions
            print(f"\nTrying to correlate with PDF positions...")
            
            # Get all characters and sort by reading order (Y then X)
            chars = page.chars
            sorted_chars = sorted(chars, key=lambda c: (-c['y0'], c['x0']))
            
            # Find characters in the problematic line (same Y coordinate)
            problem_y = None
            problem_chars = []
            
            for char in sorted_chars:
                if char['text'] in problem_line:
                    if problem_y is None:
                        problem_y = char['y0']
                    
                    # Include chars within 2 points of the line Y coordinate
                    if abs(char['y0'] - problem_y) < 2.0:
                        problem_chars.append(char)
            
            # Sort problem chars by X coordinate (reading order)
            problem_chars.sort(key=lambda c: c['x0'])
            
            print(f"\nCharacters sorted by reading order (X coordinate):")
            print("-" * 50)
            
            for i, char in enumerate(problem_chars):
                x = char['x0']
                text = char['text']
                print(f"  {i:2}: x={x:6.1f} '{text}' ({ord(text):3}) {repr(text)}")
            
            # Try to build the text as pdfplumber would
            reading_order_text = ''.join(char['text'] for char in problem_chars)
            
            print(f"\nText built from reading order: '{reading_order_text}'")
            print(f"Actual extracted text:          '{problem_line}'")
            print(f"Match: {reading_order_text == problem_line}")
            
    except Exception as e:
        print(f"Error: {e}")


def debug_character_overlaps(pdf_file):
    """Look for overlapping or out-of-order characters."""
    
    print(f"\nDEBUGGING CHARACTER OVERLAPS:")
    print("=" * 40)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            chars = page.chars
            
            # Focus on date area around y=724
            date_chars = [c for c in chars if 723 < c['y0'] < 725]
            date_chars.sort(key=lambda c: c['x0'])
            
            print(f"Found {len(date_chars)} characters in date area:")
            
            for i, char in enumerate(date_chars):
                x0 = char['x0']
                x1 = char.get('x1', x0 + char.get('width', 0))
                text = char['text']
                
                print(f"  {i:2}: x={x0:6.1f}-{x1:6.1f} '{text}'")
                
                # Check for overlaps
                if i > 0:
                    prev_char = date_chars[i-1]
                    prev_x1 = prev_char.get('x1', prev_char['x0'] + prev_char.get('width', 0))
                    
                    if x0 < prev_x1:
                        overlap = prev_x1 - x0
                        print(f"       *** OVERLAP: {overlap:.1f} points with previous character ***")
            
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main debugging function."""
    print("Text Assembly Order Debugging Tool")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python debug_text_assembly_order.py <pdf_file>")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    debug_actual_text_order(pdf_file)
    debug_character_overlaps(pdf_file)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
