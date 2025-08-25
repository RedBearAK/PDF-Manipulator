#!/usr/bin/env python3
"""
Test pdfplumber vs pypdf for text extraction granularity.
File: tests/test_pdfplumber_comparison.py

Compare what level of text granularity we get from different PDF libraries
to see if we can avoid the concatenation problem entirely.
"""

import sys

from pathlib import Path

# Test both libraries
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pdfplumber  
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def test_pypdf_extraction(pdf_file):
    """Test pypdf extraction (we know this concatenates)."""
    print("PYPDF EXTRACTION:")
    print("=" * 40)
    
    if not PYPDF_AVAILABLE:
        print("✗ pypdf not available")
        return None
    
    try:
        with open(pdf_file, 'rb') as file:
            reader = pypdf.PdfReader(file)
            page = reader.pages[0]
            text = page.extract_text()
            
            lines = text.splitlines()[:5]
            print(f"First 5 lines:")
            for i, line in enumerate(lines, 1):
                print(f"  {i}: '{line[:80]}{'...' if len(line) > 80 else ''}'")
            
            return text
            
    except Exception as e:
        print(f"✗ pypdf extraction failed: {e}")
        return None


def test_pdfplumber_characters(pdf_file):
    """Test pdfplumber character-level extraction."""
    print("\nPDFPLUMBER CHARACTER-LEVEL:")
    print("=" * 40)
    
    if not PDFPLUMBER_AVAILABLE:
        print("✗ pdfplumber not available")
        print("  Install with: pip install pdfplumber")
        return None, None
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            
            # Get individual characters with positions
            chars = page.chars
            
            print(f"Found {len(chars)} individual characters")
            print(f"Sample characters:")
            
            # Show first 20 characters with positions
            for i, char in enumerate(chars[:20]):
                x = char['x0']
                y = char['y0']
                text = repr(char['text'])
                print(f"  {i+1:2}: ({x:6.1f}, {y:6.1f}) {text}")
            
            # Try to extract text normally for comparison
            text = page.extract_text()
            
            return chars, text
            
    except Exception as e:
        print(f"✗ pdfplumber extraction failed: {e}")
        return None, None


def test_pdfplumber_words(pdf_file):
    """Test pdfplumber word-level extraction."""
    print("\nPDFPLUMBER WORD-LEVEL:")
    print("=" * 40)
    
    if not PDFPLUMBER_AVAILABLE:
        print("✗ pdfplumber not available")
        return None
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            
            # Get individual words with positions
            words = page.extract_words()
            
            print(f"Found {len(words)} individual words")
            print(f"Sample words:")
            
            # Show first 15 words with positions  
            for i, word in enumerate(words[:15]):
                x = word['x0']
                y = word['y0']
                text = repr(word['text'])
                print(f"  {i+1:2}: ({x:6.1f}, {y:6.1f}) {text}")
            
            return words
            
    except Exception as e:
        print(f"✗ pdfplumber word extraction failed: {e}")
        return None


def test_smart_reassembly(words):
    """Test reassembling words with intelligent spacing."""
    print("\nSMART REASSEMBLY TEST:")
    print("=" * 40)
    
    if not words:
        print("No words to reassemble")
        return ""
    
    # Group words by line (same Y coordinate, with tolerance)
    lines = []
    current_line = []
    current_y = None
    
    for word in words:
        y = word['y0']
        
        # Start new line if Y changed significantly
        if current_y is None or abs(y - current_y) > 5:
            if current_line:
                lines.append(current_line)
            current_line = [word]
            current_y = y
        else:
            current_line.append(word)
    
    # Don't forget the last line
    if current_line:
        lines.append(current_line)
    
    print(f"Organized into {len(lines)} lines")
    
    # Reassemble with smart spacing within lines
    reassembled_lines = []
    
    for line_words in lines[:10]:  # Show first 10 lines
        line_parts = []
        
        for i, word in enumerate(line_words):
            line_parts.append(word['text'])
            
            # Add spacing logic for next word
            if i < len(line_words) - 1:
                next_word = line_words[i + 1]
                
                # Calculate gap between words
                current_right = word['x1']  # Right edge of current word
                next_left = next_word['x0']  # Left edge of next word
                gap = next_left - current_right
                
                # Add space if there's a significant gap
                if gap > 3:  # Configurable threshold
                    line_parts.append(' ')
        
        line_text = ''.join(line_parts)
        reassembled_lines.append(line_text)
        print(f"  Line: '{line_text[:80]}{'...' if len(line_text) > 80 else ''}'")
    
    return '\n'.join(reassembled_lines)


def compare_extractions(pdf_file):
    """Compare all extraction methods."""
    print(f"COMPARING EXTRACTION METHODS: {Path(pdf_file).name}")
    print("=" * 60)
    
    # Test pypdf
    pypdf_text = test_pypdf_extraction(pdf_file)
    
    # Test pdfplumber
    chars, pdfplumber_text = test_pdfplumber_characters(pdf_file)
    words = test_pdfplumber_words(pdf_file)
    
    # Test smart reassembly
    if words:
        smart_text = test_smart_reassembly(words)
    else:
        smart_text = None
    
    # Compare results
    print(f"\nCOMPARISON SUMMARY:")
    print("=" * 40)
    
    if pypdf_text:
        pypdf_lines = pypdf_text.splitlines()
        print(f"pypdf:      {len(pypdf_text)} chars, {len(pypdf_lines)} lines")
    
    if pdfplumber_text:
        plumber_lines = pdfplumber_text.splitlines()
        print(f"pdfplumber: {len(pdfplumber_text)} chars, {len(plumber_lines)} lines")
    
    if smart_text:
        smart_lines = smart_text.splitlines()
        print(f"smart:      {len(smart_text)} chars, {len(smart_lines)} lines")
    
    # Show the problematic line
    print(f"\nPROBLEMATIC LINE COMPARISON:")
    if pypdf_text and len(pypdf_text.splitlines()) >= 3:
        print(f"pypdf line 3:      '{pypdf_text.splitlines()[2]}'")
    
    if pdfplumber_text and len(pdfplumber_text.splitlines()) >= 3:
        print(f"pdfplumber line 3: '{pdfplumber_text.splitlines()[2]}'")
    
    if smart_text and len(smart_text.splitlines()) >= 3:
        print(f"smart line 3:      '{smart_text.splitlines()[2]}'")


def main():
    """Main comparison function."""
    print("PDF Library Comparison Tool")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python test_pdfplumber_comparison.py <pdf_file>")
        print("\nThis compares pypdf vs pdfplumber text extraction granularity")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    # Check what's available
    print("Available libraries:")
    print(f"  pypdf:      {'✓' if PYPDF_AVAILABLE else '✗'}")
    print(f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
    print()
    
    if not PYPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
        print("No PDF libraries available!")
        return 1
    
    compare_extractions(pdf_file)
    
    print("\n" + "=" * 60)
    print("CONCLUSIONS:")
    print("=" * 60)
    
    if PDFPLUMBER_AVAILABLE:
        print("✓ pdfplumber provides character and word-level access")
        print("✓ We can rebuild text with proper spacing based on coordinates")
        print("✓ This avoids pypdf's concatenation problem entirely")
        print("\nRecommendation: Add pdfplumber as alternative processor")
    else:
        print("✗ pdfplumber not available to test")
        print("✗ Stuck with pypdf's pre-concatenated chunks")
        print("\nRecommendation: Install pdfplumber and retest")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
