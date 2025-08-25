#!/usr/bin/env python3
"""
Debug character positions and gaps in PDFs.
File: tests/debug_character_gaps.py

Shows exactly where pdfplumber sees characters positioned and
what gaps exist between them.
"""

import sys

from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not available")
    sys.exit(1)


def debug_character_positions(pdf_file):
    """Debug character positions for a specific problematic area."""
    
    print(f"DEBUGGING CHARACTER POSITIONS: {Path(pdf_file).name}")
    print("=" * 60)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            chars = page.chars
            
            print(f"Found {len(chars)} characters on first page")
            
            # Find characters around the problematic date
            date_chars = []
            for i, char in enumerate(chars):
                text = char['text']
                if text in '0723/25' or (i > 0 and chars[i-1]['text'] in '0723/25') or \
                   (i < len(chars)-1 and chars[i+1]['text'] in '0723/25'):
                    date_chars.append((i, char))
            
            print(f"\nCharacters around date area:")
            print("=" * 40)
            
            for i, (char_idx, char) in enumerate(date_chars[:20]):  # Show first 20
                x = char['x0']
                y = char['y0']
                text = repr(char['text'])
                width = char.get('width', 0)
                x1 = char.get('x1', x + width)
                
                print(f"  {char_idx:3}: x={x:6.1f} y={y:6.1f} w={width:4.1f} x1={x1:6.1f} {text}")
                
                # Calculate gap to next character
                if i < len(date_chars) - 1:
                    next_char_idx, next_char = date_chars[i + 1]
                    gap = next_char['x0'] - x1
                    print(f"       gap to next: {gap:4.1f} points")
            
            # Focus on the "25" specifically
            print(f"\nFOCUS ON '25' CHARACTERS:")
            print("=" * 40)
            
            two_chars = [c for c in chars if c['text'] == '2']
            five_chars = [c for c in chars if c['text'] == '5']
            
            print(f"Found {len(two_chars)} '2' characters and {len(five_chars)} '5' characters")
            
            # Find '2' and '5' that might be part of "25"
            for two_char in two_chars:
                for five_char in five_chars:
                    # Check if they're on same line and close in X
                    y_diff = abs(two_char['y0'] - five_char['y0'])
                    x_diff = five_char['x0'] - two_char.get('x1', two_char['x0'] + two_char.get('width', 0))
                    
                    if y_diff < 2.0 and 0 <= x_diff <= 20:  # Reasonable gap
                        print(f"Potential '25' pair:")
                        print(f"  '2': x={two_char['x0']:6.1f} y={two_char['y0']:6.1f}")
                        print(f"  '5': x={five_char['x0']:6.1f} y={five_char['y0']:6.1f}")
                        print(f"  Gap: {x_diff:4.1f} points")
                        print()
            
            # Test our gap logic on a specific pair
            print(f"\nTEST GAP LOGIC:")
            print("=" * 40)
            
            if len(two_chars) > 0 and len(five_chars) > 0:
                # Test with the first '2' and '5' we find
                two_char = two_chars[0]
                five_char = five_chars[0]
                
                gap = five_char['x0'] - two_char.get('x1', two_char['x0'] + two_char.get('width', 0))
                
                print(f"Testing with gap of {gap:.1f} points between '2' and '5'")
                
                for threshold in [1.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0]:
                    would_split = gap > threshold
                    print(f"  Threshold {threshold:4.1f}: {'SPLIT' if would_split else 'KEEP'}")
    
    except Exception as e:
        print(f"Error: {e}")


def debug_line_assembly(pdf_file):
    """Debug how characters get assembled into lines."""
    
    print(f"\nDEBUGGING LINE ASSEMBLY:")
    print("=" * 40)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            chars = page.chars
            
            # Sort characters as our processor would
            sorted_chars = sorted(chars, key=lambda c: (-c['y0'], c['x0']))
            
            # Find the problematic line
            problem_line_chars = []
            for char in sorted_chars:
                # Look for chars around Y coordinate of LINEAGE line
                if 725 <= char['y0'] <= 727:  # Approximate Y range
                    problem_line_chars.append(char)
            
            print(f"Found {len(problem_line_chars)} characters in problematic line")
            print(f"Line characters:")
            
            for i, char in enumerate(problem_line_chars):
                x = char['x0']
                y = char['y0']
                text = repr(char['text'])
                
                print(f"  {i:2}: x={x:6.1f} y={y:6.1f} {text}")
            
            # Show where gaps would be added
            print(f"\nGap analysis for this line:")
            for i in range(len(problem_line_chars) - 1):
                curr = problem_line_chars[i]
                next_char = problem_line_chars[i + 1]
                
                curr_right = curr.get('x1', curr['x0'] + curr.get('width', 0))
                next_left = next_char['x0']
                gap = next_left - curr_right
                
                curr_text = curr['text']
                next_text = next_char['text']
                
                would_add_space = gap > 3.0  # Using default threshold
                
                print(f"  '{curr_text}' → '{next_text}': gap={gap:4.1f} {'SPACE' if would_add_space else 'no space'}")
    
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main debugging function."""
    print("Character Gap Debugging Tool")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python debug_character_gaps.py <pdf_file>")
        print("\nShows character positions and gaps to debug spacing issues")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    debug_character_positions(pdf_file)
    debug_line_assembly(pdf_file)
    
    print(f"\nCONCLUSIONS:")
    print("=" * 40)
    print("- Look at the actual gaps between '2' and '5'")
    print("- See if gap logic is being applied correctly")
    print("- Identify why threshold changes have no effect")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
