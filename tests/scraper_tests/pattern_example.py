#!/usr/bin/env python3
"""
Example showing how pattern matching works with multi-line text.
File: pattern_example.py
"""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


def demonstrate_pattern_matching():
    """Show how pattern matching works with realistic PDF text."""
    
    # Simulate text extracted from a PDF invoice
    sample_text = """ABC Company Inc
Invoice #12345
Date: 2024-01-15

Bill To:
Customer Name
123 Main Street
City, State 12345

Item Description                    Qty    Price    Total
Widget A                            5      $10.00   $50.00
Widget B                            2      $25.00   $50.00
Premium Service                     1      $100.00  $100.00

                          Subtotal:           $200.00
                            Tax:              $16.00
                          Total:              $216.00

Payment Due: 30 days
Thank you for your business!"""

    extractor = PatternExtractor()
    
    print("SAMPLE PDF TEXT:")
    print("=" * 50)
    print(sample_text)
    print("\n" + "=" * 50)
    print("PATTERN EXTRACTION EXAMPLES:")
    print("=" * 50)
    
    # Example patterns
    patterns = [
        {
            'name': 'Invoice Number',
            'pattern': {
                'keyword': 'Invoice #',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'word'
            }
        },
        {
            'name': 'Date',
            'pattern': {
                'keyword': 'Date:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'word'
            }
        },
        {
            'name': 'Company Name',
            'pattern': {
                'keyword': 'Invoice #',
                'direction': 'above',
                'distance': 1,
                'extract_type': 'line'
            }
        },
        {
            'name': 'Total Amount',
            'pattern': {
                'keyword': 'Total:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'text'
            }
        },
        {
            'name': 'Payment Terms',
            'pattern': {
                'keyword': 'Payment Due:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'text'
            }
        },
        {
            'name': 'Customer Info',
            'pattern': {
                'keyword': 'Bill To:',
                'direction': 'below',
                'distance': 1,
                'extract_type': 'line'
            }
        }
    ]
    
    # Extract using each pattern
    for item in patterns:
        name = item['name']
        pattern = item['pattern']
        
        result = extractor.extract_pattern(sample_text, pattern)
        
        print(f"{name:15}: {result if result else '(not found)'}")
    
    print("\n" + "=" * 50)
    print("HOW PATTERNS WORK:")
    print("=" * 50)
    print("""
DIRECTION EXAMPLES:
- 'right': Look for words/text to the right of keyword
- 'left': Look for words/text to the left of keyword  
- 'below': Look at lines below the keyword line
- 'above': Look at lines above the keyword line

DISTANCE:
- 0: Immediately adjacent (next word or same line)
- 1: Skip 1 word/line, then extract
- 2: Skip 2 words/lines, then extract

EXTRACT TYPES:
- 'word': Extract a single word
- 'number': Extract just the numeric part
- 'line': Extract the entire line
- 'text': Extract from position to end of line

The text maintains its line structure, so 'above' and 'below' 
work even though the final TSV output flattens it into cells.
""")


if __name__ == "__main__":
    demonstrate_pattern_matching()

# End of file #
