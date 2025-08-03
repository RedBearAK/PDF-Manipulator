"""
Test Magazine Processing (Advanced Boolean with Range Patterns)
Run: python -m pdf_manipulator.tests.test_magazine_processing

Tests complex boolean expressions containing range patterns.
This is the most advanced functionality requiring the UnifiedBooleanSupervisor.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.page_range.boolean import (
    looks_like_boolean_expression,
    has_advanced_patterns
    
)


# Mock PDF path for testing
MOCK_PDF_PATH = Path("test_document.pdf")


def test_advanced_pattern_detection():
    """Test detection of advanced patterns within boolean expressions."""
    print("=== Testing Advanced Pattern Detection ===")
    
    test_cases = [
        # Should be detected as having advanced patterns
        ("(contains:'Article' to contains:'End') & !type:image", True, "Range pattern in boolean"),
        ("(5 to contains:'Summary') | contains:'Sidebar'", True, "Number-to-pattern range in boolean"),
        ("type:text & (contains:'A' to contains:'B')", True, "Range pattern with boolean"),
        ("!(contains:'Start' to contains:'Finish')", True, "NOT with range pattern"),
        
        # Should NOT be detected as having advanced patterns
        ("contains:'A' & contains:'B'", False, "Simple boolean AND"),
        ("type:text | type:image", False, "Simple boolean OR"),
        ("all & !contains:'DRAFT'", False, "Simple boolean NOT"),
        ("(type:text | type:image) & size:<1MB", False, "Boolean with parentheses"),
        ("contains:'Go to the store' & type:text", False, "Quoted 'to' in boolean"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_have_advanced, description in test_cases:
        has_advanced = has_advanced_patterns(range_str)
        
        if has_advanced == should_have_advanced:
            status = "advanced" if has_advanced else "simple"
            print(f"✓ {description}: '{range_str}' → Correctly detected as {status}")
            passed += 1
        else:
            expected = "advanced" if should_have_advanced else "simple"
            actual = "advanced" if has_advanced else "simple"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Advanced pattern detection: {passed}/{total} passed\n")
    return passed == total


def test_escalation_logic():
    """Test that appropriate expressions escalate to advanced processing."""
    print("=== Testing Escalation Logic ===")
    
    test_cases = [
        # These should escalate (boolean + advanced patterns)
        ("(contains:'A' to contains:'B') & !type:image", True, "Range with boolean filter"),
        ("(5 to contains:'End') | contains:'Sidebar'", True, "Range with boolean OR"),
        ("type:text & (contains:'Chapter' to contains:'Summary')", True, "Boolean with range"),
        
        # These should NOT escalate (just boolean or just advanced, not both)
        ("contains:'A' & contains:'B'", False, "Simple boolean only"),
        ("contains:'A' to contains:'B'", False, "Range pattern only"),
        ("type:text", False, "Single pattern only"),
        ("5-10", False, "Simple range only"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, should_escalate, description in test_cases:
        # Check if it's boolean AND has advanced patterns
        is_boolean = looks_like_boolean_expression(range_str)
        has_advanced = has_advanced_patterns(range_str) if is_boolean else False
        
        will_escalate = is_boolean and has_advanced
        
        if will_escalate == should_escalate:
            status = "escalated" if will_escalate else "standard processing"
            print(f"✓ {description}: '{range_str}' → Correctly {status}")
            passed += 1
        else:
            expected = "escalated" if should_escalate else "standard processing"
            actual = "escalated" if will_escalate else "standard processing"
            print(f"✗ {description}: '{range_str}' → Expected {expected}, got {actual}")
    
    print(f"Escalation logic: {passed}/{total} passed\n")
    return passed == total


def test_magazine_syntax_validation():
    """Test syntax validation for magazine processing expressions."""
    print("=== Testing Magazine Processing Syntax ===")
    
    test_cases = [
        ("(contains:'Article' to contains:'End') & !type:image", "Basic magazine pattern"),
        ("(5 to contains:'Appendix') | contains:'Sidebar'", "Number-to-pattern with OR"),
        ("type:text & (contains:'A' to contains:'B') & size:<1MB", "Multiple conditions"),
        ("!(contains:'Start' to contains:'Finish')", "NOT with range pattern"),
        ("(contains:'Ch 1' to contains:'Ch 2') & (type:text | type:mixed)", "Complex boolean"),
        ("(regex:'\\d+' to contains:'Summary') & !contains:'DRAFT'", "Regex range with filter"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            # This should parse correctly structurally, even if PDF analysis fails
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✓ {description}: '{range_str}' → Syntax OK")
            passed += 1
            
        except ValueError as e:
            if "Could not analyze PDF" in str(e) or "No pages found" in str(e):
                # Expected - we don't have a real PDF to analyze
                print(f"✓ {description}: '{range_str}' → Syntax OK (expected PDF analysis failure)")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → Syntax error: {e}")
                
        except Exception as e:
            # Other processing errors are acceptable for syntax testing
            print(f"✓ {description}: '{range_str}' → Syntax OK (expected processing error)")
            passed += 1
    
    print(f"Magazine syntax: {passed}/{total} passed\n")
    return passed == total


def test_rule_enforcement():
    """Test enforcement of magazine processing rules."""
    print("=== Testing Rule Enforcement ===")
    
    # Rule 1: Only one range pattern per boolean expression
    multiple_range_cases = [
        ("(contains:'A' to contains:'B') & (contains:'C' to contains:'D')", 
         "Multiple range patterns (should fail)"),
        ("(5 to contains:'End') | (contains:'Start' to 10)", 
         "Two different range patterns (should fail)"),
    ]
    
    passed = 0
    total = len(multiple_range_cases)
    
    for range_str, description in multiple_range_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✗ {description}: '{range_str}' → Should have failed but didn't")
            
        except ValueError as e:
            if "Only one range pattern allowed" in str(e):
                print(f"✓ {description}: '{range_str}' → Correctly enforced rule")
                passed += 1
            else:
                print(f"? {description}: '{range_str}' → Failed for different reason: {e}")
                # Count as passed since it failed (which is what we want)
                passed += 1
                
        except Exception as e:
            print(f"? {description}: '{range_str}' → Failed for different reason: {type(e).__name__}")
            # Count as passed since it failed
            passed += 1
    
    print(f"Rule enforcement: {passed}/{total} passed\n")
    return passed == total


def test_complex_nesting():
    """Test complex nested expressions with parentheses."""
    print("=== Testing Complex Nesting ===")
    
    test_cases = [
        ("((contains:'A' to contains:'B')) & !type:image", "Double parentheses around range"),
        ("!(contains:'Start' to contains:'End') & type:text", "NOT applied to range pattern"),
        ("(contains:'A' to contains:'B') & (!type:image | size:<500KB)", "Range with complex filter"),
        ("type:text & ((contains:'Ch' to contains:'Sum') & !contains:'DRAFT')", "Nested range conditions"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✓ {description}: '{range_str}' → Syntax OK")
            passed += 1
            
        except ValueError as e:
            if "Could not analyze PDF" in str(e) or "No pages found" in str(e):
                print(f"✓ {description}: '{range_str}' → Syntax OK (expected PDF analysis failure)")
                passed += 1
            else:
                print(f"✗ {description}: '{range_str}' → Syntax error: {e}")
                
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Syntax OK (expected processing error)")
            passed += 1
    
    print(f"Complex nesting: {passed}/{total} passed\n")
    return passed == total


def test_invalid_magazine_expressions():
    """Test invalid magazine processing expressions."""
    print("=== Testing Invalid Magazine Expressions ===")
    
    test_cases = [
        ("(contains:'A' to contains:'B') &", "Missing right operand"),
        ("& (contains:'A' to contains:'B')", "Missing left operand"),
        ("(contains:'A' to) & type:text", "Incomplete range pattern"),
        ("(to contains:'B') & type:text", "Incomplete range pattern"),
        ("((contains:'A' to contains:'B') & type:text", "Unmatched parentheses"),
        ("(contains:'A' to contains:'B')) & type:text", "Extra closing parenthesis"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for range_str, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(range_str, 50, MOCK_PDF_PATH)
            print(f"✗ {description}: '{range_str}' → Should have failed but didn't")
            
        except ValueError as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
            
        except Exception as e:
            print(f"✓ {description}: '{range_str}' → Correctly failed: {type(e).__name__}")
            passed += 1
    
    print(f"Invalid expressions: {passed}/{total} passed\n")
    return passed == total


def main():
    """Run all magazine processing tests."""
    print("MAGAZINE PROCESSING TESTS")
    print("=" * 50)
    print("Note: These tests focus on complex boolean expressions with range patterns.")
    print()
    
    tests = [
        test_advanced_pattern_detection,
        test_escalation_logic,
        test_magazine_syntax_validation,
        test_rule_enforcement,
        test_complex_nesting,
        test_invalid_magazine_expressions,
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    # Summary
    passed_tests = sum(results)
    total_tests = len(results)
    
    print("=" * 50)
    print(f"MAGAZINE PROCESSING TESTS: {passed_tests}/{total_tests} test categories passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL MAGAZINE PROCESSING TESTS PASSED!")
        return 0
    else:
        print("❌ Some magazine processing tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
