#!/usr/bin/env python3
"""
Comprehensive Integration Test: Conflict Resolution
File: tests/test_conflict_resolution_integration.py

Tests the complete integration chain:
CLI args -> extract_enhanced_args() -> operations functions -> file_conflicts -> actual file handling
"""

import argparse
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_manipulator.cli import extract_enhanced_args
from pdf_manipulator.core.operations import extract_pages
from pdf_manipulator.core.file_conflicts import resolve_file_conflicts
from pdf_manipulator.core.exceptions import FileConflictError


def create_mock_args(**kwargs):
    """Create a mock args object for testing."""
    args = argparse.Namespace()
    
    defaults = {
        'batch': False,
        'conflicts': 'ask',
        'dedup': None,
        'separate_files': False,
        'respect_groups': False,
        'smart_names': False,
        'name_prefix': None,
        'no_timestamp': False,
        'filename_template': None,
        'timestamp': False,
        'extract_pages': '1',
        'dry_run': False,
        'preview': False
    }
    
    for key, value in defaults.items():
        setattr(args, key, value)
    
    for key, value in kwargs.items():
        setattr(args, key, value)
    
    return args


def create_test_pdf(pdf_path: Path):
    """Create a minimal test PDF file."""
    # Create a simple PDF with pypdf for testing
    from pypdf import PdfWriter
    from pypdf.generic import RectangleObject, DictionaryObject, NameObject, ArrayObject, NumberObject
    
    writer = PdfWriter()
    
    # Create a simple blank page using proper pypdf API
    page = writer.add_blank_page(width=612, height=792)
    
    # Write to file
    with open(pdf_path, 'wb') as output:
        writer.write(output)


def is_pdf_file(file_path: Path) -> bool:
    """Check if a file is a PDF by reading the first few bytes."""
    if not file_path.exists():
        return False
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            return header.startswith(b'%PDF-')
    except Exception:
        return False


def test_batch_mode_conversion():
    """Test that batch mode converts 'ask' to 'rename'."""
    print("Testing batch mode conflict strategy conversion...")
    
    # Test interactive mode (should keep 'ask')
    args_interactive = create_mock_args(batch=False, conflicts='ask')
    enhanced_args = extract_enhanced_args(args_interactive)
    
    if enhanced_args['conflict_strategy'] == 'ask' and enhanced_args['interactive'] == True:
        print("  ✓ Interactive mode: 'ask' strategy preserved")
        interactive_passed = True
    else:
        print(f"  ✗ Interactive mode failed: strategy={enhanced_args['conflict_strategy']}, interactive={enhanced_args['interactive']}")
        interactive_passed = False
    
    # Test batch mode (should convert 'ask' to 'rename')  
    args_batch = create_mock_args(batch=True, conflicts='ask')
    enhanced_args = extract_enhanced_args(args_batch)
    
    if enhanced_args['conflict_strategy'] == 'rename' and enhanced_args['interactive'] == False:
        print("Batch mode: converting 'ask' conflict strategy to 'rename' for safety")
        print("  ✓ Batch mode: 'ask' converted to 'rename'")
        batch_passed = True
    else:
        print(f"  ✗ Batch mode failed: strategy={enhanced_args['conflict_strategy']}, interactive={enhanced_args['interactive']}")
        batch_passed = False
    
    # Test explicit overwrite in batch mode (should be preserved)
    args_batch_overwrite = create_mock_args(batch=True, conflicts='overwrite')
    enhanced_args = extract_enhanced_args(args_batch_overwrite)
    
    if enhanced_args['conflict_strategy'] == 'overwrite':
        print("  ✓ Batch mode: explicit 'overwrite' preserved")
        explicit_passed = True
    else:
        print(f"  ✗ Batch mode explicit overwrite failed: got {enhanced_args['conflict_strategy']}")
        explicit_passed = False
    
    return interactive_passed and batch_passed and explicit_passed


def test_operations_parameter_acceptance():
    """Test that operations functions accept conflict_strategy parameter."""
    print("Testing operations function parameter acceptance...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test PDF
        test_pdf = temp_path / "test.pdf"
        create_test_pdf(test_pdf)
        
        try:
            # Test extract_pages accepts conflict_strategy parameter
            result = extract_pages(
                pdf_path=test_pdf,
                page_range="1",
                dry_run=True,  # Don't actually create files
                conflict_strategy='ask'
            )
            
            # In dry_run mode, extract_pages returns (None, 0)
            if result == (None, 0):
                print("Would create: test_extracted_page1.pdf")
                print("  ✓ extract_pages accepts conflict_strategy parameter")
                return True
            else:
                print(f"  ✗ Unexpected result from extract_pages: {result}")
                return False
                
        except TypeError as e:
            if 'conflict_strategy' in str(e):
                print(f"  ✗ extract_pages does not accept conflict_strategy: {e}")
                return False
            else:
                print(f"  ✗ Other TypeError in extract_pages: {e}")
                return False
        except Exception as e:
            print(f"  ✗ extract_pages failed with conflict_strategy: {e}")
            return False


def test_file_conflict_detection():
    """Test file conflict detection and resolution logic."""
    print("Testing file conflict detection and resolution...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create an existing file
        existing_file = temp_path / "existing.pdf"
        existing_file.write_text("existing content")
        
        # Test different strategies
        test_cases = [
            ('skip', None, "Skip strategy should return None"),
            ('rename', 'different_name', "Rename strategy should return different path"),
            ('overwrite', existing_file, "Overwrite strategy should return same path"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for strategy, expected_type, description in test_cases:
            try:
                result_paths, skipped_paths = resolve_file_conflicts(
                    [existing_file], strategy, interactive=False
                )
                
                if strategy == 'skip':
                    if not result_paths and skipped_paths == [existing_file]:
                        print(f"Skipping existing file: {existing_file.name}")
                        print(f"  ✓ {description}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: got result_paths={result_paths}, skipped={skipped_paths}")
                
                elif strategy == 'rename':
                    if result_paths and len(result_paths) == 1 and result_paths[0] != existing_file:
                        print(f"Renaming to avoid conflict: {existing_file.name} → {result_paths[0].name}")
                        print(f"  ✓ {description}: {result_paths[0].name}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: got {result_paths}")
                
                elif strategy == 'overwrite':
                    if result_paths == [existing_file]:
                        print(f"Overwriting existing file: {existing_file.name}")
                        print(f"  ✓ {description}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: got {result_paths}")
                        
            except Exception as e:
                print(f"  ✗ {description}: Exception {type(e)}: {e}")
        
        # Test fail strategy
        try:
            result_paths, skipped_paths = resolve_file_conflicts(
                [existing_file], 'fail', interactive=False
            )
            print("  ✗ Fail strategy should have raised exception")
        except Exception as e:
            if 'conflict' in str(e).lower():
                print("  ✓ Fail strategy correctly raised exception")
                passed += 1
            else:
                print(f"  ✗ Fail strategy raised wrong exception: {e}")
        
        total += 1  # Account for fail test
        
        return passed == total


def test_end_to_end_integration():
    """Test complete integration from CLI args to file operations."""
    print("Testing end-to-end integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test PDF
        test_pdf = temp_path / "source.pdf"
        create_test_pdf(test_pdf)
        
        # Create expected output file to test conflict (match actual filename generation)
        expected_output = temp_path / "source_extracted_page1.pdf"
        expected_output.write_text("existing output")
        
        test_cases = [
            # (args_kwargs, expected_behavior, description)
            ({'conflicts': 'skip', 'batch': True}, 'skip', "Batch skip should not create new file"),
            ({'conflicts': 'rename', 'batch': True}, 'rename', "Batch rename should create renamed file"),
            ({'conflicts': 'overwrite', 'batch': True}, 'overwrite', "Batch overwrite should replace file"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for args_kwargs, expected_behavior, description in test_cases:
            # Reset the existing file to text content
            expected_output.write_text("existing output")
            original_was_text = not is_pdf_file(expected_output)
            
            args = create_mock_args(extract_pages="1", **args_kwargs)
            
            try:
                # Call extract_pages with arguments processed through the full chain
                enhanced_args = extract_enhanced_args(args)
                
                result = extract_pages(
                    pdf_path=test_pdf,
                    page_range=args.extract_pages,
                    dry_run=False,  # Actually perform operation
                    conflict_strategy=enhanced_args['conflict_strategy']
                )
                
                if expected_behavior == 'skip':
                    # Should return None, and original file should be unchanged (still text)
                    if result == (None, 0) and not is_pdf_file(expected_output):
                        print(f"Skipping existing file: {expected_output.name}")
                        print(f"Skipping existing file: {expected_output.name}")
                        print(f"  ✓ {description}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: result={result}, file changed to PDF={is_pdf_file(expected_output)}")
                
                elif expected_behavior == 'rename':
                    # Should return a renamed path, original file unchanged
                    if result[0] and result[0] != expected_output and not is_pdf_file(expected_output):
                        print(f"Renaming to avoid conflict: {expected_output.name} → {result[0].name}")
                        print(f"✓ Extracted 1 pages: 1")
                        print(f"  ✓ {description}: created {result[0].name}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: result={result}, original file changed to PDF={is_pdf_file(expected_output)}")
                
                elif expected_behavior == 'overwrite':
                    # Should return original path, and file should be changed from text to PDF
                    if result[0] == expected_output and is_pdf_file(expected_output):
                        print(f"Overwriting existing file: {expected_output.name}")
                        print(f"✓ Extracted 1 pages: 1")
                        print(f"  ✓ {description}: {expected_output.name}")
                        passed += 1
                    else:
                        print(f"  ✗ {description}: result={result}, file is PDF={is_pdf_file(expected_output)}")
                        
            except Exception as e:
                print(f"  ✗ {description}: Exception {type(e)}: {e}")
        
        return passed == total


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Comprehensive Conflict Resolution Integration Test")
    print("=" * 60)
    
    tests = [
        test_batch_mode_conversion,
        test_operations_parameter_acceptance, 
        test_file_conflict_detection,
        test_end_to_end_integration,
    ]
    
    total_passed = 0
    total_tests = len(tests)
    
    for test_func in tests:
        print(f"\n{test_func.__name__.replace('_', ' ').title()}:")
        try:
            if test_func():
                total_passed += 1
                print("  ✓ PASSED")
            else:
                print("  ✗ FAILED")
        except Exception as e:
            print(f"  ✗ FAILED with exception: {e}")
        
    print(f"\n{'='*60}")
    print(f"Integration Test Results: {total_passed}/{total_tests} passed")
    
    if total_passed == total_tests:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✓ Conflict resolution integration is working correctly")
        print("✓ Batch mode safety conversion works") 
        print("✓ Operations functions properly use conflict resolution")
        print("✓ End-to-end chain from CLI to file operations works")
        return True
    else:
        failed = total_tests - total_passed
        print(f"💥 {failed} integration test(s) failed")
        print("⚠️  Review the failed tests and check the integration")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)


# End of file #
