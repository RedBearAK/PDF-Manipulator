#!/usr/bin/env python3
"""
Explore how pypdf assembles text from PDF objects.
File: tests/explore_text_assembly.py

Investigates the granularity at which pypdf extracts text and whether
we can intercept or influence the assembly process.
"""

import sys

from pathlib import Path

try:
    import pypdf
except ImportError:
    print("Error: pypdf not installed. Run: pip install pypdf")
    sys.exit(1)


def test_basic_text_extraction(page):
    """Test the basic text extraction to see what we get."""
    print("BASIC TEXT EXTRACTION:")
    print("=" * 40)
    
    # Standard extraction
    text = page.extract_text()
    
    print(f"Total characters: {len(text)}")
    print(f"Total lines: {len(text.splitlines())}")
    
    # Show first few lines
    lines = text.splitlines()
    for i, line in enumerate(lines[:10]):
        print(f"Line {i+1:2}: '{line}'")
    
    if len(lines) > 10:
        print(f"... and {len(lines) - 10} more lines")
    
    return text


def test_visitor_text_granularity(page):
    """Test what granularity the visitor pattern gives us."""
    print("\n\nVISITOR PATTERN GRANULARITY:")
    print("=" * 40)
    
    text_chunks = []
    positions = []
    
    def capture_visitor(text, user_matrix, tm_matrix, font_dict, font_size):
        """Capture each text chunk the visitor sees."""
        if text and text.strip():
            text_chunks.append(text)
            
            # Try to extract position
            try:
                if tm_matrix and len(tm_matrix) >= 6:
                    x, y = float(tm_matrix[4]), float(tm_matrix[5])
                    positions.append((x, y))
                else:
                    positions.append((None, None))
            except:
                positions.append((None, None))
    
    try:
        # Extract using visitor
        result = page.extract_text(visitor_text=capture_visitor)
        
        print(f"✓ Visitor pattern works!")
        print(f"Total chunks captured: {len(text_chunks)}")
        print(f"Result length: {len(result)} characters")
        
        # Analyze chunk sizes
        chunk_sizes = [len(chunk) for chunk in text_chunks]
        print(f"Chunk size range: {min(chunk_sizes)} to {max(chunk_sizes)} characters")
        
        # Show first few chunks with positions
        print(f"\nFirst 10 chunks:")
        for i, (chunk, pos) in enumerate(zip(text_chunks[:10], positions[:10])):
            x, y = pos
            pos_str = f"({x:.1f}, {y:.1f})" if x is not None else "(?, ?)"
            print(f"  {i+1:2}: {pos_str:12} '{chunk}'")
        
        # Look for position jumps that might indicate concatenation issues
        if len(positions) > 1:
            print(f"\nPosition analysis:")
            big_jumps = 0
            for i in range(1, len(positions)):
                x1, y1 = positions[i-1]
                x2, y2 = positions[i]
                
                if x1 is not None and x2 is not None:
                    x_jump = abs(x2 - x1)
                    y_jump = abs(y2 - y1)
                    
                    if x_jump > 50:  # Arbitrary threshold
                        big_jumps += 1
                        if big_jumps <= 5:  # Show first 5
                            print(f"  Big X jump ({x_jump:.1f}): '{text_chunks[i-1]}' → '{text_chunks[i]}'")
            
            if big_jumps > 5:
                print(f"  ... and {big_jumps - 5} more big jumps")
        
        return True, text_chunks, positions
        
    except Exception as e:
        print(f"✗ Visitor pattern failed: {e}")
        return False, [], []


def test_manual_assembly(text_chunks, positions):
    """Test manually assembling text with better spacing logic."""
    print("\n\nMANUAL ASSEMBLY TEST:")
    print("=" * 40)
    
    if not text_chunks or not positions:
        print("No chunks to assemble")
        return ""
    
    assembled_parts = []
    
    for i, (chunk, pos) in enumerate(zip(text_chunks, positions)):
        # Add the current chunk
        assembled_parts.append(chunk)
        
        # Decide whether to add spacing before next chunk
        if i < len(text_chunks) - 1:  # Not the last chunk
            current_x, current_y = pos
            next_x, next_y = positions[i + 1]
            
            # Add spacing logic
            should_add_space = False
            
            if current_x is not None and next_x is not None:
                x_jump = abs(next_x - current_x)
                y_jump = abs(next_y - current_y) if next_y is not None else 0
                
                # Add space for big horizontal jumps (different columns/boxes)
                if x_jump > 20:  # Configurable threshold
                    should_add_space = True
                
                # Add space for line breaks if text doesn't end/start with whitespace
                elif y_jump > 5 and not chunk.endswith(' ') and not text_chunks[i+1].startswith(' '):
                    should_add_space = True
            
            if should_add_space:
                assembled_parts.append(' ')
    
    manually_assembled = ''.join(assembled_parts)
    
    # Compare with original
    original = ''.join(text_chunks)
    
    print(f"Original length: {len(original)}")
    print(f"Manual length: {len(manually_assembled)}")
    print(f"Added {len(manually_assembled) - len(original)} characters")
    
    # Show differences in first few lines
    orig_lines = original.splitlines()
    manual_lines = manually_assembled.splitlines()
    
    print(f"\nComparison (first 5 lines):")
    for i in range(min(5, len(orig_lines), len(manual_lines))):
        if orig_lines[i] != manual_lines[i]:
            print(f"  Line {i+1}:")
            print(f"    Orig:   '{orig_lines[i]}'")
            print(f"    Manual: '{manual_lines[i]}'")
        else:
            print(f"  Line {i+1}: (same)")
    
    return manually_assembled


def explore_text_assembly(pdf_file):
    """Main exploration of text assembly process."""
    print(f"EXPLORING TEXT ASSEMBLY: {pdf_file}")
    print("=" * 60)
    
    try:
        with open(pdf_file, 'rb') as file:
            reader = pypdf.PdfReader(file)
            
            if len(reader.pages) == 0:
                print("✗ PDF has no pages")
                return False
            
            page = reader.pages[0]
            print(f"✓ Using first page")
            
            # Test basic extraction
            basic_text = test_basic_text_extraction(page)
            
            # Test visitor granularity
            visitor_worked, chunks, positions = test_visitor_text_granularity(page)
            
            if visitor_worked:
                # Test manual assembly
                manual_text = test_manual_assembly(chunks, positions)
                
                # Final comparison
                print(f"\n\nFINAL COMPARISON:")
                print("=" * 40)
                print(f"Basic extraction gives us: {len(basic_text)} chars")
                print(f"Manual assembly gives us: {len(manual_text)} chars")
                
                if basic_text != manual_text:
                    print("✓ Manual assembly produced different result!")
                    print("✓ We can improve spacing during extraction!")
                else:
                    print("✗ Manual assembly same as basic - no improvement")
            
            return visitor_worked
            
    except Exception as e:
        print(f"✗ Error exploring PDF: {e}")
        return False


def main():
    """Main function."""
    print("Text Assembly Explorer")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python explore_text_assembly.py <pdf_file>")
        print("\nThis script investigates how pypdf assembles text from PDF objects")
        print("and whether we can intercept the process to add better spacing.")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    success = explore_text_assembly(pdf_file)
    
    print("\n" + "=" * 60)
    print("CONCLUSIONS:")
    print("=" * 60)
    
    if success:
        print("✓ We can intercept pypdf's text assembly process!")
        print("✓ Text comes in chunks with position information")
        print("✓ We can add intelligent spacing based on coordinate jumps")
        print("✓ This is much simpler than complex pattern matching")
        print("\nNext step: Implement coordinate-threshold spacing")
    else:
        print("✗ Cannot intercept pypdf's text assembly")
        print("✗ Must fall back to pattern-based fixes")
        print("✗ Or try alternative PDF libraries")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

# End of file #
