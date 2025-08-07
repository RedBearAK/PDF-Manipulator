"""
Test pattern extraction functionality.

Tests should be runnable with pytest but not in pytest style.
Accumulate results and show final score.
"""

import sys

from pathlib import Path

# Add parent directory to Python path to find the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


def test_pattern_extractor_initialization():
    """Test that PatternExtractor can be initialized."""
    try:
        extractor = PatternExtractor()
        return True, "PatternExtractor initialized successfully"
    except Exception as e:
        return False, f"Failed to initialize PatternExtractor: {e}"


def test_keyword_finding():
    """Test finding keywords in text."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Invoice Number: 12345\nTotal Amount: $567.89\nDate: 2024-01-15"
        
        # Test finding existing keyword
        pos = extractor._find_keyword_position(test_text, "Invoice Number")
        if pos is None:
            return False, "Failed to find existing keyword"
        
        if pos['line'] != 0 or pos['word_index'] != 0:
            return False, f"Wrong position for keyword: line {pos['line']}, word {pos['word_index']}"
        
        # Test case insensitive search
        pos_case = extractor._find_keyword_position(test_text, "TOTAL AMOUNT")
        if pos_case is None:
            return False, "Case insensitive search failed"
        
        return True, "Keyword finding works correctly"
    except Exception as e:
        return False, f"Error testing keyword finding: {e}"


def test_right_direction_extraction():
    """Test extracting text to the right of a keyword."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Invoice Number: 12345 ABC"
        pattern = {
            'keyword': 'Invoice Number:',
            'direction': 'right',
            'distance': 0,
            'extract_type': 'word'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        if result != "12345":
            return False, f"Expected '12345', got '{result}'"
        
        return True, "Right direction extraction works"
    except Exception as e:
        return False, f"Error testing right direction: {e}"


def test_left_direction_extraction():
    """Test extracting text to the left of a keyword."""
    try:
        extractor = PatternExtractor()
        
        test_text = "ABC 12345 Total Amount"
        pattern = {
            'keyword': 'Total',
            'direction': 'left',
            'distance': 1,
            'extract_type': 'word'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        if result != "12345":
            return False, f"Expected '12345', got '{result}'"
        
        return True, "Left direction extraction works"
    except Exception as e:
        return False, f"Error testing left direction: {e}"


def test_below_direction_extraction():
    """Test extracting text below a keyword."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Invoice Details\nTotal: $100.50\nPayment Due"
        pattern = {
            'keyword': 'Invoice Details',
            'direction': 'below',
            'distance': 1,
            'extract_type': 'line'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        if result != "Total: $100.50":
            return False, f"Expected 'Total: $100.50', got '{result}'"
        
        return True, "Below direction extraction works"
    except Exception as e:
        return False, f"Error testing below direction: {e}"


def test_above_direction_extraction():
    """Test extracting text above a keyword."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Company Name Inc\nInvoice #123\nPayment Due"
        pattern = {
            'keyword': 'Invoice',
            'direction': 'above',
            'distance': 1,
            'extract_type': 'line'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        if result != "Company Name Inc":
            return False, f"Expected 'Company Name Inc', got '{result}'"
        
        return True, "Above direction extraction works"
    except Exception as e:
        return False, f"Error testing above direction: {e}"


def test_number_extraction():
    """Test extracting numbers specifically."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Total Amount: $1,234.56 USD"
        pattern = {
            'keyword': 'Total Amount:',
            'direction': 'right',
            'distance': 0,
            'extract_type': 'number'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        # Should extract the number portion
        if result not in ["1,234.56", "1234.56"]:
            return False, f"Expected number extraction, got '{result}'"
        
        return True, "Number extraction works"
    except Exception as e:
        return False, f"Error testing number extraction: {e}"


def test_text_extraction():
    """Test extracting remaining text from position."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Description: High quality widgets for testing purposes"
        pattern = {
            'keyword': 'Description:',
            'direction': 'right',
            'distance': 0,
            'extract_type': 'text'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        expected = "High quality widgets for testing purposes"
        if result != expected:
            return False, f"Expected '{expected}', got '{result}'"
        
        return True, "Text extraction works"
    except Exception as e:
        return False, f"Error testing text extraction: {e}"


def test_pattern_not_found():
    """Test handling when pattern is not found."""
    try:
        extractor = PatternExtractor()
        
        test_text = "No relevant content here"
        pattern = {
            'keyword': 'Missing Keyword',
            'direction': 'right',
            'distance': 1,
            'extract_type': 'word'
        }
        
        result = extractor.extract_pattern(test_text, pattern)
        if result is not None:
            return False, f"Expected None for missing pattern, got '{result}'"
        
        return True, "Missing pattern handled correctly"
    except Exception as e:
        return False, f"Error testing missing pattern: {e}"


def test_multiple_patterns():
    """Test extracting multiple patterns from same text."""
    try:
        extractor = PatternExtractor()
        
        test_text = "Invoice: 12345\nDate: 2024-01-15\nTotal: $567.89"
        patterns = [
            {
                'keyword': 'Invoice:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'word'
            },
            {
                'keyword': 'Total:',
                'direction': 'right',
                'distance': 0,
                'extract_type': 'text'
            }
        ]
        
        results = extractor.extract_multiple_patterns(test_text, patterns)
        
        if len(results) != 2:
            return False, f"Expected 2 results, got {len(results)}"
        
        if results[0] != "12345":
            return False, f"First pattern failed: got '{results[0]}'"
        
        if "$567.89" not in str(results[1]):
            return False, f"Second pattern failed: got '{results[1]}'"
        
        return True, "Multiple pattern extraction works"
    except Exception as e:
        return False, f"Error testing multiple patterns: {e}"


def run_tests():
    """Run all extractor tests and return results."""
    tests = [
        test_pattern_extractor_initialization,
        test_keyword_finding,
        test_right_direction_extraction,
        test_left_direction_extraction,
        test_below_direction_extraction,
        test_above_direction_extraction,
        test_number_extraction,
        test_text_extraction,
        test_pattern_not_found,
        test_multiple_patterns
    ]
    
    results = []
    passed = 0
    total = len(tests)
    
    print("Testing Pattern Extractors")
    print("=" * 50)
    
    for test_func in tests:
        test_name = test_func.__name__
        try:
            success, message = test_func()
            if success:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"
            
            print(f"{status:4} | {test_name:35} | {message}")
            results.append((test_name, success, message))
            
        except Exception as e:
            print(f"ERROR| {test_name:35} | Unexpected error: {e}")
            results.append((test_name, False, f"Unexpected error: {e}"))
    
    print("-" * 50)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total, results


def main():
    """Main test runner."""
    success, results = run_tests()
    return 1 if success else 0


if __name__ == "__main__":
    exit(main())
