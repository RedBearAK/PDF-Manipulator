"""
Test module for smart filename pattern functionality.
File: tests/test_smart_filename_patterns.py

Tests the regex pattern extraction and smart filename generation
to ensure the module works correctly after pattern isolation.
"""

from pathlib import Path

from pdf_manipulator.core.smart_filenames import (
    generate_smart_description,
    generate_extraction_filename,
    suggest_batch_naming_scheme,
    _describe_single_argument,
    _sanitize_for_filename,
)


def test_regex_pattern_imports():
    """Test that imported regex patterns work correctly."""
    print("Testing regex pattern functionality...")
    
    results = []
    
    # Test _describe_single_argument with numeric patterns
    test_cases = [
        ("5", "pages5"),
        ("1-10", "pages1-10"),
        ("contains:'test'", "contains_test"),
        ("regex:pattern", "regex_pattern"),
        ("file:data.txt", "data"),
        ("all", "all_pages")
    ]
    
    for input_arg, expected in test_cases:
        try:
            result = _describe_single_argument(input_arg)
            if expected in result or result == expected:
                print(f"  ✓ Argument '{input_arg}' -> '{result}'")
                results.append(True)
            else:
                print(f"  ✗ Argument '{input_arg}' -> '{result}', expected something containing '{expected}'")
                results.append(False)
        except Exception as e:
            print(f"  ✗ Argument '{input_arg}' failed: {e}")
            results.append(False)
    
    return all(results)


def test_filename_sanitization():
    """Test filename sanitization with problematic characters."""
    print("Testing filename sanitization...")
    
    test_cases = [
        ("Test: File<>Name|With*Bad?Chars", "Test_File_Name_With_Bad_Chars"),
        ("  Multiple   Spaces  ", "Multiple_Spaces"),
        ("normal_filename", "normal_filename"),
        ("___too___many___underscores___", "too_many_underscores"),
        ("", "")  # Edge case
    ]
    
    results = []
    
    for input_text, expected in test_cases:
        try:
            result = _sanitize_for_filename(input_text)
            if result == expected:
                print(f"  ✓ '{input_text}' -> '{result}'")
                results.append(True)
            else:
                print(f"  ✗ '{input_text}' -> '{result}', expected '{expected}'")
                results.append(False)
        except Exception as e:
            print(f"  ✗ Sanitization failed for '{input_text}': {e}")
            results.append(False)
    
    return all(results)


def test_smart_description_generation():
    """Test smart description generation for multiple arguments."""
    print("Testing smart description generation...")
    
    test_cases = [
        (["1-5"], 10),
        (["contains:'Alaska'", "contains:'cities'"], 25),
        (["file:data.txt"], 15),
        ([], 0)  # Edge case
    ]
    
    results = []
    
    for arguments, total_pages in test_cases:
        try:
            result = generate_smart_description(arguments, total_pages)
            if result and isinstance(result, str):
                print(f"  ✓ Arguments {arguments} -> '{result}'")
                results.append(True)
            else:
                print(f"  ✗ Arguments {arguments} -> '{result}', expected non-empty string")
                results.append(False)
        except Exception as e:
            print(f"  ✗ Description generation failed for {arguments}: {e}")
            results.append(False)
    
    return all(results)


def test_extraction_filename_generation():
    """Test extraction filename generation."""
    print("Testing extraction filename generation...")
    
    test_pdf_path = Path("test_document.pdf")
    
    test_cases = [
        ("pages1-5", "single", True, None),
        ("contains_Alaska", "separate", False, "custom"),
        ("all_pages", "grouped", True, None)
    ]
    
    results = []
    
    for page_desc, mode, timestamp, prefix in test_cases:
        try:
            result = generate_extraction_filename(test_pdf_path, page_desc, mode, timestamp, prefix)
            if isinstance(result, Path) and result.suffix == '.pdf':
                print(f"  ✓ Generated: '{result.name}' for {page_desc}/{mode}")
                results.append(True)
            else:
                print(f"  ✗ Invalid result: {result}")
                results.append(False)
        except Exception as e:
            print(f"  ✗ Filename generation failed: {e}")
            results.append(False)
    
    return all(results)


def test_batch_naming_scheme():
    """Test batch naming scheme suggestions."""
    print("Testing batch naming scheme generation...")
    
    test_cases = [
        # (pdf_paths, operation, expected_keys)
        ([Path("invoice_2024_01.pdf"), Path("invoice_2024_02.pdf"), Path("invoice_2024_03.pdf")], 
         "page extraction", ["common_prefix", "suggested_base", "operation_desc"]),
        
        ([Path("report_summary.pdf"), Path("report_details.pdf")], 
         "text analysis", ["common_prefix", "suggested_base", "operation_desc"]),
        
        ([Path("document.pdf")], 
         "single extraction", ["suggested_base", "operation_desc", "count"]),
        
        ([Path("different.pdf"), Path("names.pdf"), Path("here.pdf")], 
         "mixed operation", ["suggested_base", "operation_desc", "count"])
    ]
    
    results = []
    
    for pdf_paths, operation, expected_keys in test_cases:
        try:
            result = suggest_batch_naming_scheme(pdf_paths, operation)
            
            # Check that result is a dictionary with expected keys
            if isinstance(result, dict):
                missing_keys = [key for key in expected_keys if key not in result]
                if not missing_keys:
                    print(f"  ✓ Batch scheme for {len(pdf_paths)} files: '{result.get('suggested_base', 'N/A')}'")
                    results.append(True)
                else:
                    print(f"  ✗ Missing keys: {missing_keys}")
                    results.append(False)
            else:
                print(f"  ✗ Expected dict, got {type(result)}")
                results.append(False)
                
        except Exception as e:
            print(f"  ✗ Batch naming failed: {e}")
            results.append(False)
    
    return all(results)


def main():
    """Run all tests and report results."""
    print("Running smart filename pattern tests...\n")
    
    tests = [
        ("Regex pattern imports", test_regex_pattern_imports),
        ("Filename sanitization", test_filename_sanitization),
        ("Smart description generation", test_smart_description_generation),
        ("Extraction filename generation", test_extraction_filename_generation),
        ("Batch naming scheme", test_batch_naming_scheme)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        try:
            if test_func():
                print(f"✓ {test_name}: PASSED")
                passed += 1
            else:
                print(f"✗ {test_name}: FAILED")
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
    
    print(f"\n=== Final Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    return 1 if passed == total else 0


if __name__ == "__main__":
    exit(main())


# End of file #
