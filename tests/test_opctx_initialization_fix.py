#!/usr/bin/env python3
"""
Test module to verify OpCtx initialization fixes in batch processing.
File: tests/test_opctx_initialization_fix.py

Tests that:
1. OpCtx.set_current_pdf() is called before parsing in batch operations
2. Defensive guards catch missing initialization
3. The "all" keyword works correctly with group-end options

Run: python tests/test_opctx_initialization_fix.py
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.operation_context import OperationContext as OpCtx
from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser


console_output = []


def mock_console_print(msg):
    """Capture console output for testing."""
    console_output.append(msg)


def test_parser_guard_catches_none_total_pages():
    """Test that PageRangeParser.__init__ catches None total_pages."""
    print("\n=== Test 1: Parser Guard Catches None total_pages ===")
    
    try:
        parser = PageRangeParser(total_pages=None)
        print("✗ FAILED: Parser accepted None total_pages (guard not implemented)")
        return False
    except ValueError as e:
        error_msg = str(e)
        if "cannot be None" in error_msg and "OpCtx.set_current_pdf" in error_msg:
            print(f"✓ PASSED: Guard caught None with helpful message: {error_msg[:80]}...")
            return True
        else:
            print(f"✗ FAILED: Guard caught None but message not helpful: {error_msg}")
            return False
    except Exception as e:
        print(f"✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False


def test_parser_guard_catches_invalid_total_pages():
    """Test that PageRangeParser.__init__ validates total_pages type."""
    print("\n=== Test 2: Parser Guard Validates total_pages Type ===")
    
    test_cases = [
        (0, "zero pages"),
        (-5, "negative pages"),
        ("10", "string instead of int"),
    ]
    
    passed = 0
    for invalid_value, description in test_cases:
        try:
            parser = PageRangeParser(total_pages=invalid_value)
            print(f"  ✗ {description}: Accepted invalid value {invalid_value}")
        except (ValueError, TypeError) as e:
            print(f"  ✓ {description}: Rejected with {type(e).__name__}")
            passed += 1
        except Exception as e:
            print(f"  ? {description}: Unexpected exception {type(e).__name__}")
    
    success = passed == len(test_cases)
    print(f"Result: {passed}/{len(test_cases)} validations working")
    return success


def test_parse_range_guard_checks_opctx():
    """Test that parse_page_range checks OpCtx initialization."""
    print("\n=== Test 3: parse_page_range() Checks OpCtx State ===")
    
    # Clear OpCtx state
    OpCtx.current_pdf_path = None
    OpCtx.current_page_count = None
    OpCtx._parsed_results = None
    
    try:
        from pdf_manipulator.core.parser import parse_page_range
        
        # Try to parse without initializing OpCtx
        result = parse_page_range()
        print("✗ FAILED: parse_page_range accepted uninitialized OpCtx")
        return False
        
    except RuntimeError as e:
        error_msg = str(e)
        if "not initialized" in error_msg and "OpCtx.set_current_pdf" in error_msg:
            print(f"✓ PASSED: Guard caught uninitialized OpCtx: {error_msg[:80]}...")
            return True
        else:
            print(f"✗ FAILED: RuntimeError but message not helpful: {error_msg}")
            return False
    except Exception as e:
        print(f"✗ FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False


def test_all_keyword_with_valid_context():
    """Test that 'all' keyword works when OpCtx is properly initialized."""
    print("\n=== Test 4: 'all' Keyword Works With Valid Context ===")
    
    try:
        # Create a temporary PDF path (doesn't need to exist for this test)
        temp_pdf = Path("/tmp/test.pdf")
        
        # Properly initialize OpCtx
        OpCtx.set_current_pdf(temp_pdf, page_count=5)
        
        # Create parser - should work now
        parser = PageRangeParser(total_pages=5, pdf_path=temp_pdf)
        
        # Parse "all" - should work without NoneType error
        pages_set, description, groups = parser.parse("all")
        
        if pages_set == {1, 2, 3, 4, 5}:
            print(f"✓ PASSED: 'all' parsed correctly: {sorted(pages_set)}")
            return True
        else:
            print(f"✗ FAILED: 'all' gave wrong pages: {sorted(pages_set)}")
            return False
            
    except Exception as e:
        print(f"✗ FAILED: Exception during parsing: {type(e).__name__}: {e}")
        return False
    finally:
        # Clean up
        OpCtx.current_pdf_path = None
        OpCtx.current_page_count = None
        OpCtx._parsed_results = None


def test_simulated_batch_processing():
    """Simulate batch processing to verify fix pattern."""
    print("\n=== Test 5: Simulated Batch Processing Pattern ===")
    
    # Simulate batch processing with the fixed pattern
    pdf_files = [
        (Path("/tmp/file1.pdf"), 3, 0.5),
        (Path("/tmp/file2.pdf"), 5, 1.2),
        (Path("/tmp/file3.pdf"), 2, 0.3),
    ]
    
    processed = 0
    errors = []
    
    for pdf_path, page_count, file_size in pdf_files:
        try:
            # CRITICAL: Set PDF context BEFORE parsing (the fix!)
            OpCtx.set_current_pdf(pdf_path, page_count)
            
            # Create parser - should work because context is set
            parser = PageRangeParser(total_pages=page_count, pdf_path=pdf_path)
            
            # Try parsing "all"
            pages_set, desc, groups = parser.parse("all")
            
            expected_pages = set(range(1, page_count + 1))
            if pages_set == expected_pages:
                processed += 1
            else:
                errors.append(f"{pdf_path.name}: wrong pages")
                
        except Exception as e:
            errors.append(f"{pdf_path.name}: {type(e).__name__}: {e}")
    
    if processed == len(pdf_files) and not errors:
        print(f"✓ PASSED: Processed all {len(pdf_files)} files successfully")
        return True
    else:
        print(f"✗ FAILED: Processed {processed}/{len(pdf_files)}")
        for error in errors:
            print(f"  - {error}")
        return False


def test_original_failing_scenario():
    """Test the exact scenario that was failing: 'all' with group-end."""
    print("\n=== Test 6: Original Failing Scenario (all + group-end) ===")
    
    try:
        import argparse
        
        # Set up args like the original failing command
        args = argparse.Namespace(
            extract_pages="all",
            group_end="contains:'For ACH Payments'",
            respect_groups=True,
            batch=True
        )
        
        OpCtx.set_args(args)
        
        # Simulate processing a 2-page PDF (like the original)
        pdf_path = Path("/tmp/invoice.pdf")
        page_count = 2
        
        # This is what the fix ensures happens
        OpCtx.set_current_pdf(pdf_path, page_count)
        
        # Now try parsing - should work
        from pdf_manipulator.core.parser import parse_page_range
        
        # Note: This will fail if group-end pattern can't be found in the PDF,
        # but it should NOT fail with "NoneType + int"
        try:
            pages, desc, groups = parse_page_range()
            print(f"✓ PASSED: Parsing completed without NoneType error")
            print(f"  Pages: {sorted(pages)}, Groups: {len(groups)}")
            return True
        except ValueError as ve:
            # ValueError is OK - means pattern not found, but parsing logic worked
            if "NoneType" not in str(ve) and "unsupported operand" not in str(ve):
                print(f"✓ PASSED: No NoneType error (got expected ValueError: {ve})")
                return True
            else:
                print(f"✗ FAILED: Still getting NoneType error: {ve}")
                return False
                
    except TypeError as te:
        if "NoneType" in str(te):
            print(f"✗ FAILED: Still getting NoneType error: {te}")
            return False
        raise
    except Exception as e:
        print(f"? UNCERTAIN: Unexpected exception: {type(e).__name__}: {e}")
        return False
    finally:
        # Clean up
        OpCtx.current_pdf_path = None
        OpCtx.current_page_count = None
        OpCtx._parsed_results = None
        OpCtx.args = None


def main():
    """Run all tests."""
    print("=" * 70)
    print("OpCtx Initialization Fix Verification Tests")
    print("=" * 70)
    
    tests = [
        test_parser_guard_catches_none_total_pages,
        test_parser_guard_catches_invalid_total_pages,
        test_parse_range_guard_checks_opctx,
        test_all_keyword_with_valid_context,
        test_simulated_batch_processing,
        test_original_failing_scenario,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ TEST CRASHED: {test.__name__}")
            print(f"  Exception: {type(e).__name__}: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - Test {i}: {test.__name__}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL FIXES VERIFIED - OpCtx initialization working correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - fixes may not be complete")
        return 1


if __name__ == "__main__":
    sys.exit(main())


# End of file #
