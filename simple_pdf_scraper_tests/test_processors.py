"""
Test PDF processors functionality.

Tests should be runnable with pytest but not in pytest style.
Accumulate results and show final score.
"""

import sys

from pathlib import Path

# Add parent directory to Python path to find the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile

from simple_pdf_scraper.processors.pypdf_processor import PyPDFProcessor


def test_pypdf_processor_initialization():
    """Test that PyPDFProcessor can be initialized."""
    try:
        processor = PyPDFProcessor()
        return True, "PyPDFProcessor initialized successfully"
    except Exception as e:
        return False, f"Failed to initialize PyPDFProcessor: {e}"


def test_pypdf_processor_inheritance():
    """Test that PyPDFProcessor properly inherits from PDFProcessor."""
    try:
        from simple_pdf_scraper.processors.base import PDFProcessor
        processor = PyPDFProcessor()
        
        if isinstance(processor, PDFProcessor):
            return True, "PyPDFProcessor properly inherits from PDFProcessor"
        else:
            return False, "PyPDFProcessor does not inherit from PDFProcessor"
    except Exception as e:
        return False, f"Error testing inheritance: {e}"


def test_processor_methods_exist():
    """Test that required methods exist on the processor."""
    try:
        processor = PyPDFProcessor()
        
        required_methods = ['extract_pages', 'extract_page', 'get_page_count', 'validate_pdf']
        missing_methods = []
        
        for method in required_methods:
            if not hasattr(processor, method) or not callable(getattr(processor, method)):
                missing_methods.append(method)
        
        if missing_methods:
            return False, f"Missing required methods: {missing_methods}"
        else:
            return True, "All required methods exist"
    except Exception as e:
        return False, f"Error checking methods: {e}"


def test_processor_info():
    """Test that processor info is available."""
    try:
        processor = PyPDFProcessor()
        
        if hasattr(processor, 'get_processor_info'):
            info = processor.get_processor_info()
            if isinstance(info, dict) and 'name' in info:
                return True, f"Processor info available: {info['name']}"
            else:
                return False, "Processor info format invalid"
        else:
            return False, "get_processor_info method not found"
    except Exception as e:
        return False, f"Error getting processor info: {e}"


def test_file_not_found_handling():
    """Test handling of non-existent files."""
    try:
        processor = PyPDFProcessor()
        
        # Test with a file that definitely doesn't exist
        fake_file = "/tmp/definitely_does_not_exist_12345.pdf"
        
        try:
            processor.extract_pages(fake_file)
            return False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            return True, "Properly handles non-existent files"
        except Exception as e:
            return False, f"Wrong exception type for missing file: {e}"
    except Exception as e:
        return False, f"Error testing file handling: {e}"


def test_text_cleaning():
    """Test the internal text cleaning method."""
    try:
        processor = PyPDFProcessor()
        
        # Test text with multiple spaces and empty lines
        test_text = "   Multiple    spaces   \n\n  \n  Another line  \n\n"
        cleaned = processor._clean_text(test_text)
        
        # Should have normalized spaces and removed empty lines
        lines = cleaned.split('\n')
        if len(lines) == 2 and "Multiple spaces" in lines[0] and "Another line" in lines[1]:
            return True, "Text cleaning works correctly"
        else:
            return False, f"Text cleaning failed: got {repr(cleaned)}"
    except Exception as e:
        return False, f"Error testing text cleaning: {e}"


def run_tests():
    """Run all processor tests and return results."""
    tests = [
        test_pypdf_processor_initialization,
        test_pypdf_processor_inheritance,
        test_processor_methods_exist,
        test_processor_info,
        test_file_not_found_handling,
        test_text_cleaning
    ]
    
    results = []
    passed = 0
    total = len(tests)
    
    print("Testing PDF Processors")
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
