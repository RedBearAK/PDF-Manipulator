#!/usr/bin/env python3
"""
Debug script to analyze PDF text extraction and pattern matching.
File: debug_pdf.py
"""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from simple_pdf_scraper.processors.pypdf_processor import PyPDFProcessor
from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


def analyze_pdf(pdf_file):
    """Analyze a PDF file and show detailed text extraction info."""
    
    print(f"ANALYZING: {pdf_file}")
    print("=" * 60)
    
    processor = PyPDFProcessor(suppress_warnings=True)
    
    try:
        # Validate PDF first
        validation = processor.validate_pdf(pdf_file)
        
        print("PDF VALIDATION:")
        print(f"  Valid: {validation['valid']}")
        if validation['error']:
            print(f"  Error: {validation['error']}")
        if validation['info']:
            print(f"  Pages: {validation['info'].get('page_count', 'unknown')}")
            print(f"  Encrypted: {validation['info'].get('encrypted', 'unknown')}")
        print()
        
        if not validation['valid']:
            return False
        
        # Extract pages
        pages = processor.extract_pages(pdf_file)
        
        print(f"EXTRACTED {len(pages)} PAGES:")
        print("-" * 30)
        
        for page_num, page_text in enumerate(pages, 1):
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            print(f"Page {page_num}: {len(lines)} lines, {len(page_text)} chars")
            
            # Show first few lines as preview
            if lines:
                print(f"  First line: '{lines[0][:60]}{'...' if len(lines[0]) > 60 else ''}'")
                if len(lines) > 1:
                    print(f"  Last line:  '{lines[-1][:60]}{'...' if len(lines[-1]) > 60 else ''}'")
            else:
                print("  (No text found)")
            print()
        
        # Show full text structure for first page
        if pages and pages[0].strip():
            print("FIRST PAGE STRUCTURE:")
            print("-" * 30)
            first_page_lines = [line for line in pages[0].split('\n') if line.strip()]
            
            for i, line in enumerate(first_page_lines[:15], 1):  # Show first 15 lines
                print(f"{i:2}: {line}")
            
            if len(first_page_lines) > 15:
                print(f"... ({len(first_page_lines) - 15} more lines)")
            print()
        
        # Test some common patterns
        if pages and pages[0].strip():
            print("TESTING COMMON PATTERNS:")
            print("-" * 30)
            
            extractor = PatternExtractor()
            
            test_patterns = [
                ('Invoice', 'Invoice:right:0:word'),
                ('Number', '#:right:0:word'),
                ('Date', 'Date:right:0:word'),
                ('Total', 'Total:right:0:text'),
                ('Amount', 'Amount:right:0:text'),
            ]
            
            for name, pattern_str in test_patterns:
                try:
                    keyword, direction, distance, extract_type = pattern_str.split(':')
                    pattern = {
                        'keyword': keyword,
                        'direction': direction,
                        'distance': int(distance),
                        'extract_type': extract_type
                    }
                    
                    result = extractor.extract_pattern(pages[0], pattern)
                    status = "✓" if result else "✗"
                    print(f"  {status} {name:10}: {result if result else '(not found)'}")
                    
                except Exception as e:
                    print(f"  ✗ {name:10}: Error - {e}")
            
            print()
        
        print("RECOMMENDATIONS:")
        print("-" * 30)
        print("1. Use --dump-text to see the exact text structure")
        print("2. Look for unique keywords near the data you want")
        print("3. Count words/lines between keyword and target data")
        print("4. Test patterns with single files before batch processing")
        print()
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python debug_pdf.py <pdf_file>")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    success = analyze_pdf(pdf_file)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

# End of file #
