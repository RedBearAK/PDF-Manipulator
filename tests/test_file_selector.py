#!/usr/bin/env python3
"""
Test module for file selector functionality.
File: tests/test_file_selector.py

Usage:  python test_file_selector.py
        pytest test_file_selector.py
"""

import sys
import tempfile
import os
from pathlib import Path
from rich.console import Console

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pdf_manipulator.core.page_range.file_selector import FileSelector
    from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser
    from pdf_manipulator.core.operations import get_ordered_pages_from_groups
    print("✅ Successfully imported file selector modules")
except ImportError as e:
    print(f"❌ Import failed - file selector not yet implemented: {e}")
    sys.exit(1)

console = Console()


class TestFileSelector:
    """Test file selector functionality in isolation and integration."""
    
    def __init__(self):
        self.temp_dir = None
        self.temp_files = {}
    
    def setup_temp_files(self):
        """Create temporary test files."""
        self.temp_dir = tempfile.mkdtemp()
        temp_path = Path(self.temp_dir)
        
        # Create test files with different content
        test_files = {
            'simple_pages.txt': """# Simple page selections
1-5
10,15,20
30-25""",
            
            'reverse_pages.txt': """# Reverse page selections
50-40
25-15
10-1""",
            
            'mixed_pages.txt': """# Mixed page selections
1-3
# Some individual pages
5,10,15
# Reverse range
20-16
# Special keywords
last 2""",
            
            'empty_file.txt': """# File with only comments

# No actual page specifications
""",
            
            'complex_pages.txt': """# Complex selections
first 3
10,5,15,2
50-45
# Slicing patterns
::2
5:10:2"""
        }
        
        for filename, content in test_files.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
            self.temp_files[filename] = file_path
        
        return temp_path
    
    def cleanup_temp_files(self):
        """Clean up temporary test files."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_file_selector_basic(self) -> bool:
        """Test basic file selector functionality."""
        print("=== Testing Basic File Selector ===")
        
        temp_path = self.setup_temp_files()
        selector = FileSelector(base_path=temp_path)
        
        test_cases = [
            # (selector_spec, expected_specs, description)
            ("file:simple_pages.txt", ["1-5", "10,15,20", "30-25"], "Simple file loading"),
            ("file:reverse_pages.txt", ["50-40", "25-15", "10-1"], "Reverse ranges file"),
            ("file:mixed_pages.txt", ["1-3", "5,10,15", "20-16", "last 2"], "Mixed specifications"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for selector_spec, expected_specs, description in test_cases:
            try:
                result = selector.parse_file_selector(selector_spec)
                
                if result == expected_specs:
                    print(f"✓ {description}: {result}")
                    passed += 1
                else:
                    print(f"✗ {description}")
                    print(f"    Expected: {expected_specs}")
                    print(f"    Got:      {result}")
                    
            except Exception as e:
                print(f"✗ {description}: Exception: {e}")
        
        self.cleanup_temp_files()
        print(f"Basic file selector: {passed}/{total} passed\n")
        return passed == total
    
    def test_file_selector_expansion(self) -> bool:
        """Test file selector expansion in range strings."""
        print("=== Testing File Selector Expansion ===")
        
        temp_path = self.setup_temp_files()
        selector = FileSelector(base_path=temp_path)
        
        test_cases = [
            # (input_range, expected_expanded, description)
            ("file:simple_pages.txt", "1-5,10,15,20,30-25", "Single file expansion"),
            ("1-3,file:reverse_pages.txt,40-50", "1-3,50-40,25-15,10-1,40-50", "Mixed expansion"),
            ("file:simple_pages.txt,file:reverse_pages.txt", "1-5,10,15,20,30-25,50-40,25-15,10-1", "Multiple files"),
            ("no_file_here", "no_file_here", "No file selector (unchanged)"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for input_range, expected_expanded, description in test_cases:
            try:
                result = selector.expand_file_selectors(input_range)
                
                if result == expected_expanded:
                    print(f"✓ {description}: '{input_range}' → '{result}'")
                    passed += 1
                else:
                    print(f"✗ {description}: '{input_range}'")
                    print(f"    Expected: '{expected_expanded}'")
                    print(f"    Got:      '{result}'")
                    
            except Exception as e:
                print(f"✗ {description}: '{input_range}' → Exception: {e}")
        
        self.cleanup_temp_files()
        print(f"File selector expansion: {passed}/{total} passed\n")
        return passed == total
    
    def test_file_selector_errors(self) -> bool:
        """Test file selector error handling."""
        print("=== Testing File Selector Error Handling ===")
        
        temp_path = self.setup_temp_files()
        selector = FileSelector(base_path=temp_path)
        
        test_cases = [
            # (selector_spec, should_fail, expected_error_type, description)
            ("file:nonexistent.txt", True, "not found", "Nonexistent file"),
            ("file:", True, "missing file path", "Empty file path"),
            ("file:empty_file.txt", True, "No valid page specifications", "File with no specs"),
            ("not_a_file_selector", False, None, "Non-file selector (should not process)"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for selector_spec, should_fail, expected_error_type, description in test_cases:
            try:
                if selector_spec == "not_a_file_selector":
                    # This should not be processed as a file selector
                    if not selector.is_file_selector(selector_spec):
                        print(f"✓ {description}: Correctly identified as non-file selector")
                        passed += 1
                    else:
                        print(f"✗ {description}: Incorrectly identified as file selector")
                else:
                    result = selector.parse_file_selector(selector_spec)
                    
                    if should_fail:
                        print(f"✗ {description}: Should have failed but got: {result}")
                    else:
                        print(f"✓ {description}: Success: {result}")
                        passed += 1
                        
            except Exception as e:
                if should_fail and expected_error_type and expected_error_type.lower() in str(e).lower():
                    print(f"✓ {description}: Correctly failed with: {e}")
                    passed += 1
                elif should_fail:
                    print(f"✓ {description}: Failed as expected (different error): {e}")
                    passed += 1
                else:
                    print(f"✗ {description}: Unexpected failure: {e}")
        
        self.cleanup_temp_files()
        print(f"Error handling: {passed}/{total} passed\n")
        return passed == total
    
    def test_integration_with_parser(self) -> bool:
        """Test file selector integration with PageRangeParser."""
        print("=== Testing Integration with PageRangeParser ===")
        
        temp_path = self.setup_temp_files()
        
        # Create a mock PDF path in the temp directory for the parser
        mock_pdf = temp_path / "test.pdf"
        mock_pdf.touch()  # Create empty file
        
        # Build expected result for complex file step by step
        complex_expected = []
        complex_expected.extend([1, 2, 3])  # first 3
        complex_expected.extend([10, 5, 15, 2])  # 10,5,15,2
        complex_expected.extend([50, 49, 48, 47, 46, 45])  # 50-45
        complex_expected.extend(list(range(1, 50, 2)))  # ::2 (all odd pages 1-49)
        complex_expected.extend([5, 7, 9])  # 5:10:2
        
        test_cases = [
            # (range_string, expected_pages, description)
            ("file:simple_pages.txt", [1,2,3,4,5,10,15,20,30,29,28,27,26,25], "File with mixed ranges"),
            ("1-3,file:reverse_pages.txt", [1,2,3,50,49,48,47,46,45,44,43,42,41,40,25,24,23,22,21,20,19,18,17,16,15,10,9,8,7,6,5,4,3,2,1], "Mixed file and direct"),
            ("file:complex_pages.txt", complex_expected, "Complex file with various specs"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for range_string, expected_pages, description in test_cases:
            try:
                parser = PageRangeParser(total_pages=50, pdf_path=mock_pdf)
                pages_set, desc, groups = parser.parse(range_string)
                actual_pages = get_ordered_pages_from_groups(groups, pages_set)
                
                if actual_pages == expected_pages:
                    print(f"✓ {description}: {actual_pages}")
                    passed += 1
                else:
                    print(f"✗ {description}")
                    print(f"    Expected: {expected_pages}")
                    print(f"    Got:      {actual_pages}")
                    
            except Exception as e:
                print(f"✗ {description}: Exception: {e}")
        
        self.cleanup_temp_files()
        print(f"Parser integration: {passed}/{total} passed\n")
        return passed == total


def main() -> bool:
    """Run all file selector tests."""
    console.print("[cyan]Testing File Selector Implementation[/cyan]\n")
    
    tester = TestFileSelector()
    
    tests = [
        tester.test_file_selector_basic,
        tester.test_file_selector_expansion,
        tester.test_file_selector_errors,
        tester.test_integration_with_parser,
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            console.print(f"[red]Test {test_func.__name__} crashed: {e}[/red]")
    
    console.print(f"\n[cyan]Overall Results: {passed_tests}/{total_tests} test groups passed[/cyan]")
    
    if passed_tests == total_tests:
        console.print("[green]✓ All file selector tests passed![/green]")
        return True
    else:
        console.print("[red]✗ Some file selector tests failed.[/red]")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


# End of file #
