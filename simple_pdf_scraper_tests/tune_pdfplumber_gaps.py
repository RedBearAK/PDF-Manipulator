#!/usr/bin/env python3
"""
Tune pdfplumber gap detection thresholds.
File: tests/tune_pdfplumber_gaps.py

Test different gap thresholds to find optimal settings for specific PDFs.
"""

import sys

from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from simple_pdf_scraper.processors.pdfplumber_processor import PDFPlumberProcessor
except ImportError:
    print("Error: PDFPlumberProcessor not available")
    sys.exit(1)


def test_gap_settings(pdf_file, char_gaps, word_gaps):
    """Test different gap threshold combinations."""
    
    print(f"TESTING GAP SETTINGS: {Path(pdf_file).name}")
    print("=" * 60)
    
    results = []
    
    for char_gap in char_gaps:
        for word_gap in word_gaps:
            print(f"\nTesting char_gap={char_gap}, word_gap={word_gap}")
            print("-" * 30)
            
            try:
                processor = PDFPlumberProcessor(
                    char_gap_threshold=char_gap,
                    word_gap_threshold=word_gap
                )
                
                # Extract first page
                pages = processor.extract_pages(pdf_file)
                if not pages:
                    print("✗ No text extracted")
                    continue
                
                text = pages[0]
                lines = text.splitlines()
                
                # Find the problematic line
                problem_line = None
                for line in lines:
                    if "LINEAGE TRANSPORTATION LLC" in line:
                        problem_line = line
                        break
                
                if problem_line:
                    print(f"Result: '{problem_line[:80]}{'...' if len(problem_line) > 80 else ''}'")
                    
                    # Score the result
                    score = score_line_quality(problem_line)
                    print(f"Score: {score}/10")
                    
                    results.append({
                        'char_gap': char_gap,
                        'word_gap': word_gap, 
                        'line': problem_line,
                        'score': score
                    })
                else:
                    print("✗ Problematic line not found")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
    
    # Show best results
    if results:
        print(f"\n\nBEST RESULTS:")
        print("=" * 60)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        for i, result in enumerate(results[:3]):
            print(f"{i+1}. Score {result['score']}/10 - char_gap={result['char_gap']}, word_gap={result['word_gap']}")
            print(f"   '{result['line'][:100]}{'...' if len(result['line']) > 100 else ''}'")
            print()


def score_line_quality(line):
    """Score how well a line is formatted (0-10)."""
    score = 10
    
    # Penalize obvious formatting issues
    if " / 2 5" in line:  # Broken year
        score -= 3
    elif "/ 2 5" in line:
        score -= 2
    elif " 2 5" in line and "07/23" in line:  # Broken year in date context
        score -= 2
    
    if "9057759407/23" in line:  # Number stuck to date
        score -= 3
    
    if "   " in line:  # Multiple spaces (might be too much spacing)
        score -= 1
    
    # Reward good patterns
    if "90577594 07/23/25" in line:  # Good separation
        score += 2
    
    if "$1,197.82" in line:  # Properly formatted currency
        score += 1
    
    return max(0, score)


def main():
    """Main tuning function."""
    print("PDFPlumber Gap Tuning Tool")
    print("=" * 40)
    
    if len(sys.argv) != 2:
        print("Usage: python tune_pdfplumber_gaps.py <pdf_file>")
        print("\nTest different gap thresholds to find optimal settings")
        return 1
    
    pdf_file = sys.argv[1]
    
    if not Path(pdf_file).exists():
        print(f"Error: File not found: {pdf_file}")
        return 1
    
    # Test different gap combinations
    char_gaps = [1.0, 2.0, 3.0, 4.0, 5.0]
    word_gaps = [6.0, 8.0, 10.0, 12.0, 15.0]
    
    test_gap_settings(pdf_file, char_gaps, word_gaps)
    
    print("\nRECOMMENDATIONS:")
    print("=" * 40)
    print("- Use the highest scoring settings")
    print("- char_gap controls spacing within words/numbers")  
    print("- word_gap controls spacing between distinct elements")
    print("- Lower values = less spacing, higher values = more spacing")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# End of file #
