#!/usr/bin/env python3
"""
Test invoice patterns on your specific PDF text.
File: test_invoice_patterns.py
"""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


def test_patterns_on_sample():
    """Test the patterns on your sample text."""
    
    # Your actual PDF text
    sample_text = """Silver Bay Seafoods LLC
4019 21st Ave W Suite 300
Seattle, WA 98199-1252
Ph. +1 (206) 960-4140
SALES INVOICE
2004716
DATE: Aug. 6, 2025
Bill To: Ship To:
Limson Trading Inc.
PO Box 1787
Grand Rapids, MI 49501
USA
Lineage Lynden
604 Curt Maberry Road
Lynden, WA 98264
USA
Customer Ref. No.: 185606 Payment Terms: Net 14 from delivery date MSC No. MSC-C-50251"""

    extractor = PatternExtractor()
    
    print("TESTING INVOICE PATTERNS")
    print("=" * 50)
    print("Sample text structure:")
    lines = sample_text.split('\n')
    for i, line in enumerate(lines, 1):
        print(f"{i:2}: {line}")
    
    print("\n" + "=" * 50)
    print("PATTERN RESULTS:")
    print("=" * 50)
    
    # Test patterns
    patterns = [
        {
            'name': 'Invoice Number',
            'pattern': {
                'keyword': 'SALES INVOICE',
                'direction': 'below',
                'distance': 1,
                'extract_type': 'word'
            }
        },
        {
            'name': 'Customer Reference',
            'pattern': {
                'keyword': 'Customer Ref. No.:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'word'
            }
        }
    ]
    
    for item in patterns:
        name = item['name']
        pattern = item['pattern']
        
        print(f"\nTesting: {name}")
        print(f"Pattern: {pattern['keyword']}:{pattern['direction']}:{pattern['distance']}:{pattern['extract_type']}")
        
        # Get debug info
        debug_info = extractor.debug_extraction(sample_text, pattern)
        
        if debug_info['success']:
            print(f"✓ Result: '{debug_info['extracted']}'")
            print(f"  Found keyword at line {debug_info['keyword_pos']['line'] + 1}")
            print(f"  Target at line {debug_info['target_pos']['line'] + 1}")
        else:
            print(f"✗ Failed: {debug_info['error']}")
            if 'keyword_matches' in debug_info:
                matches = debug_info['keyword_matches']
                if matches:
                    print(f"  Found similar keywords: {[m['word'] for m in matches]}")


def main():
    """Run the test."""
    test_patterns_on_sample()
    
    print("\n" + "=" * 50)
    print("COMMAND TO RUN:")
    print("=" * 50)
    print('python -m simple_pdf_scraper Test2_gs_fixed.pdf \\')
    print('  --pattern "SALES INVOICE:below:1:word" \\')
    print('  --pattern "Customer Ref. No.:right:0:word" \\')
    print('  --headers "Invoice_Number" "Customer_Ref" \\')
    print('  -o results.tsv')


if __name__ == "__main__":
    main()

# End of file #
