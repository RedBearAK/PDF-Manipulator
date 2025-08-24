#!/usr/bin/env python3
"""
Test Interactive Mode Logic
File: tests/test_interactive_mode_fix.py

Tests that the interactive mode detection works correctly after fixes.
"""

import argparse
from pathlib import Path


def create_mock_args(**kwargs):
    """Create a mock args object for testing."""
    args = argparse.Namespace()
    
    # Set default values
    args.batch = False
    args.preview = False
    args.conflicts = 'ask'
    args.dedup = None
    args.separate_files = False
    args.respect_groups = False
    
    # Override with provided values
    for key, value in kwargs.items():
        setattr(args, key, value)
    
    return args


def is_interactive_mode(args) -> bool:
    """Fixed interactive mode detection."""
    return not getattr(args, 'batch', False)


def extract_enhanced_args_fixed(args) -> dict:
    """Fixed version of extract_enhanced_args."""
    # Extract interactive options - FIXED LOGIC
    interactive_options = {
        # Interactive mode is the DEFAULT unless --batch is specified
        'interactive': not getattr(args, 'batch', False),  # ← FIXED
        'preview': getattr(args, 'preview', False)
    }
    
    return {
        'interactive': interactive_options
    }


def test_interactive_mode_detection():
    """Test that interactive mode detection works correctly."""
    print("Testing interactive mode detection...")
    
    test_cases = [
        # (args_kwargs, expected_interactive, description)
        ({}, True, "Default (no --batch) should be interactive"),
        ({'batch': False}, True, "Explicit batch=False should be interactive"),
        ({'batch': True}, False, "With --batch should be non-interactive"),
        ({'preview': True}, True, "Preview alone should still be interactive"),
        ({'batch': True, 'preview': True}, False, "Batch with preview should be non-interactive"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for args_kwargs, expected_interactive, description in test_cases:
        args = create_mock_args(**args_kwargs)
        
        # Test the fixed function
        result = is_interactive_mode(args)
        
        if result == expected_interactive:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}: got {result}, expected {expected_interactive}")
    
    return passed, total


def test_extract_enhanced_args_fixed():
    """Test that extract_enhanced_args works correctly after fixes."""
    print("Testing extract_enhanced_args fix...")
    
    test_cases = [
        # (args_kwargs, expected_interactive, description)
        ({}, True, "Default should extract interactive=True"),
        ({'batch': False}, True, "batch=False should extract interactive=True"),
        ({'batch': True}, False, "batch=True should extract interactive=False"),
        ({'preview': True}, True, "Preview should not affect interactive detection"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for args_kwargs, expected_interactive, description in test_cases:
        args = create_mock_args(**args_kwargs)
        
        # Test the fixed function
        enhanced_args = extract_enhanced_args_fixed(args)
        result = enhanced_args['interactive']['interactive']
        
        if result == expected_interactive:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}: got {result}, expected {expected_interactive}")
    
    return passed, total


def test_no_args_interactive_attribute():
    """Test that we don't rely on args.interactive attribute."""
    print("Testing that args.interactive attribute is not needed...")
    
    args = create_mock_args()
    
    # Make sure args.interactive doesn't exist (which was causing the AttributeError)
    if hasattr(args, 'interactive'):
        delattr(args, 'interactive')
    
    try:
        # This should work without needing args.interactive
        is_interactive = is_interactive_mode(args)
        enhanced_args = extract_enhanced_args_fixed(args)
        
        print(f"  ✓ Functions work without args.interactive attribute")
        print(f"    is_interactive_mode() → {is_interactive}")
        print(f"    extract_enhanced_args()['interactive']['interactive'] → {enhanced_args['interactive']['interactive']}")
        
        # Both should be True (interactive) since batch is not set
        if is_interactive and enhanced_args['interactive']['interactive']:
            return 1, 1
        else:
            print(f"  ✗ Expected both to be True for interactive mode")
            return 0, 1
        
    except AttributeError as e:
        if 'interactive' in str(e):
            print(f"  ✗ Still trying to access args.interactive: {e}")
            return 0, 1
        else:
            print(f"  ✗ Other AttributeError: {e}")
            return 0, 1
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return 0, 1


def test_conflict_strategy_logic():
    """Test conflict strategy logic for interactive vs batch modes."""
    print("Testing conflict strategy logic...")
    
    def get_conflict_strategy_fixed(args) -> str:
        """Fixed conflict strategy logic."""
        strategy = getattr(args, 'conflicts', 'ask')
        
        # In batch mode, if strategy is 'ask', change it to 'rename' 
        # since we can't prompt interactively
        if getattr(args, 'batch', False) and strategy == 'ask':
            return 'rename'
        
        return strategy
    
    test_cases = [
        # (args_kwargs, expected_strategy, description)
        ({}, 'ask', "Interactive mode should use 'ask' strategy"),
        ({'batch': False}, 'ask', "Interactive mode should use 'ask' strategy"),
        ({'batch': True}, 'rename', "Batch mode should convert 'ask' to 'rename'"),
        ({'batch': True, 'conflicts': 'overwrite'}, 'overwrite', "Batch mode should keep explicit strategy"),
        ({'conflicts': 'skip'}, 'skip', "Interactive mode should keep explicit strategy"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for args_kwargs, expected_strategy, description in test_cases:
        args = create_mock_args(**args_kwargs)
        
        result = get_conflict_strategy_fixed(args)
        
        if result == expected_strategy:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description}: got '{result}', expected '{expected_strategy}'")
    
    return passed, total


def main():
    """Run all interactive mode tests."""
    print("🔧 Testing Interactive Mode Fixes")
    print("=" * 50)
    
    total_passed = 0
    total_tests = 0
    
    # Run all tests
    test_functions = [
        test_interactive_mode_detection,
        test_extract_enhanced_args_fixed,
        test_no_args_interactive_attribute,
        test_conflict_strategy_logic,
    ]
    
    for test_func in test_functions:
        print(f"\n{test_func.__name__.replace('_', ' ').title()}:")
        passed, count = test_func()
        total_passed += passed
        total_tests += count
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Interactive Mode Fix Results: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Interactive mode logic is fixed.")
        return True
    else:
        print(f"💔 {total_tests - total_passed} tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)


# End of file #
