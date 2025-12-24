#!/usr/bin/env python3
"""
Debug text extraction comparison tool.
File: debug_text_extraction.py

Compares pypdf vs pdfplumber text extraction for specific pages
to diagnose regex pattern matching failures.
"""

import re
import sys

from pathlib import Path

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def extract_with_pypdf(pdf_path, page_num):
    """Extract text using pypdf (what pdf-manipulator uses)."""
    if not PYPDF_AVAILABLE:
        return None, "pypdf not available"
    
    try:
        reader = PdfReader(pdf_path)
        if page_num < 1 or page_num > len(reader.pages):
            return None, f"Page {page_num} out of range (1-{len(reader.pages)})"
        
        page = reader.pages[page_num - 1]
        text = page.extract_text()
        return text, None
    except Exception as e:
        return None, str(e)


def extract_with_pdfplumber(pdf_path, page_num):
    """Extract text using pdfplumber (what simple-pdf-scraper uses)."""
    if not PDFPLUMBER_AVAILABLE:
        return None, "pdfplumber not available"
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < 1 or page_num > len(pdf.pages):
                return None, f"Page {page_num} out of range (1-{len(pdf.pages)})"
            
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            return text, None
    except Exception as e:
        return None, str(e)


def extract_with_tuned_pdfplumber(pdf_path, page_num):
    """Extract text using the TUNED pdfplumber processor (what patterns.py now uses)."""
    try:
        from simple_pdf_scraper.processors.pdfplumber_processor import PDFPlumberProcessor
        processor = PDFPlumberProcessor()
        text = processor.extract_page(pdf_path, page_num)
        return text, None
    except ImportError:
        return None, "PDFPlumberProcessor not available"
    except Exception as e:
        return None, str(e)


def find_place_of_receipt_line(text):
    """Find and return the 'Place of receipt' line from text."""
    if not text:
        return None
    
    for line in text.split('\n'):
        if 'place' in line.lower() and 'receipt' in line.lower():
            return line.strip()
    
    return None


def test_regex_against_text(text, pattern):
    """Test a regex pattern against text and return match info."""
    if not text:
        return False, None
    
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group()
        return False, None
    except re.error as e:
        return False, f"Regex error: {e}"


def show_char_codes(text, max_chars=100):
    """Show character codes for debugging invisible characters."""
    if not text:
        return "None"
    
    result = []
    for i, char in enumerate(text[:max_chars]):
        if char.isalnum() or char in ' .,!?:;-':
            result.append(char)
        else:
            result.append(f'[{ord(char):02x}]')
    
    return ''.join(result)


def compare_page(pdf_path, page_num, test_pattern=None):
    """Compare extraction methods for a single page."""
    print(f"\n{'='*70}")
    print(f"PAGE {page_num}")
    print('='*70)
    
    # Extract with both methods
    pypdf_text, pypdf_err = extract_with_pypdf(pdf_path, page_num)
    plumber_text, plumber_err = extract_with_pdfplumber(pdf_path, page_num)
    tuned_text, tuned_err = extract_with_tuned_pdfplumber(pdf_path, page_num)
    
    # Find the relevant line in each
    pypdf_line = find_place_of_receipt_line(pypdf_text) if pypdf_text else None
    plumber_line = find_place_of_receipt_line(plumber_text) if plumber_text else None
    tuned_line = find_place_of_receipt_line(tuned_text) if tuned_text else None
    
    print("\nPYPDF (raw):")
    if pypdf_err:
        print(f"  Error: {pypdf_err}")
    elif pypdf_line:
        print(f"  Line: '{pypdf_line}'")
        print(f"  Hex:  {show_char_codes(pypdf_line)}")
    else:
        print("  No 'Place of receipt' line found")
        if pypdf_text:
            print(f"  (Full text has {len(pypdf_text)} chars, {len(pypdf_text.splitlines())} lines)")
    
    print("\nPDFPLUMBER (raw):")
    if plumber_err:
        print(f"  Error: {plumber_err}")
    elif plumber_line:
        print(f"  Line: '{plumber_line}'")
        print(f"  Hex:  {show_char_codes(plumber_line)}")
    else:
        print("  No 'Place of receipt' line found")
        if plumber_text:
            print(f"  (Full text has {len(plumber_text)} chars, {len(plumber_text.splitlines())} lines)")
    
    print("\nTUNED PDFPLUMBER (what patterns.py uses):")
    if tuned_err:
        print(f"  Error: {tuned_err}")
    elif tuned_line:
        print(f"  Line: '{tuned_line}'")
        print(f"  Hex:  {show_char_codes(tuned_line)}")
    else:
        print("  No 'Place of receipt' line found")
        if tuned_text:
            print(f"  (Full text has {len(tuned_text)} chars, {len(tuned_text.splitlines())} lines)")
    
    # Test regex if provided
    if test_pattern and tuned_text:
        print(f"\nREGEX TEST against tuned pdfplumber text:")
        print(f"  Pattern: {test_pattern[:60]}...")
        matched, match_text = test_regex_against_text(tuned_text, test_pattern)
        if matched:
            print(f"  ✓ MATCHED: '{match_text}'")
        else:
            print(f"  ✗ NO MATCH")


def parse_page_list(page_str):
    """Parse comma-separated page numbers."""
    pages = []
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python debug_text_extraction.py <pdf_file> <pages> [regex_pattern]")
        print()
        print("  pages: comma-separated page numbers (e.g., '9,17,48-49,56')")
        print("  regex_pattern: optional pattern to test against pypdf extraction")
        print()
        print("Example:")
        print("  python debug_text_extraction.py doc.pdf 9,17,48,49,56")
        print()
        print("Available libraries:")
        print(f"  pypdf:      {'✓' if PYPDF_AVAILABLE else '✗'}")
        print(f"  pdfplumber: {'✓' if PDFPLUMBER_AVAILABLE else '✗'}")
        return 1
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    pages = parse_page_list(sys.argv[2])
    
    test_pattern = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"Comparing text extraction for: {pdf_path.name}")
    print(f"Pages: {pages}")
    
    for page_num in pages:
        compare_page(pdf_path, page_num, test_pattern)
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("If pypdf shows different text than pdfplumber, that explains why")
    print("your regex patterns work with simple-pdf-scraper but fail with")
    print("pdf-manipulator.")
    print()
    print("Solution options:")
    print("  1. Add pdfplumber support to pdf-manipulator's pattern matching")
    print("  2. Adjust regex to match what pypdf actually extracts")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
