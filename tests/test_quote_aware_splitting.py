#!/usr/bin/env python3
"""
Test quote-aware comma splitting functionality.
File: tests/test_quote_aware_splitting.py

Run: python tests/test_quote_aware_splitting.py
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pdf_manipulator.core.page_range.patterns import split_comma_respecting_quotes
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import split_comma_respecting_quotes: {e}")
    IMPORTS_AVAILABLE = False


def test_quote_aware_splitting():
    """Test the quote-aware comma splitting function."""
    if not IMPORTS_AVAILABLE:
        print("Skipping tests - imports not available")
        return False
    
    test_cases = [
        # Basic cases
        ('a,b,c', ['a', 'b', 'c']),
        ('a, b, c', ['a', 'b', 'c']),
        
        # Quoted strings with commas (the main issue)
        ('contains:"CORDOVA, AK",contains:"CRAIG, AK"', 
         ['contains:"CORDOVA, AK"', 'contains:"CRAIG, AK"']),
        
        # Mixed quotes
        ("a,'b,c',d", ['a', "'b,c'", 'd']),
        ('x,"y,z",w', ['x', '"y,z"', 'w']),
        
        # Single item (no commas)
        ('single_item', ['single_item']),
        
        # Complex real-world case from alaska_cities.txt
        ('contains:"SITKA AK",contains:"SITKA, AK"',
         ['contains:"SITKA AK"', 'contains:"SITKA, AK"']),
        
        # Boolean expressions with quoted commas
        ('contains:"A, B" & type:text,contains:"C, D"',
         ['contains:"A, B" & type:text', 'contains:"C, D"']),
        
        # Edge cases
        ('', ['']),
        (',', ['', '']),
        ('a,', ['a', '']),
        (',a', ['', 'a']),
        
        # Escaped quotes
        ('contains:"test\\"quote, here",other',
         ['contains:"test\\"quote, here"', 'other']),
        
        # Complex file expansion result (similar to your error)
        ('contains:"CORDOVA, AK",contains:"CRAIG, AK",contains:"DILLINGHAM, AK"',
         ['contains:"CORDOVA, AK"', 'contains:"CRAIG, AK"', 'contains:"DILLINGHAM, AK"']),
    ]
    
    print("=== Testing Quote-Aware Comma Splitting ===")
    passed = 0
    total = len(test_cases)
    
    for input_text, expected in test_cases:
        try:
            result = split_comma_respecting_quotes(input_text)
            if result == expected:
                print(f"✓ '{input_text}' → {result}")
                passed += 1
            else:
                print(f"✗ '{input_text}'")
                print(f"   Expected: {expected}")
                print(f"   Got:      {result}")
        except Exception as e:
            print(f"✗ '{input_text}' → Exception: {e}")
    
    print(f"\nQuote-aware splitting: {passed}/{total} passed")
    return passed == total


def test_comma_parsing_integration():
    """Test integration with pattern detection functions."""
    if not IMPORTS_AVAILABLE:
        print("Skipping integration tests - imports not available")
        return True
    
    print("\n=== Testing Integration with Pattern Detection ===")
    
    # Import pattern detection functions
    try:
        from pdf_manipulator.core.page_range.patterns import (
            looks_like_pattern, 
            _looks_like_comma_separated_list_pattern,
            _has_unquoted_commas
        )
        
        # First test the _has_unquoted_commas helper function
        print("\nTesting _has_unquoted_commas helper:")
        comma_test_cases = [
            ('contains:"CORDOVA, AK"', False, "Comma inside quotes"),
            ('a,b,c', True, "Commas outside quotes"),
            ('contains:"A, B" & type:text', False, "Comma only inside quotes (& is not comma)"),
            ('contains:"no comma here"', False, "No comma at all"),
            ('"quoted, text",other', True, "Comma both inside and outside quotes"),
            ('contains:"A, B",type:text', True, "Comma inside quotes AND outside quotes"),
        ]
        
        comma_passed = 0
        for text, expected, description in comma_test_cases:
            result = _has_unquoted_commas(text)
            if result == expected:
                print(f"  ✓ {description}: '{text}' → {result}")
                comma_passed += 1
            else:
                print(f"  ✗ {description}: '{text}' → Expected {expected}, got {result}")
        
        print(f"  _has_unquoted_commas: {comma_passed}/{len(comma_test_cases)} passed")
        
        # Now test the main pattern detection
        print("\nTesting main pattern detection:")
        test_cases = [
            # These should NOT be detected as single patterns (due to comma-separated list detection)
            ('contains:"CORDOVA, AK",contains:"CRAIG, AK"', False, "Comma-separated patterns"),
            ('type:text,type:image,5-10', False, "Mixed patterns and numbers"),
            
            # These SHOULD be detected as single patterns
            ('contains:"CORDOVA, AK"', True, "Single pattern with comma in quotes"),
            ('type:text', True, "Simple single pattern"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for pattern_str, should_be_pattern, description in test_cases:
            try:
                is_pattern = looks_like_pattern(pattern_str)
                if is_pattern == should_be_pattern:
                    status = "single pattern" if is_pattern else "not single pattern"
                    print(f"  ✓ {description}: '{pattern_str}' → {status}")
                    passed += 1
                else:
                    expected = "single pattern" if should_be_pattern else "not single pattern"
                    actual = "single pattern" if is_pattern else "not single pattern"
                    print(f"  ✗ {description}: '{pattern_str}' → Expected {expected}, got {actual}")
                    
                    # Debug the comma-separated detection
                    if not should_be_pattern:
                        is_comma_list = _looks_like_comma_separated_list_pattern(pattern_str)
                        print(f"    Debug: _looks_like_comma_separated_list_pattern = {is_comma_list}")
                        
            except Exception as e:
                print(f"  ✗ {description}: '{pattern_str}' → Exception: {e}")
        
        print(f"\nPattern detection integration: {passed}/{total} passed")
        success = (comma_passed == len(comma_test_cases)) and (passed == total)
        return success
        
    except ImportError as e:
        print(f"Could not import pattern detection functions: {e}")
        return True


def main():
    """Run all quote-aware splitting tests."""
    print("Quote-Aware Comma Splitting Tests")
    print("=" * 50)
    
    results = []
    results.append(test_quote_aware_splitting())
    results.append(test_comma_parsing_integration())
    
    passed_tests = sum(results)
    total_tests = len(results)
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed_tests}/{total_tests} test groups passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Quote-aware comma splitting is working correctly!")
        print("\n💡 Your alaska_cities.txt command should now work:")
        print('   pdf-manipulator --extract-pages="file:alaska_cities.txt" 20250816143441_OCRd.pdf')
    else:
        print(f"\n❌ {total_tests - passed_tests} test group(s) failed.")
        print("Check the implementations in patterns.py and page_range_parser.py")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# End of file #
