"""
Integration tests for Simple PDF Scraper.

Tests should be runnable with pytest but not in pytest style.
Accumulate results and show final score.
"""

import sys

from pathlib import Path

# Add parent directory to Python path to find the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import tempfile

from simple_pdf_scraper.cli import parse_pattern, parse_patterns_file, expand_file_paths
from simple_pdf_scraper.output.tsv_writer import TSVWriter


def test_pattern_parsing():
    """Test CLI pattern parsing functionality."""
    try:
        # Test valid pattern
        pattern = parse_pattern("Invoice:right:2:number")
        expected = {
            'keyword': 'Invoice',
            'direction': 'right',
            'distance': 2,
            'extract_type': 'number'
        }
        
        if pattern != expected:
            return False, f"Pattern parsing failed: {pattern} != {expected}"
        
        # Test invalid pattern (should raise ValueError)
        try:
            parse_pattern("invalid:pattern")
            return False, "Should have raised ValueError for invalid pattern"
        except ValueError:
            pass  # Expected
        
        return True, "Pattern parsing works correctly"
    except Exception as e:
        return False, f"Error testing pattern parsing: {e}"


def test_patterns_file_parsing():
    """Test parsing patterns from file."""
    try:
        # Create temporary patterns file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Invoice:right:1:word\n")
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            f.write("Total:below:1:number\n")
            patterns_file = f.name
        
        try:
            patterns = parse_patterns_file(patterns_file)
            
            if patterns is None:
                return False, "Failed to parse patterns file"
            
            if len(patterns) != 2:
                return False, f"Expected 2 patterns, got {len(patterns)}"
            
            if patterns[0]['keyword'] != 'Invoice':
                return False, f"First pattern wrong: {patterns[0]}"
            
            if patterns[1]['keyword'] != 'Total':
                return False, f"Second pattern wrong: {patterns[1]}"
            
            return True, "Patterns file parsing works"
        finally:
            os.unlink(patterns_file)
    except Exception as e:
        return False, f"Error testing patterns file: {e}"


def test_file_expansion():
    """Test file path expansion functionality."""
    try:
        # Create temporary directory with some files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.pdf").touch()
            (temp_path / "test2.pdf").touch()
            (temp_path / "other.txt").touch()
            
            # Test expansion
            pattern = str(temp_path / "*.pdf")
            expanded = expand_file_paths([pattern])
            
            if len(expanded) != 2:
                return False, f"Expected 2 PDF files, got {len(expanded)}"
            
            # Should only include PDF files
            for file_path in expanded:
                if not file_path.endswith('.pdf'):
                    return False, f"Non-PDF file included: {file_path}"
            
            return True, "File expansion works correctly"
    except Exception as e:
        return False, f"Error testing file expansion: {e}"


def test_tsv_writer():
    """Test TSV output functionality."""
    try:
        writer = TSVWriter()
        
        headers = ['filename', 'page', 'invoice', 'total']
        rows = [
            ['test1.pdf', 1, 'INV-001', '$100.00'],
            ['test2.pdf', 1, 'INV-002', '$250.50']
        ]
        
        # Test validation
        validation = writer.validate_data(headers, rows)
        if not validation['valid']:
            return False, f"Validation failed: {validation['errors']}"
        
        # Test preview
        preview = writer.preview_output(headers, rows)
        if 'filename\tpage\tinvoice\ttotal' not in preview:
            return False, "Preview missing headers"
        
        if 'INV-001' not in preview:
            return False, "Preview missing data"
        
        # Test stats
        stats = writer.get_stats(headers, rows)
        if stats['total_rows'] != 2:
            return False, f"Wrong row count: {stats['total_rows']}"
        
        if stats['total_columns'] != 4:
            return False, f"Wrong column count: {stats['total_columns']}"
        
        return True, "TSV writer works correctly"
    except Exception as e:
        return False, f"Error testing TSV writer: {e}"


def test_tsv_file_writing():
    """Test actual TSV file writing."""
    try:
        writer = TSVWriter()
        
        headers = ['filename', 'page', 'data']
        rows = [
            ['test.pdf', 1, 'Some data with\ttabs and\nnewlines'],
            ['test.pdf', 2, '']  # Empty cell
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as f:
            output_file = f.name
        
        try:
            writer.write_results(output_file, headers, rows)
            
            # Read back and verify
            with open(output_file, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            if len(lines) != 3:  # Header + 2 data rows
                return False, f"Expected 3 lines, got {len(lines)}"
            
            # Check header
            if lines[0] != 'filename\tpage\tdata':
                return False, f"Wrong header: {lines[0]}"
            
            # Check that tabs and newlines were cleaned
            if '\n' in lines[1] or '\n' in lines[2]:
                return False, "Newlines not cleaned from data"
            
            return True, "TSV file writing works correctly"
        finally:
            os.unlink(output_file)
    except Exception as e:
        return False, f"Error testing TSV file writing: {e}"


def test_cell_value_cleaning():
    """Test cell value cleaning functionality."""
    try:
        writer = TSVWriter()
        
        # Test various problematic values
        test_cases = [
            ("Normal text", "Normal text"),
            ("Text\twith\ttabs", "Text with tabs"),
            ("Text\nwith\nnewlines", "Text with newlines"),
            ("  Extra   spaces  ", "Extra spaces"),
            (None, ""),
            (123, "123"),
            ("$1,234.56", "$1,234.56")
        ]
        
        for input_val, expected in test_cases:
            result = writer._clean_cell_value(input_val)
            if result != expected:
                return False, f"Cleaning failed for {repr(input_val)}: got {repr(result)}, expected {repr(expected)}"
        
        return True, "Cell value cleaning works correctly"
    except Exception as e:
        return False, f"Error testing cell cleaning: {e}"


def test_number_detection():
    """Test number detection in cell values."""
    try:
        writer = TSVWriter()
        
        test_cases = [
            ("123", True),
            ("123.45", True),
            ("$1,234.56", True),
            ("Not a number", False),
            ("123ABC", False),
            ("", False),
            ("1 234", True)  # Space-separated number
        ]
        
        for value, expected in test_cases:
            result = writer._looks_like_number(value)
            if result != expected:
                return False, f"Number detection failed for {repr(value)}: got {result}, expected {expected}"
        
        return True, "Number detection works correctly"
    except Exception as e:
        return False, f"Error testing number detection: {e}"


def run_tests():
    """Run all integration tests and return results."""
    tests = [
        test_pattern_parsing,
        test_patterns_file_parsing,
        test_file_expansion,
        test_tsv_writer,
        test_tsv_file_writing,
        test_cell_value_cleaning,
        test_number_detection
    ]
    
    results = []
    passed = 0
    total = len(tests)
    
    print("Testing Integration Components")
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
