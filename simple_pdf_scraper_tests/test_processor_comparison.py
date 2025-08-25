#!/usr/bin/env python3
"""
Compare pypdf vs pdfplumber processor results.
File: tests/test_processor_comparison.py

Tests both processors on the same PDF to compare text extraction quality,
focusing on spacing issues and concatenation problems.
"""

import sys

from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simple_pdf_scraper.processors.pypdf_processor import PyPDFProcessor

try:
    from simple_pdf_scraper.processors.pdfplumber_processor import PDFPlumberProcessor
    pdfplumber_available = True
except ImportError:
    pdfplumber_available = False


def compare_processors(pdf_path):
    """Compare pypdf and pdfplumber processors on the same PDF."""
    
    print("PROCESSOR COMPARISON TEST")
    print("=" * 60)
    print(f"Testing file: {Path(pdf_path).name}")
    print()
    
    # Test pypdf processor
    print("PYPDF PROCESSOR:")
    print("-" * 30)
    
    try:
        pypdf_processor = PyPDFProcessor(smart_spacing=True)
        pypdf_pages = pypdf_processor.extract_pages(pdf_path)
        
        print(f"Extracted {len(pypdf_pages)} pages")
        
        # Show first few lines from first page
        if pypdf_pages and pypdf_pages[0]:
            lines = [line.strip() for line in pypdf_pages[0].split('\n') if line.strip()]
            print("First 5 lines:")
            for i, line in enumerate(lines[:5], 1):
                print(f"  {i}: '{line}'")
        
    except Exception as e:
        print(f"pypdf failed: {e}")
        pypdf_pages = None
    
    print()
    
    # Test pdfplumber processor
    print("PDFPLUMBER PROCESSOR (center-distance filtering):")
    print("-" * 50)
    
    if not pdfplumber_available:
        print("pdfplumber not available - skipping")
        return
    
    try:
        pdfplumber_processor = PDFPlumberProcessor(
            min_space_distance=6.0,
            add_space_distance=15.0
        )
        pdfplumber_pages = pdfplumber_processor.extract_pages(pdf_path)
        
        print(f"Extracted {len(pdfplumber_pages)} pages")
        
        # Show first few lines from first page
        if pdfplumber_pages and pdfplumber_pages[0]:
            lines = [line.strip() for line in pdfplumber_pages[0].split('\n') if line.strip()]
            print("First 5 lines:")
            for i, line in enumerate(lines[:5], 1):
                print(f"  {i}: '{line}'")
        
    except Exception as e:
        print(f"pdfplumber failed: {e}")
        pdfplumber_pages = None
    
    print()
    
    # Compare specific lines
    if pypdf_pages and pdfplumber_pages:
        print("LINE-BY-LINE COMPARISON:")
        print("-" * 40)
        
        pypdf_lines = [line.strip() for line in pypdf_pages[0].split('\n') if line.strip()]
        pdfplumber_lines = [line.strip() for line in pdfplumber_pages[0].split('\n') if line.strip()]
        
        # Compare first 5 lines
        max_lines = min(5, len(pypdf_lines), len(pdfplumber_lines))
        
        for i in range(max_lines):
            pypdf_line = pypdf_lines[i] if i < len(pypdf_lines) else ""
            pdfplumber_line = pdfplumber_lines[i] if i < len(pdfplumber_lines) else ""
            
            print(f"Line {i+1}:")
            print(f"  pypdf:      '{pypdf_line}'")
            print(f"  pdfplumber: '{pdfplumber_line}'")
            
            # Highlight differences
            if pypdf_line != pdfplumber_line:
                print(f"  >>> DIFFERENT")
            else:
                print(f"  >>> SAME")
            print()
        
        # Test specific patterns that should be fixed
        print("PATTERN-SPECIFIC TESTS:")
        print("-" * 30)
        test_spacing_patterns(pypdf_lines, pdfplumber_lines)


def test_spacing_patterns(pypdf_lines, pdfplumber_lines):
    """Test specific spacing patterns that commonly cause problems."""
    
    test_cases = [
        {
            'name': 'Date with spurious spaces',
            'pattern': lambda line: '/' in line and ' / ' in line
        },
        {
            'name': 'Missing spaces between words/numbers',
            'pattern': lambda line: any(c.isdigit() and (i+1 < len(line)) and line[i+1].isalpha() 
                                      for i, c in enumerate(line))
        },
        {
            'name': 'Concatenated text without spaces',
            'pattern': lambda line: len(line) > 50 and ' ' not in line[-20:]  # Long line with no spaces at end
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test['name']}")
        
        pypdf_matches = [i for i, line in enumerate(pypdf_lines) if test['pattern'](line)]
        pdfplumber_matches = [i for i, line in enumerate(pdfplumber_lines) if test['pattern'](line)]
        
        print(f"  pypdf matches:      {len(pypdf_matches)} lines")
        print(f"  pdfplumber matches: {len(pdfplumber_matches)} lines")
        
        if pypdf_matches and pdfplumber_matches:
            # Show first match from each
            pypdf_example = pypdf_lines[pypdf_matches[0]]
            pdfplumber_example = pdfplumber_lines[pdfplumber_matches[0]]
            
            print(f"  pypdf example:      '{pypdf_example[:80]}...'")
            print(f"  pdfplumber example: '{pdfplumber_example[:80]}...'")
        
        improvement = len(pypdf_matches) - len(pdfplumber_matches)
        if improvement > 0:
            print(f"  >>> IMPROVEMENT: {improvement} fewer problematic lines with pdfplumber")
        elif improvement < 0:
            print(f"  >>> REGRESSION: {-improvement} more problematic lines with pdfplumber")
        else:
            print(f"  >>> NO CHANGE")


def main():
    """Main test runner."""
    if len(sys.argv) != 2:
        print("Usage: python test_processor_comparison.py <pdf_file>")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    compare_processors(pdf_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
