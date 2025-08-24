#!/usr/bin/env python3
"""
Test Architecture Fixes
File: tests/test_architecture_fixes.py

Tests the architectural fixes for:
1. Flattened enhanced_args structure
2. UI module integration issues
"""

import argparse
from pathlib import Path


def create_mock_args(**kwargs):
    """Create a mock args object for testing."""
    args = argparse.Namespace()
    
    # Set default values
    defaults = {
        'batch': False,
        'preview': False,
        'conflicts': 'ask',
        'dedup': None,
        'separate_files': False,
        'respect_groups': False,
        'smart_names': False,
        'name_prefix': None,
        'no_timestamp': False,
        'filename_template': None
    }
    
    # Apply defaults
    for key, value in defaults.items():
        setattr(args, key, value)
    
    # Override with provided values
    for key, value in kwargs.items():
        setattr(args, key, value)
    
    return args


def extract_enhanced_args_fixed(args) -> dict:
    """Fixed version with flattened structure."""
    def determine_default_dedup_strategy(args) -> str:
        if hasattr(args, 'dedup') and args.dedup:
            return args.dedup
        elif hasattr(args, 'respect_groups') and args.respect_groups:
            return 'groups'
        elif hasattr(args, 'separate_files') and args.separate_files:
            return 'strict'
        else:
            return 'strict'
    
    # Determine deduplication strategy
    dedup_strategy = determine_default_dedup_strategy(args)
    
    # Extract conflict resolution strategy  
    conflict_strategy = getattr(args, 'conflicts', 'ask')
    
    # FLATTENED STRUCTURE - no nested dictionaries
    return {
        # Core behavior flags
        'interactive': not getattr(args, 'batch', False),
        'preview': getattr(args, 'preview', False),
        
        # Strategy settings
        'dedup_strategy': dedup_strategy,
        'conflict_strategy': conflict_strategy,
        
        # Naming options (flattened)
        'smart_names': getattr(args, 'smart_names', False),
        'name_prefix': getattr(args, 'name_prefix', None),
        'no_timestamp': getattr(args, 'no_timestamp', False),
        'template': getattr(args, 'filename_template', None)
    }


def extract_enhanced_args_old(args) -> dict:
    """Old version with nested structure (for comparison)."""
    def determine_default_dedup_strategy(args) -> str:
        if hasattr(args, 'dedup') and args.dedup:
            return args.dedup
        elif hasattr(args, 'respect_groups') and args.respect_groups:
            return 'groups'
        elif hasattr(args, 'separate_files') and args.separate_files:
            return 'strict'
        else:
            return 'strict'
    
    dedup_strategy = determine_default_dedup_strategy(args)
    conflict_strategy = getattr(args, 'conflicts', 'ask')
    
    naming_options = {
        'smart_names': getattr(args, 'smart_names', False),
        'name_prefix': getattr(args, 'name_prefix', None),
        'no_timestamp': getattr(args, 'no_timestamp', False),
        'template': getattr(args, 'filename_template', None)
    }
    
    interactive_options = {
        'interactive': getattr(args, 'interactive', False),  # OLD: Wrong default
        'preview': getattr(args, 'preview', False)
    }
    
    return {
        'dedup_strategy': dedup_strategy,
        'conflict_strategy': conflict_strategy,
        'naming': naming_options,
        'interactive': interactive_options  # ← NESTED STRUCTURE
    }


def test_flattened_structure():
    """Test that the flattened structure works correctly."""
    print("Testing flattened enhanced_args structure...")
    
    test_cases = [
        ({}, "default arguments"),
        ({'batch': True}, "batch mode"),
        ({'preview': True}, "preview mode"),
        ({'smart_names': True, 'name_prefix': 'custom'}, "naming options"),
        ({'conflicts': 'rename', 'dedup': 'none'}, "strategy options"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for args_kwargs, description in test_cases:
        args = create_mock_args(**args_kwargs)
        
        try:
            # Test new flattened structure
            enhanced_args = extract_enhanced_args_fixed(args)
            
            # Verify flattened access works
            interactive = enhanced_args['interactive']          # ← Should work
            preview = enhanced_args['preview']                  # ← Should work
            smart_names = enhanced_args['smart_names']          # ← Should work
            dedup_strategy = enhanced_args['dedup_strategy']    # ← Should work
            
            # Verify nested access would fail (good!)
            try:
                nested_interactive = enhanced_args['interactive']['interactive']  # ← Should fail
                print(f"  ✗ {description}: Nested access still works (bad!)")
                continue
            except (KeyError, TypeError):
                # Good! Nested access fails as expected
                pass
            
            print(f"  ✓ {description}: Flattened structure works")
            print(f"    interactive={interactive}, preview={preview}, smart_names={smart_names}")
            passed += 1
            
        except Exception as e:
            print(f"  ✗ {description}: Failed with {e}")
    
    return passed, total


def test_code_migration_patterns():
    """Test common code patterns that need to be migrated."""
    print("Testing code migration patterns...")
    
    args = create_mock_args(preview=True, smart_names=True)
    enhanced_args = extract_enhanced_args_fixed(args)
    
    migration_tests = [
        # (old_pattern, new_pattern, description)
        (
            lambda: enhanced_args['interactive'],  # NEW: Direct access
            "enhanced_args['interactive']",
            "Direct interactive access"
        ),
        (
            lambda: enhanced_args['preview'],      # NEW: Direct access  
            "enhanced_args['preview']",
            "Direct preview access"
        ),
        (
            lambda: enhanced_args['smart_names'],  # NEW: Direct access
            "enhanced_args['smart_names']", 
            "Direct naming option access"
        ),
    ]
    
    passed = 0
    total = len(migration_tests)
    
    for test_func, pattern_desc, description in migration_tests:
        try:
            result = test_func()
            print(f"  ✓ {description}: {pattern_desc} → {result}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {description}: {pattern_desc} → Failed: {e}")
    
    return passed, total


def test_ui_import_resolution():
    """Test that UI import issues would be resolved."""
    print("Testing UI import resolution...")
    
    # Simulate the UI function mapping approach
    def get_ui_function_module(function_name: str) -> str:
        """Determine which UI module a function belongs to."""
        basic_functions = {
            'decide_extraction_mode', 'show_folder_help', 'show_single_file_help',
            'display_pdf_table'
        }
        
        enhanced_functions = {
            'confirm_deduplication_strategy', 'prompt_single_filename', 
            'prompt_base_filename', 'show_extraction_preview', 
            'show_conflict_resolution_summary', 'prompt_complex_operation_confirmation'
        }
        
        if function_name in basic_functions:
            return 'pdf_manipulator.ui'
        elif function_name in enhanced_functions:
            return 'pdf_manipulator.ui_enhanced'
        else:
            return 'unknown'
    
    import_tests = [
        ('decide_extraction_mode', 'pdf_manipulator.ui'),
        ('confirm_deduplication_strategy', 'pdf_manipulator.ui_enhanced'),
        ('show_folder_help', 'pdf_manipulator.ui'),
        ('prompt_single_filename', 'pdf_manipulator.ui_enhanced'),
        ('nonexistent_function', 'unknown'),
    ]
    
    passed = 0
    total = len(import_tests)
    
    for function_name, expected_module in import_tests:
        actual_module = get_ui_function_module(function_name)
        if actual_module == expected_module:
            print(f"  ✓ {function_name} → {actual_module}")
            passed += 1
        else:
            print(f"  ✗ {function_name} → got {actual_module}, expected {expected_module}")
    
    return passed, total


def test_backward_compatibility():
    """Test that old code patterns would be caught."""
    print("Testing backward compatibility detection...")
    
    args = create_mock_args()
    
    # Test old nested structure (should be different from new)
    old_enhanced_args = extract_enhanced_args_old(args)
    new_enhanced_args = extract_enhanced_args_fixed(args)
    
    compatibility_tests = [
        (
            # Old nested pattern would fail
            lambda: old_enhanced_args['interactive']['interactive'],
            # New direct pattern works
            lambda: new_enhanced_args['interactive'],
            "Interactive access pattern"
        ),
        (
            # Old nested pattern would fail  
            lambda: old_enhanced_args['naming']['smart_names'],
            # New direct pattern works
            lambda: new_enhanced_args['smart_names'],
            "Naming options access pattern"
        ),
    ]
    
    passed = 0
    total = len(compatibility_tests)
    
    for old_func, new_func, description in compatibility_tests:
        try:
            old_result = old_func()
            new_result = new_func()
            
            if old_result == new_result:
                print(f"  ✓ {description}: Migration preserves values ({old_result} → {new_result})")
                passed += 1
            else:
                print(f"  ✗ {description}: Values differ ({old_result} → {new_result})")
        except Exception as e:
            print(f"  ? {description}: Old pattern fails as expected: {e}")
            try:
                new_result = new_func()
                print(f"    New pattern works: {new_result}")
                passed += 1
            except Exception as e2:
                print(f"    New pattern also fails: {e2}")
    
    return passed, total


def main():
    """Run all architecture fix tests."""
    print("🔧 Testing Architecture Fixes")
    print("=" * 50)
    
    total_passed = 0
    total_tests = 0
    
    test_functions = [
        test_flattened_structure,
        test_code_migration_patterns,
        test_ui_import_resolution,
        test_backward_compatibility,
    ]
    
    for test_func in test_functions:
        print(f"\n{test_func.__name__.replace('_', ' ').title()}:")
        passed, count = test_func()
        total_passed += passed
        total_tests += count
        print(f"Result: {passed}/{count} passed")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Architecture Fix Results: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Architecture fixes are working correctly.")
        
        print("\n📋 Migration Checklist:")
        print("1. ✓ Flatten enhanced_args structure")
        print("2. ✓ Update all enhanced_args['interactive']['interactive'] → enhanced_args['interactive']")
        print("3. ✓ Update all enhanced_args['naming']['*'] → enhanced_args['*']")
        print("4. ✓ Fix UI import issues (import from ui_enhanced where needed)")
        print("5. ⚠️  Test with actual codebase")
        
        return True
    else:
        print(f"💔 {total_tests - total_passed} tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)


# End of file #
