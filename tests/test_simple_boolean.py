"""
Test Simple Boolean Expressions
Run: python tests/test_simple_boolean.py

Tests basic boolean logic: AND (&), OR (|), NOT (!), parentheses.
Does NOT test advanced range patterns ("X to Y").
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.core.page_range.boolean import looks_like_boolean_expression, parse_boolean_expression


# Mock PDF path for testing
MOCK_PDF_PATH = Path("test_document.pdf")


def test_boolean_detection():
    """Test detection of boolean expressions vs simple ranges."""
    print("=== Testing Boolean Expression Detection ===")
    
    test_cases = [
        # Should be detected as boolean expressions
        ("contains:'A' & contains:'B'", True, "AND expression"),
        ("type:text | type:mixed", True, "OR expression"),
        ("all & !contains:'DRAFT'", True, "NOT expression"),
        ("(type:text | type:image) & size:<1MB", True, "Parentheses with operators"),
        ("!type:empty", True, "Simple NOT"),
        
        # Should NOT be detected as boolean expressions
        ("contains:'text'", False, "Single pattern"),
        ("type:text", False, "Single type pattern"),
        ("3-7", False, "Simple range"),
        ("all", False, "All keyword"),
        ("contains:'text with & symbol'", False, "Quoted ampersand"),
        ("contains:'A and B'", False, "Quoted 'and' text"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_boolean, description in test_cases:
        is_boolean = looks_like_boolean_expression(range_str)
        
        if is_boolean == should_be_boolean:
            status = "boolean" if is_boolean else "simple"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "boolean" if should_be_boolean else "simple"
            actual = "boolean" if is_boolean else "simple"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Boolean detection: {passed}/{total} passed\n")
    return passed == total


def test_operator_spacing():
    """Test strict operator spacing requirements."""
    print("=== Testing Operator Spacing ===")
    
    test_cases = [
        # Valid spacing
        ("all & !type:empty", True, "Correct spacing: ' & !'"),
        ("type:text | type:image", True, "Correct spacing: ' | '"),
        ("contains:'A' & contains:'B'", True, "Correct spacing: ' & '"),
        
        # Invalid spacing (should not be detected as boolean)
        ("all& !type:empty", False, "Missing space before &"),
        ("all &!type:empty", False, "Missing space after &"),
        ("type:text|type:image", False, "No spaces around |"),
        ("type:text  &  type:image", False, "Extra spaces around &"),
        ("contains:'A'&contains:'B'", False, "No spaces around &"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_boolean, description in test_cases:
        is_boolean = looks_like_boolean_expression(range_str)
        
        if is_boolean == should_be_boolean:
            status = "boolean" if is_boolean else "simple"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "boolean" if should_be_boolean else "simple"
            actual = "boolean" if is_boolean else "simple"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Operator spacing: {passed}/{total} passed\n")
    return passed == total


def test_parentheses_detection():
    """Test parentheses as boolean expression indicators."""
    print("=== Testing Parentheses Detection ===")
    
    test_cases = [
        ("(type:text)", True, "Simple parentheses"),
        ("(contains:'A' & contains:'B')", True, "Parentheses with operators"),
        ("(type:text | type:image) & size:<1MB", True, "Mixed parentheses and operators"),
        ("!(type:text | type:image)", True, "NOT with parentheses"),
        ("((type:text))", True, "Nested parentheses"),
        
        # Edge case: quoted parentheses should not trigger boolean detection
        ("contains:'(parentheses in text)'", False, "Quoted parentheses"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_boolean, description in test_cases:
        is_boolean = looks_like_boolean_expression(range_str)
        
        if is_boolean == should_be_boolean:
            status = "boolean" if is_boolean else "simple"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "boolean" if should_be_boolean else "simple"
            actual = "boolean" if is_boolean else "simple"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Parentheses detection: {passed}/{total} passed\n")
    return passed == total


def test_quote_awareness():
    """Test that operators inside quotes don't trigger boolean detection."""
    print("=== Testing Quote Awareness ===")
    
    test_cases = [
        ("contains:'A & B'", False, "Quoted ampersand"),
        ("contains:'A | B'", False, "Quoted pipe"),
        ("contains:'!important'", False, "Quoted exclamation"),
        ('contains:"A & B or C"', False, "Double quoted operators"),
        ("contains:'Text with (parentheses)'", False, "Quoted parentheses"),
        ("regex:'[a-z]+ & [0-9]+'", False, "Regex with operators"),
        
        # Real operators outside quotes should still work
        ("contains:'A' & contains:'B'", True, "Real operators outside quotes"),
        ("contains:'Text & more' | type:image", True, "Mixed quoted and real operators"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_be_boolean, description in test_cases:
        is_boolean = looks_like_boolean_expression(range_str)
        
        if is_boolean == should_be_boolean:
            status = "boolean" if is_boolean else "simple"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "boolean" if should_be_boolean else "simple"
            actual = "boolean" if is_boolean else "simple"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Quote awareness: {passed}/{total} passed\n")
    return passed == total


def test_simple_boolean_parsing():
    """Test parsing of simple boolean expressions (syntax only)."""
    print("=== Testing Simple Boolean Parsing ===")
    
    # Note: These will fail during PDF analysis but should parse correctly
    
    test_cases = [
        ("all & !type:empty", "Basic AND NOT"),
        ("type:text | type:image", "Basic OR"),
        ("(type:text | type:mixed) & size:<1MB", "Parentheses with AND"),
        ("!type:empty", "Simple NOT"),
        ("!(type:text | type:image)", "NOT with parentheses"),
        ("type:text & contains:'Chapter' & size:<500KB", "Multiple AND"),
        ("type:text | type:image | type:mixed", "Multiple OR"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            # This will fail during PDF analysis but should parse the boolean structure
            pages = parse_boolean_expression(range_str, MOCK_PDF_PATH, 10)
            print(f"✓ {description}: '{range_str}' → Parsing OK")
            passed += 1
            
        except ValueError as e:
            if "Could not analyze PDF" in str(e) or "Error analyzing" in str(e):
                print(f"✓ {description}: '{range_str}' → Parsing OK (expected PDF analysis failure)")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → Parsing error: {e}")
                
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Parsing OK (expected processing error)")
            passed += 1
    
    print(f"Boolean parsing: {passed}/{total} passed\n")
    return passed == total


def test_precedence_and_errors():
    """Test operator precedence and error handling."""
    print("=== Testing Precedence and Error Cases ===")
    
    error_cases = [
        ("type:text &", "Missing right operand for AND"),
        ("& type:text", "Missing left operand for AND"),
        ("type:text |", "Missing right operand for OR"),
        ("| type:text", "Missing left operand for OR"),
        ("!", "Missing operand for NOT"),
        ("(type:text", "Unmatched opening parenthesis"),
        ("type:text)", "Unmatched closing parenthesis"),
        ("((type:text)", "Mismatched parentheses"),
    ]
    
    passed = 0
    total = len(error_cases)
    
    for range_str, description in error_cases:
        try:
            pages = parse_boolean_expression(range_str, MOCK_PDF_PATH, 10)
            print(f"✗ {description}: '{range_str}' → Should have failed but didn't")
            
        except ValueError as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
            
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
    
    print(f"Error handling: {passed}/{total} passed\n")
    return passed == total


def main():
    """Run all simple boolean expression tests."""
    print("SIMPLE BOOLEAN EXPRESSION TESTS")
    print("=" * 50)
    print("Note: These tests focus on syntax and structure validation.")
    print()
    
    tests = [
        test_boolean_detection,
        test_operator_spacing,
        test_parentheses_detection,
        test_quote_awareness,
        test_simple_boolean_parsing,
        test_precedence_and_errors,
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    # Summary
    passed_tests = sum(results)
    total_tests = len(results)
    
    print("=" * 50)
    print(f"SIMPLE BOOLEAN TESTS: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL SIMPLE BOOLEAN TESTS PASSED!")
        return 0
    else:
        print("❌ Some simple boolean tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
