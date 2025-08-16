"""
Pattern Extractor Debugger - Phase 2 
File: debug_pattern_extractor.py

Debug script to understand exactly what's happening with pattern extraction.
This will show us the sample text and step-by-step extraction process.
"""

import tempfile
from pathlib import Path

# Import the enhanced pattern extractor
from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor


def create_sample_text():
    """Create sample text that matches the actual test file."""
    return """Company: ACME Corporation
Invoice Number: INV-2024-001
Date: March 15, 2024

Description: Software License
Amount: $1,250.00
Tax: $125.00
Total: $1,375.00

Thank you for your business!"""


def debug_test_patterns():
    """Debug the test patterns to see what's happening."""
    
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("=== SAMPLE TEXT ===")
    print(sample_text)
    print()
    
    # Test patterns from the ACTUAL test file
    test_cases = [
        {
            'name': 'Test 1: Basic movement (legacy format)', 
            'pattern': {
                'keyword': 'Invoice Number:',
                'direction': 'right',
                'distance': 1,
                'extract_type': 'word'
            },
            'expected': 'INV-2024-001'
        },
        {
            'name': 'Test 2: Enhanced single movement',
            'pattern': {
                'keyword': 'Amount:',
                'movements': [('r', 1)],
                'extract_type': 'nb',
                'extract_count': 1,
                'flexible': False
            },
            'expected': 'contains 1250'
        },
        {
            'name': 'Test 3: Chained movements',
            'pattern': {
                'keyword': 'Invoice Number:',
                'movements': [('d', 2), ('r', 1)],  # Down 2 lines, right 1 word
                'extract_type': 'wd',
                'extract_count': 1,
                'flexible': False
            },
            'expected': 'Software'
        },
        {
            'name': 'Test 4: Zero-count extraction',
            'pattern': {
                'keyword': 'Description:',
                'movements': [('r', 1)],
                'extract_type': 'wd',
                'extract_count': 0,  # Until end of line
                'flexible': False
            },
            'expected': 'Software License'
        },
        {
            'name': 'Test 5: Flexible extraction',
            'pattern': {
                'keyword': 'Total:',
                'movements': [('r', 1)],
                'extract_type': 'nb',
                'extract_count': 1,
                'flexible': True
            },
            'expected': 'contains 1375'
        },
        {
            'name': 'Test 6: Zero movements',
            'pattern': {
                'keyword': 'ACME',
                'movements': [],  # No movements
                'extract_type': 'wd',
                'extract_count': 1,
                'flexible': False
            },
            'expected': 'Corporation'  # Should get word after ACME
        }
    ]
    
    print("=== PATTERN EXTRACTION DEBUG ===")
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        print(f"Pattern: {test_case['pattern']}")
        print(f"Expected: {test_case['expected']}")
        
        # Debug the extraction step by step
        debug_result = extractor.debug_extraction(sample_text, test_case['pattern'])
        
        print(f"Success: {debug_result['success']}")
        if debug_result['success']:
            print(f"Keyword found at: line {debug_result['keyword_pos']['line']}, word {debug_result['keyword_pos']['word_index']}")
            print(f"Keyword word: '{debug_result['keyword_pos']['word']}'")
            print(f"Target position: line {debug_result['target_pos']['line']}, word {debug_result['target_pos']['word_index']}")
            print(f"Target line text: '{debug_result['target_pos']['line_text']}'")
            print(f"Extracted: '{debug_result['extracted']}'")
            
            # Check if result matches expectation
            if test_case['expected'].startswith('contains '):
                expected_substring = test_case['expected'].replace('contains ', '')
                # Handle comma-separated numbers properly
                if debug_result['extracted'] and (
                    expected_substring in debug_result['extracted'] or 
                    expected_substring in debug_result['extracted'].replace(',', '')
                ):
                    print("✅ MATCH!")
                else:
                    print(f"❌ MISMATCH - got '{debug_result['extracted']}', expected to contain '{expected_substring}'")
            elif debug_result['extracted'] == test_case['expected']:
                print("✅ MATCH!")
            else:
                print(f"❌ MISMATCH - got '{debug_result['extracted']}', expected '{test_case['expected']}'")
        else:
            print(f"Error: {debug_result['error']}")
            if 'keyword_matches' in debug_result:
                print(f"Available keyword matches: {debug_result['keyword_matches']}")


def debug_keyword_search():
    """Debug the keyword search functionality specifically."""
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("\n=== KEYWORD SEARCH DEBUG ===")
    
    keywords_to_test = ['Invoice Number', 'ACME', 'Corporation', 'Software', 'Total Amount', 'Company']
    
    for keyword in keywords_to_test:
        print(f"\nSearching for: '{keyword}'")
        pos = extractor._find_keyword_position(sample_text, keyword)
        if pos:
            print(f"  Found at line {pos['line']}, word {pos['word_index']}")
            print(f"  Word: '{pos['word']}'")
            print(f"  Line text: '{pos['line_text']}'")
        else:
            print(f"  Not found")
            
            # Show all matches for debugging
            all_matches = extractor.find_all_keyword_matches(sample_text, keyword)
            if all_matches:
                print(f"  Partial matches found:")
                for match in all_matches:
                    print(f"    Line {match['line']}: '{match['word']}' in '{match['line_text']}'")


def test_number_extraction():
    """Test number extraction specifically since tests are getting monetary amounts."""
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("\n=== NUMBER EXTRACTION DEBUG ===")
    
    # Test number extraction from Amount
    pattern = {
        'keyword': 'Amount:',
        'movements': [('r', 1)],
        'extract_type': 'nb',
        'extract_count': 1,
        'flexible': False
    }
    
    result = extractor.debug_extraction(sample_text, pattern)
    print(f"Amount number extraction: {result}")
    
    # Test number extraction from Total
    pattern_total = {
        'keyword': 'Total:',
        'movements': [('r', 1)],
        'extract_type': 'nb',
        'extract_count': 1,
        'flexible': True
    }
    
    result_total = extractor.debug_extraction(sample_text, pattern_total)
    print(f"Total number extraction: {result_total}")


def debug_empty_line_handling():
    """Debug empty line handling in vertical movements."""
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("\n=== EMPTY LINE HANDLING DEBUG ===")
    
    lines = sample_text.split('\n')
    for i, line in enumerate(lines):
        print(f"Line {i}: '{line}'")
    
    # Test the chained movement that's failing
    pattern = {
        'keyword': 'Invoice Number:',
        'movements': [('d', 2), ('r', 1)],
        'extract_type': 'wd',
        'extract_count': 1,
        'flexible': False
    }
    
    print(f"\nTesting chained movement: {pattern}")
    debug_result = extractor.debug_extraction(sample_text, pattern)
    print(f"Result: {debug_result}")
    
    # Test what happens with different down movements
    for down_amount in [1, 2, 3]:
        test_pattern = {
            'keyword': 'Invoice Number:',
            'movements': [('d', down_amount)],
            'extract_type': 'wd',
            'extract_count': 1,
            'flexible': False
        }
        result = extractor.extract_pattern(sample_text, test_pattern)
        print(f"Down {down_amount}: '{result}'")
    """Test number extraction specifically since tests are getting monetary amounts."""
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("\n=== NUMBER EXTRACTION DEBUG ===")
    
    # Test direct number extraction
    pattern = {
        'keyword': 'Total Amount',
        'movements': [('r', 1)],
        'extract_type': 'nb',
        'extract_count': 1,
        'flexible': False
    }
    
    result = extractor.debug_extraction(sample_text, pattern)
    print(f"Total Amount number extraction: {result}")
    
    # Test what happens if we extract words instead
    pattern_words = {
        'keyword': 'Total Amount',
        'movements': [('r', 1)],
        'extract_type': 'wd',
        'extract_count': 1,
        'flexible': False
    }
    
    result_words = extractor.debug_extraction(sample_text, pattern_words)
    print(f"Total Amount word extraction: {result_words}")


def debug_keyword_search():
    """Debug the keyword search functionality specifically."""
    sample_text = create_sample_text()
    extractor = PatternExtractor()
    
    print("\n=== KEYWORD SEARCH DEBUG ===")
    
    keywords_to_test = ['Invoice Number', 'ACME', 'Corporation', 'Software', 'Total Amount', 'Company']
    
    for keyword in keywords_to_test:
        print(f"\nSearching for: '{keyword}'")
        pos = extractor._find_keyword_position(sample_text, keyword)
        if pos:
            print(f"  Found at line {pos['line']}, word {pos['word_index']}")
            print(f"  Word: '{pos['word']}'")
            print(f"  Line text: '{pos['line_text']}'")
        else:
            print(f"  Not found")
            
            # Show all matches for debugging
            all_matches = extractor.find_all_keyword_matches(sample_text, keyword)
            if all_matches:
                print(f"  Partial matches found:")
                for match in all_matches:
                    print(f"    Line {match['line']}: '{match['word']}' in '{match['line_text']}'")


if __name__ == "__main__":
    debug_keyword_search()
    debug_test_patterns()
    test_number_extraction()
    debug_empty_line_handling()


# End of file #
