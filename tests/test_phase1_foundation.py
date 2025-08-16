#!/usr/bin/env python3
"""
Phase 1 foundation test for scraper integration.
File: test_phase1_foundation.py

Tests the basic infrastructure without requiring actual PDF processing.
"""

import sys
from pathlib import Path

# Add the pdf_manipulator package to the path (adjust as needed)
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.renamer.pattern_processor import PatternProcessor, CompactPatternError
from pdf_manipulator.renamer.template_engine import TemplateEngine, TemplateError
from pdf_manipulator.renamer.sanitizer import (
    sanitize_variable_name, 
    sanitize_filename, 
    auto_generate_variable_name
)


def test_compact_pattern_parsing():
    """Test compact pattern syntax parsing."""
    print("Testing compact pattern parsing...")
    
    processor = PatternProcessor()
    
    # Test valid patterns
    valid_patterns = [
        "Invoice Number:r1wd1",
        "company=Company Name:u1ln1", 
        "Total:d1r1nb1-",
        "Description:d2wd0",
        "Balance:u99r99wd99",
        "Amount:nb1-",                  # No movement - extract at keyword
        "Date:u1r2wd3-"
    ]
    
    for pattern in valid_patterns:
        try:
            var_name, keyword, spec = processor.parse_pattern_string(pattern)
            print(f"  ✓ {pattern} -> {var_name}, '{keyword}', {spec}")
        except Exception as e:
            print(f"  ✗ {pattern} failed: {e}")
            return False
    
    # Test invalid patterns
    invalid_patterns = [
        "Invoice Number:r100wd1",  # Distance > 99
        "Total:u1d1wd1",           # Conflicting directions  
        "Amount:u1r2l3wd1",        # Too many movements
        "Company:wd",              # Missing count
        "Invoice:r1zz1",           # Invalid extraction type
    ]
    
    for pattern in invalid_patterns:
        try:
            var_name, keyword, spec = processor.parse_pattern_string(pattern)
            print(f"  ✗ {pattern} should have failed but didn't")
            return False
        except CompactPatternError:
            print(f"  ✓ {pattern} correctly rejected")
        except Exception as e:
            print(f"  ? {pattern} failed with unexpected error: {e}")
    
    return True


def test_template_engine():
    """Test template engine functionality."""
    print("\nTesting template engine...")
    
    engine = TemplateEngine()
    
    # Test template parsing
    template = "{company|Unknown}_{invoice}_{amount|NO-AMT}_pages{range}.pdf"
    
    try:
        variables = engine.parse_template(template)
        expected = [
            ('company', 'Unknown'),
            ('invoice', ''),
            ('amount', 'NO-AMT'),
            ('range', '')
        ]
        
        if variables == expected:
            print(f"  ✓ Template parsing: {variables}")
        else:
            print(f"  ✗ Template parsing failed: got {variables}, expected {expected}")
            return False
            
    except Exception as e:
        print(f"  ✗ Template parsing failed: {e}")
        return False
    
    # Test variable substitution
    test_variables = {
        'company': 'ACME-Corp',
        'invoice': 'INV-2024-001',
        'amount': '1250-00'
    }
    
    built_ins = {
        'range': '01-03',
        'original_name': 'invoice_abc123'
    }
    
    try:
        result = engine.substitute_variables(template, test_variables, built_ins)
        expected = "ACME-Corp_INV-2024-001_1250-00_pages01-03.pdf"
        
        if result == expected:
            print(f"  ✓ Variable substitution: {result}")
        else:
            print(f"  ✗ Variable substitution failed: got '{result}', expected '{expected}'")
            return False
            
    except Exception as e:
        print(f"  ✗ Variable substitution failed: {e}")
        return False
    
    # Test fallback behavior
    test_variables_partial = {
        'invoice': 'INV-2024-001'
        # Missing company and amount - should use fallbacks
    }
    
    try:
        result = engine.substitute_variables(template, test_variables_partial, built_ins)
        # Should use "Unknown" for company, "NO-AMT" for amount
        if "Unknown" in result and "NO-AMT" in result and "INV-2024-001" in result:
            print(f"  ✓ Fallback behavior: {result}")
        else:
            print(f"  ✗ Fallback behavior failed: {result}")
            return False
            
    except Exception as e:
        print(f"  ✗ Fallback behavior failed: {e}")
        return False
    
    return True


def test_sanitization():
    """Test text sanitization functions."""
    print("\nTesting sanitization...")
    
    # Test variable name sanitization
    test_cases = [
        ("Invoice Number", "invoice_number"),
        ("PO#", "po"),
        ("Company Name Ltd.", "company_name_ltd"),
        ("123 Test", "var_123_test"),
        ("Very Long Company Name Limited Corporation", "very_long_company"),  # Test word-aware truncation
        ("", "unknown")
    ]
    
    for input_text, expected in test_cases:
        result = auto_generate_variable_name(input_text)
        if result == expected:
            print(f"  ✓ Variable name: '{input_text}' -> '{result}'")
        else:
            print(f"  ✗ Variable name: '{input_text}' -> '{result}' (expected '{expected}')")
            return False
    
    # Test filename sanitization
    filename_cases = [
        ("ACME Corp & Co.", "ACME-Corp-Co"),
        ("$1,250.00", "1250-00"),
        ("INV-2024/001", "INV-2024-001"),
        ("", "unknown")
    ]
    
    for input_text, expected in filename_cases:
        result = sanitize_filename(input_text)
        if result == expected:
            print(f"  ✓ Filename: '{input_text}' -> '{result}'")
        else:
            print(f"  ✗ Filename: '{input_text}' -> '{result}' (expected '{expected}')")
            return False
    
    return True


def test_cli_argument_parsing():
    """Test that new CLI arguments parse correctly."""
    print("\nTesting CLI argument parsing...")
    
    # Import the enhanced CLI module
    try:
        from pdf_manipulator.cli import validate_scraper_arguments
        import argparse
        
        # Create a mock args object
        args = argparse.Namespace()
        args.scrape_pattern = ["Invoice Number:r1wd1", "company=Company:u1ln1"]
        args.scrape_patterns_file = None
        args.filename_template = "{company}_{invoice_number}.pdf"
        args.extract_pages = "1"
        args.scrape_text = False
        args.pattern_source_page = 1
        
        is_valid, error_msg = validate_scraper_arguments(args)
        
        if is_valid:
            print("  ✓ Valid argument combination accepted")
        else:
            print(f"  ✗ Valid arguments rejected: {error_msg}")
            return False
        
        # Test invalid combination
        args.scrape_pattern = ["Invoice Number:r1wd1"]
        args.scrape_patterns_file = "patterns.txt"  # Conflict
        
        is_valid, error_msg = validate_scraper_arguments(args)
        
        if not is_valid:
            print(f"  ✓ Invalid combination correctly rejected: {error_msg}")
        else:
            print("  ✗ Invalid combination should have been rejected")
            return False
            
    except Exception as e:
        print(f"  ✗ CLI argument testing failed: {e}")
        return False
    
    return True


def main():
    """Run all Phase 1 foundation tests."""
    print("Phase 1 Foundation Test - Scraper Integration")
    print("=" * 50)
    
    tests = [
        test_compact_pattern_parsing,
        test_template_engine,
        test_sanitization,
        test_cli_argument_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"FAILED: {test.__name__}")
        except Exception as e:
            print(f"ERROR in {test.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print(f"Phase 1 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ Phase 1 foundation is working correctly!")
        print("\nNext steps:")
        print("- Phase 2: Implement actual pattern extraction")
        print("- Phase 2: Integrate with existing operations")
        print("- Phase 2: Add dry-run functionality")
        return 0
    else:
        print("✗ Phase 1 foundation has issues that need to be fixed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# End of file #
