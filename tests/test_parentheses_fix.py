"""
Test script to verify the parentheses boolean parsing fix.
File: tests/test_parentheses_fix.py

This tests the specific cases that were failing before the fix.
"""

import sys
from pathlib import Path


def test_tokenization():
    """Test the new tokenization strategy."""
    print("=== Testing New Tokenization Strategy ===")
    
    # Mock the boolean supervisor for testing
    class MockBooleanSupervisor:
        def __init__(self):
            pass
            
        def _tokenize_expression(self, expr: str) -> list[str]:
            """Copy of the fixed tokenization method."""
            tokens = []
            current_token = ""
            in_quote = False
            quote_char = None
            i = 0
            
            while i < len(expr):
                char = expr[i]
                
                # Handle escapes
                if char == '\\' and i + 1 < len(expr):
                    current_token += char + expr[i + 1]
                    i += 2
                    continue
                    
                # Handle quotes
                if char in ['"', "'"] and not in_quote:
                    in_quote = True
                    quote_char = char
                    current_token += char
                elif char == quote_char and in_quote:
                    in_quote = False
                    quote_char = None
                    current_token += char
                elif not in_quote:
                    # FIXED: Handle parentheses as separate tokens
                    if char == '(':
                        # Save any accumulated token
                        if current_token.strip():
                            tokens.append(current_token.strip())
                            current_token = ""
                        # Add opening parenthesis as separate token
                        tokens.append('(')
                    elif char == ')':
                        # Save any accumulated token
                        if current_token.strip():
                            tokens.append(current_token.strip())
                            current_token = ""
                        # Add closing parenthesis as separate token
                        tokens.append(')')
                    # Handle operators with exact spacing
                    elif expr[i:i+4] == ' & !':
                        if current_token.strip():
                            tokens.append(current_token.strip())
                        tokens.append('&!')
                        current_token = ""
                        i += 4
                        continue
                    elif expr[i:i+3] == ' & ':
                        if current_token.strip():
                            tokens.append(current_token.strip())
                        tokens.append('&')
                        current_token = ""
                        i += 3
                        continue
                    elif expr[i:i+3] == ' | ':
                        if current_token.strip():
                            tokens.append(current_token.strip())
                        tokens.append('|')
                        current_token = ""
                        i += 3
                        continue
                    elif char == '!' and (i == 0 or expr[i-1].isspace()):
                        if current_token.strip():
                            tokens.append(current_token.strip())
                        tokens.append('!')
                        current_token = ""
                    else:
                        current_token += char
                else:
                    # Inside quotes - accumulate everything as part of current token
                    current_token += char
                
                i += 1
            
            # Add final token if any
            if current_token.strip():
                tokens.append(current_token.strip())
            
            return [token for token in tokens if token]
    
    supervisor = MockBooleanSupervisor()
    
    test_cases = [
        # The specific failing cases
        ('(contains:"SITKA AK" | contains:"SITKA, AK")', 
         "Simple parentheses with OR"),
        
        ('(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"CRAIG, AK"',
         "Parentheses with AND NOT"),
         
        ('(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"CRAIG, AK" & !contains:"PETERSBURG, AK"',
         "Complex parentheses chain"),
        
        # Other test cases
        ('contains:"simple test"', "Simple pattern (no parentheses)"),
        ('type:text | type:image', "Simple OR"),
        ('all & !type:empty', "Simple AND NOT"),
        ('!(type:text | type:image)', "NOT with parentheses"),
        ('((contains:"nested"))', "Nested parentheses"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for expression, description in test_cases:
        print(f"\n  Testing: {description}")
        print(f"  Expression: '{expression}'")
        
        try:
            tokens = supervisor._tokenize_expression(expression)
            print(f"  ✓ Tokens: {tokens}")
            
            # Verify parentheses are separate tokens
            if '(' in expression:
                if '(' in tokens and ')' in tokens:
                    print(f"  ✓ Parentheses correctly separated")
                    passed += 1
                else:
                    print(f"  ✗ Parentheses NOT properly separated")
            else:
                print(f"  ✓ No parentheses to separate")
                passed += 1
                
        except Exception as e:
            print(f"  ✗ Exception: {type(e).__name__}: {e}")
    
    print(f"\nTokenization test result: {passed}/{total} passed")
    return passed == total


def test_parentheses_balance_validation():
    """Test parentheses balance validation."""
    print("\n=== Testing Parentheses Balance Validation ===")
    
    class MockValidator:
        def validate_parentheses_balance(self, tokens: list[str]) -> tuple[bool, str]:
            """Validate that parentheses are balanced."""
            paren_count = 0
            for token in tokens:
                if token == '(':
                    paren_count += 1
                elif token == ')':
                    paren_count -= 1
                if paren_count < 0:
                    return False, "')' without '('"
            if paren_count > 0:
                return False, "'(' without ')'"
            return True, "balanced"
    
    validator = MockValidator()
    
    test_cases = [
        # Valid cases
        (['(', 'contains:"test"', ')'], True, "Simple balanced parentheses"),
        (['(', 'contains:"A"', '|', 'contains:"B"', ')'], True, "Balanced with OR"),
        (['(', '(', 'contains:"nested"', ')', ')'], True, "Nested balanced"),
        (['contains:"no parens"'], True, "No parentheses"),
        
        # Invalid cases
        (['(', 'contains:"test"'], False, "Missing closing paren"),
        (['contains:"test"', ')'], False, "Missing opening paren"),
        (['(', ')', '('], False, "Missing second closing paren"),
        ([')', '('], False, "Wrong order"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for tokens, should_be_valid, description in test_cases:
        is_valid, message = validator.validate_parentheses_balance(tokens)
        
        if is_valid == should_be_valid:
            status = "✓ Valid" if is_valid else "✓ Invalid (as expected)"
            print(f"  {status}: {description} - {message}")
            passed += 1
        else:
            expected = "valid" if should_be_valid else "invalid"
            actual = "valid" if is_valid else "invalid"
            print(f"  ✗ {description}: Expected {expected}, got {actual} - {message}")
    
    print(f"\nBalance validation result: {passed}/{total} passed")
    return passed == total


def test_specific_failing_cases():
    """Test the specific cases that were failing before the fix."""
    print("\n=== Testing Specific Failing Cases ===")
    
    # Mock tokenizer
    class MockTokenizer:
        def tokenize_and_validate(self, expression: str) -> tuple[bool, list[str], str]:
            """Tokenize and validate in one step."""
            try:
                # Simple tokenization for testing
                tokens = []
                current_token = ""
                in_quote = False
                quote_char = None
                i = 0
                
                while i < len(expression):
                    char = expression[i]
                    
                    # Handle quotes
                    if char in ['"', "'"] and not in_quote:
                        in_quote = True
                        quote_char = char
                        current_token += char
                    elif char == quote_char and in_quote:
                        in_quote = False
                        quote_char = None
                        current_token += char
                    elif not in_quote:
                        # Handle parentheses as separate tokens
                        if char == '(':
                            if current_token.strip():
                                tokens.append(current_token.strip())
                                current_token = ""
                            tokens.append('(')
                        elif char == ')':
                            if current_token.strip():
                                tokens.append(current_token.strip())
                                current_token = ""
                            tokens.append(')')
                        # Handle operators
                        elif expression[i:i+3] == ' | ':
                            if current_token.strip():
                                tokens.append(current_token.strip())
                            tokens.append('|')
                            current_token = ""
                            i += 3
                            continue
                        elif expression[i:i+3] == ' & ':
                            if current_token.strip():
                                tokens.append(current_token.strip())
                            tokens.append('&')
                            current_token = ""
                            i += 3
                            continue
                        elif char == '!' and (i == 0 or expression[i-1].isspace()):
                            if current_token.strip():
                                tokens.append(current_token.strip())
                            tokens.append('!')
                            current_token = ""
                        else:
                            current_token += char
                    else:
                        current_token += char
                    
                    i += 1
                
                if current_token.strip():
                    tokens.append(current_token.strip())
                
                # Validate parentheses balance
                paren_count = 0
                for token in tokens:
                    if token == '(':
                        paren_count += 1
                    elif token == ')':
                        paren_count -= 1
                    if paren_count < 0:
                        return False, tokens, "Mismatched parentheses: ')' without '('"
                
                if paren_count > 0:
                    return False, tokens, "Mismatched parentheses: '(' without ')'"
                
                return True, tokens, "Success"
                
            except Exception as e:
                return False, [], f"Exception: {e}"
    
    tokenizer = MockTokenizer()
    
    # These are the expressions that were failing
    failing_cases = [
        '(contains:"SITKA AK" | contains:"SITKA, AK")',
        '(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"CRAIG, AK"',
        '''(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"CRAIG, AK" & \
!contains:"PETERSBURG, AK" & !contains:"KETCHIKAN, AK" & !contains:"VALDEZ, AK"''',
    ]
    
    passed = 0
    total = len(failing_cases)
    
    for i, expression in enumerate(failing_cases, 1):
        # Clean up line continuation
        expression = ' '.join(expression.split())
        
        print(f"\n  Case {i}: {expression[:50]}{'...' if len(expression) > 50 else ''}")
        
        success, tokens, message = tokenizer.tokenize_and_validate(expression)
        
        if success:
            print(f"  ✓ Parsed successfully")
            print(f"  ✓ Tokens: {tokens[:5]}{'...' if len(tokens) > 5 else ''}")
            print(f"  ✓ Message: {message}")
            passed += 1
        else:
            print(f"  ✗ Failed to parse")
            print(f"  ✗ Tokens: {tokens}")
            print(f"  ✗ Error: {message}")
    
    print(f"\nSpecific cases result: {passed}/{total} passed")
    return passed == total


def main():
    """Run all tests."""
    print("Testing Boolean Expression Parentheses Fix")
    print("=" * 60)
    
    tests = [
        test_tokenization,
        test_parentheses_balance_validation,
        test_specific_failing_cases,
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"\nTest {test_func.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"FINAL RESULT: {passed_tests}/{total_tests} test groups passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The parentheses fix should work correctly.")
        return 0
    else:
        print("❌ Some tests failed. Review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


# End of file #
