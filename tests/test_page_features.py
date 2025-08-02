#!/usr/bin/env python3
"""
Test script for new page type and size analysis features.
Save as: test_page_features.py

Run this to verify that all new functionality works correctly.
"""

import sys
import tempfile

from pathlib import Path
from rich.table import Table
from rich.console import Console

# Add the pdf_manipulator to path if running standalone
sys.path.insert(0, str(Path(__file__).parent))

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.page_analysis import PageAnalyzer
from pdf_manipulator.core.page_range.patterns import looks_like_pattern

console = Console()


def test_pattern_recognition():
    """Test that new patterns are recognized correctly."""
    console.print("\n[yellow]🧪 Testing Pattern Recognition[/yellow]")
    
    test_cases = [
        # Should be recognized as patterns
        ("type:text", True),
        ("type:image", True),
        ("type:mixed", True),
        ("type:empty", True),
        ("size:>1MB", True),
        ("size:<500KB", True),
        ("size:>=2MB", True),
        ("size:<=100KB", True),
        ("contains:'text'", True),
        ("regex:'pattern'", True),
        ("line-starts:'Chapter'", True),
        
        # Should NOT be recognized as patterns
        ("5", False),
        ("3-7", False),
        ("first 3", False),
        ("last 2", False),
        ("all", False),
    ]
    
    success_count = 0
    for pattern, expected in test_cases:
        result = looks_like_pattern(pattern)
        status = "✓" if result == expected else "✗"
        color = "green" if result == expected else "red"
        
        console.print(f"  [{color}]{status}[/{color}] {pattern:>15} → {result} (expected {expected})")
        
        if result == expected:
            success_count += 1
    
    console.print(f"\n  Result: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)


def test_size_parsing():
    """Test size condition parsing."""
    console.print("\n[yellow]🧪 Testing Size Condition Parsing[/yellow]")
    
    from pdf_manipulator.core.page_analysis import PageAnalyzer
    
    # Create a dummy analyzer to test parsing
    test_cases = [
        ("<500KB", ("<", 512000)),
        (">1MB", (">", 1048576)),
        (">=2MB", (">=", 2097152)),
        ("<=100KB", ("<=", 102400)),
        ("=1MB", ("=", 1048576)),
        ("<1.5GB", ("<", 1610612736)),
    ]
    
    success_count = 0
    for condition, expected in test_cases:
        try:
            # Create a minimal analyzer instance to test the parsing method
            analyzer = PageAnalyzer.__new__(PageAnalyzer)  # Don't call __init__
            result = analyzer._parse_size_condition(condition)
            
            status = "✓" if result == expected else "✗"
            color = "green" if result == expected else "red"
            
            console.print(f"  [{color}]{status}[/{color}] {condition:>8} → {result} (expected {expected})")
            
            if result == expected:
                success_count += 1
                
        except Exception as e:
            console.print(f"  [red]✗[/red] {condition:>8} → Error: {e}")
    
    console.print(f"\n  Result: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)


def test_page_classification():
    """Test page type classification logic."""
    console.print("\n[yellow]🧪 Testing Page Classification Logic[/yellow]")
    
    from pdf_manipulator.core.page_analysis import PageAnalyzer
    
    # Test classification with mock data
    test_cases = [
        # (text_content, image_count, expected_type, description)
        ("", 0, "empty", "No text, no images"),
        ("Short", 0, "empty", "Very short text, no images"),
        ("A" * 100, 0, "text", "Meaningful text, no images"),
        ("", 3, "image", "No text, has images"),
        ("A" * 100, 2, "mixed", "Meaningful text and images"),
        ("A" * 10, 1, "image", "Little text, has images"),
    ]
    
    success_count = 0
    analyzer = PageAnalyzer.__new__(PageAnalyzer)  # Don't call __init__
    
    for text_content, image_count, expected_type, description in test_cases:
        try:
            result_type, confidence = analyzer._classify_page_type(text_content, image_count)
            
            status = "✓" if result_type == expected_type else "✗"
            color = "green" if result_type == expected_type else "red"
            
            console.print(f"  [{color}]{status}[/{color}] {description:>30} → {result_type:>6} (conf: {confidence:.2f})")
            
            if result_type == expected_type:
                success_count += 1
                
        except Exception as e:
            console.print(f"  [red]✗[/red] {description:>30} → Error: {e}")
    
    console.print(f"\n  Result: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)


def debug_boolean_detection():
    """Debug boolean expression detection step-by-step."""
    console.print("\n[yellow]🧪 Testing Boolean Expression Detection[/yellow]")
    
    from pdf_manipulator.core.page_range.boolean import looks_like_boolean_expression
    
    test_cases = [
        # Should be detected as boolean
        ("type:image | type:mixed", True, "OR expression"),
        ("type:text & size:<500KB", True, "AND expression"), 
        ("all & !type:empty", True, "AND NOT expression"),
        ("(type:text | type:mixed) & size:<500KB", True, "Parentheses grouping"),
        
        # Should NOT be detected as boolean (quotes protect operators)
        ("contains:'text & text'", False, "Literal & inside quotes"),
        ("regex:'A|B|C'", False, "Literal | inside quotes"),
        ("line-starts:'! Important'", False, "Literal ! inside quotes"),
        
        # Should NOT be detected (improper spacing)
        ("type:text&size:<500KB", False, "No spaces around &"),
        ("type:text  &  size:<500KB", False, "Multiple spaces around &"),
        ("type:text|type:mixed", False, "No spaces around |"),
        
        # Simple patterns (not boolean)
        ("type:text", False, "Single pattern"),
        ("5", False, "Number"),
        ("3-7", False, "Range"),
    ]
    
    success_count = 0
    for case, expected, description in test_cases:
        result = looks_like_boolean_expression(case)
        
        status = "✓" if result == expected else "✗"
        color = "green" if result == expected else "red"
        
        console.print(f"  [{color}]{status}[/{color}] {description}")
        console.print(f"      '{case}' → {result} (expected {expected})")
        
        if result == expected:
            success_count += 1
    
    console.print(f"\n  Result: {success_count}/{len(test_cases)} detection tests passed")
    return success_count == len(test_cases)


def debug_boolean_parsing():
    """Debug boolean expression parsing with detailed output including complex cases."""
    console.print("\n[yellow]🧪 Testing Boolean Expression Parsing[/yellow]")
    
    from pdf_manipulator.core.page_range.boolean import parse_boolean_expression
    from pdf_manipulator.core.parser import parse_page_range
    
    # Create a real test PDF to use
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        console.print("  [yellow]Skipping boolean parsing debug - no test PDF[/yellow]")
        return False
    
    try:
        test_cases = [
            # Basic boolean expressions
            ("type:image | type:mixed", "OR expression with no matches"),
            ("type:text & size:<500KB", "AND expression with matches"),
            ("all & !type:empty", "NOT expression"),
            
            # Parentheses grouping
            ("(type:text | type:mixed) & size:<500KB", "Parentheses grouping"),
            ("type:text & (size:<500KB | size:>1MB)", "Parentheses with OR"),
            
            # Quote protection
            ("contains:'text with spaces'", "Single pattern with spaces"),
            
            # Complex expressions
            ("type:text | (type:mixed & size:>1MB)", "Complex with parentheses"),
        ]
        
        success_count = 0
        for test_expr, description in test_cases:
            console.print(f"\n  Testing: '{test_expr}'")
            console.print(f"  Description: {description}")
            
            try:
                # Test integration with main parser (this is what users actually call)
                pages, desc, groups = parse_page_range(test_expr, 3, test_pdf_path)
                console.print(f"    ✓ Result: {len(pages)} pages found")
                console.print(f"    ✓ Description: '{desc}'")
                console.print(f"    ✓ Pages: {sorted(list(pages)) if pages else 'none'}")
                
                success_count += 1
                
            except Exception as e:
                console.print(f"    ✗ Exception: {type(e).__name__}: {e}")
        
        console.print(f"\n  Result: {success_count}/{len(test_cases)} parsing tests passed")
        return success_count == len(test_cases)
        
    finally:
        # Clean up test PDF
        test_pdf_path.unlink(missing_ok=True)


def test_case_insensitive_patterns():
    """Test case-insensitive pattern functionality."""
    console.print("\n[yellow]🧪 Testing Case-Insensitive Patterns[/yellow]")
    
    from pdf_manipulator.core.page_range.patterns import looks_like_pattern
    
    # Test pattern recognition for case-insensitive patterns
    pattern_tests = [
        ("contains/i:'text'", True, "Case-insensitive contains"),
        ("regex/i:'pattern'", True, "Case-insensitive regex"),
        ("line-starts/i:'chapter'", True, "Case-insensitive line-starts"),
        ("type/i:text", True, "Case-insensitive type (though type doesn't need it)"),
        ("size/i:>1MB", True, "Case-insensitive size (though size doesn't need it)"),
    ]
    
    recognition_success = 0
    for pattern, expected, description in pattern_tests:
        result = looks_like_pattern(pattern)
        status = "✓" if result == expected else "✗"
        color = "green" if result == expected else "red"
        console.print(f"  [{color}]{status}[/{color}] {description}: '{pattern}' → {result}")
        if result == expected:
            recognition_success += 1
    
    console.print(f"\n  Pattern recognition: {recognition_success}/{len(pattern_tests)} tests passed")
    
    # Test actual parsing with real PDF
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        console.print("  [yellow]Skipping parsing tests - no test PDF[/yellow]")
        return recognition_success == len(pattern_tests)
    
    try:
        from pdf_manipulator.core.parser import parse_page_range
        
        parsing_tests = [
            # Single case-insensitive patterns
            ("contains/i:'lorem'", "Case-insensitive text search"),
            ("contains/i:'LOREM'", "Case-insensitive CAPS text search"),
            ("line-starts/i:'this'", "Case-insensitive line start"),
            
            # Boolean expressions with case-insensitive patterns
            ("contains/i:'lorem' & type:text", "Case-insensitive in boolean AND"),
            ("contains/i:'MISSING' | type:text", "Case-insensitive in boolean OR"),
            ("type:text & !contains/i:'DRAFT'", "Case-insensitive in boolean NOT"),
            
            # Mixed case sensitivity in same expression
            ("contains:'Lorem' | contains/i:'lorem'", "Mixed case sensitivity"),
        ]
        
        parsing_success = 0
        for pattern, description in parsing_tests:
            try:
                pages, desc, groups = parse_page_range(pattern, 3, test_pdf_path)
                console.print(f"  ✓ {description}: '{pattern}' → {len(pages)} pages")
                parsing_success += 1
            except Exception as e:
                console.print(f"  ✗ {description}: '{pattern}' → Error: {e}")
        
        console.print(f"\n  Pattern parsing: {parsing_success}/{len(parsing_tests)} tests passed")
        total_success = recognition_success + parsing_success
        total_tests = len(pattern_tests) + len(parsing_tests)
        
        console.print(f"\n  Overall case-insensitive tests: {total_success}/{total_tests} passed")
        return total_success == total_tests
        
    finally:
        test_pdf_path.unlink(missing_ok=True)


def test_with_real_pdf(pdf_path: Path):
    """Test case-insensitive pattern functionality."""
    console.print("\n[yellow]🧪 Testing Case-Insensitive Patterns[/yellow]")
    
    from pdf_manipulator.core.page_range.patterns import looks_like_pattern
    
    # Test pattern recognition for case-insensitive patterns
    pattern_tests = [
        ("contains/i:'text'", True, "Case-insensitive contains"),
        ("regex/i:'pattern'", True, "Case-insensitive regex"),
        ("line-starts/i:'chapter'", True, "Case-insensitive line-starts"),
        ("type/i:text", True, "Case-insensitive type (though type doesn't need it)"),
        ("size/i:>1MB", True, "Case-insensitive size (though size doesn't need it)"),
    ]
    
    recognition_success = 0
    for pattern, expected, description in pattern_tests:
        result = looks_like_pattern(pattern)
        status = "✓" if result == expected else "✗"
        color = "green" if result == expected else "red"
        console.print(f"  [{color}]{status}[/{color}] {description}: '{pattern}' → {result}")
        if result == expected:
            recognition_success += 1
    
    console.print(f"\n  Pattern recognition: {recognition_success}/{len(pattern_tests)} tests passed")
    
    # Test actual parsing with real PDF
    test_pdf_path = create_test_pdf()
    if not test_pdf_path:
        console.print("  [yellow]Skipping parsing tests - no test PDF[/yellow]")
        return recognition_success == len(pattern_tests)
    
    try:
        from pdf_manipulator.core.parser import parse_page_range
        
        parsing_tests = [
            # Single case-insensitive patterns
            ("contains/i:'lorem'", "Case-insensitive text search"),
            ("contains/i:'LOREM'", "Case-insensitive CAPS text search"),
            ("line-starts/i:'this'", "Case-insensitive line start"),
            
            # Boolean expressions with case-insensitive patterns
            ("contains/i:'lorem' & type:text", "Case-insensitive in boolean AND"),
            ("contains/i:'MISSING' | type:text", "Case-insensitive in boolean OR"),
            ("type:text & !contains/i:'DRAFT'", "Case-insensitive in boolean NOT"),
            
            # Mixed case sensitivity in same expression
            ("contains:'Lorem' | contains/i:'lorem'", "Mixed case sensitivity"),
        ]
        
        parsing_success = 0
        for pattern, description in parsing_tests:
            try:
                pages, desc, groups = parse_page_range(pattern, 3, test_pdf_path)
                console.print(f"  ✓ {description}: '{pattern}' → {len(pages)} pages")
                parsing_success += 1
            except Exception as e:
                console.print(f"  ✗ {description}: '{pattern}' → Error: {e}")
        
        console.print(f"\n  Pattern parsing: {parsing_success}/{len(parsing_tests)} tests passed")
        total_success = recognition_success + parsing_success
        total_tests = len(pattern_tests) + len(parsing_tests)
        
        console.print(f"\n  Overall case-insensitive tests: {total_success}/{total_tests} passed")
        return total_success == total_tests
        
    finally:
        test_pdf_path.unlink(missing_ok=True)
    """Test with a real PDF file."""
    console.print(f"\n[yellow]🧪 Testing with Real PDF: {pdf_path.name}[/yellow]")
    
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            total_pages = len(analyzer.reader.pages)
            console.print(f"  PDF has {total_pages} pages")
            
            # Test basic analysis
            console.print("  Testing page analysis...")
            analysis = analyzer.analyze_page(1)
            console.print(f"    Page 1: {analysis.page_type}, {analysis.size_kb:.1f} KB, {analysis.text_length} chars")
            
            # Test type-based queries
            console.print("  Testing type-based queries...")
            for page_type in ['text', 'image', 'mixed', 'empty']:
                try:
                    pages = analyzer.get_pages_by_type(page_type)
                    console.print(f"    {page_type:>6}: {len(pages)} pages")
                except Exception as e:
                    console.print(f"    {page_type:>6}: Error - {e}")
            
            # Test size-based queries
            console.print("  Testing size-based queries...")
            size_conditions = ['>1MB', '<500KB', '>=100KB']
            for condition in size_conditions:
                try:
                    pages = analyzer.get_pages_by_size(condition)
                    console.print(f"    {condition:>8}: {len(pages)} pages")
                except Exception as e:
                    console.print(f"    {condition:>8}: Error - {e}")
            
            # Test pattern parsing integration
            console.print("  Testing pattern parsing integration...")
            test_patterns = [
                "type:text",
                "size:>1MB", 
                "type:text & size:<500KB",
                "type:image | type:mixed",
                # Add case-insensitive tests
                "contains/i:'lorem'",
                "contains/i:'LOREM'",
                "contains/i:'text' & type:text"
            ]
            
            for pattern in test_patterns:
                try:
                    matching_pages, desc, groups = parse_page_range(pattern, total_pages, pdf_path)
                    console.print(f"    {pattern:>25}: {len(matching_pages)} pages")
                except Exception as e:
                    console.print(f"    {pattern:>25}: Error - {e}")
            
            console.print("  [green]✓ Real PDF test completed[/green]")
            return True
            
    except Exception as e:
        console.print(f"  [red]✗ Real PDF test failed: {e}[/red]")
        return False


def create_test_pdf():
    """Create a simple test PDF for testing."""
    console.print("\n[yellow]🧪 Creating Test PDF[/yellow]")
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Create temporary PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        c = canvas.Canvas(str(tmp_path), pagesize=letter)
        
        # Page 1: Text page
        c.drawString(100, 750, "This is a text-heavy page with lots of content.")
        c.drawString(100, 730, "Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
        c.drawString(100, 710, "This page should be classified as 'text' type.")
        for i in range(10):
            c.drawString(100, 690 - i*20, f"Line {i+1}: More text content to make this a substantial text page.")
        c.showPage()
        
        # Page 2: Minimal text page (should be 'empty')
        c.drawString(100, 750, "Minimal")
        c.showPage()
        
        # Page 3: Another text page
        c.drawString(100, 750, "Another text page with reasonable content length.")
        c.drawString(100, 730, "This should also be classified as text type.")
        for i in range(5):
            c.drawString(100, 710 - i*20, f"Additional line {i+1} of meaningful content.")
        c.showPage()
        
        c.save()
        
        console.print(f"  Created test PDF: {tmp_path}")
        return tmp_path
        
    except ImportError:
        console.print("  [yellow]⚠ reportlab not available, skipping test PDF creation[/yellow]")
        return None
    except Exception as e:
        console.print(f"  [red]✗ Failed to create test PDF: {e}[/red]")
        return None


def main():
    """Run all tests."""
    console.print("[bold green]🧪 PDF Manipulator - Page Analysis Feature Tests[/bold green]\n")
    
    test_results = []
    
    # Test 1: Pattern recognition
    test_results.append(("Pattern Recognition", test_pattern_recognition()))
    
    # Test 2: Size parsing
    test_results.append(("Size Parsing", test_size_parsing()))
    
    # Test 3: Page classification
    test_results.append(("Page Classification", test_page_classification()))
    
    # Test 4: Test case-insensitive pattern functionality
    test_results.append(("Case-Insensitive Patterns", test_case_insensitive_patterns()))
    
    # Test 5: Debug boolean detection step-by-step
    test_results.append(("Boolean Expression Detection", debug_boolean_detection()))
    
    # Test 5: Debug boolean parsing with detailed output
    test_results.append(("Boolean Expression Parsing", debug_boolean_parsing()))
    
    # Test 6: Create and test with generated PDF
    test_pdf_path = create_test_pdf()
    if test_pdf_path:
        test_results.append(("Test PDF Analysis", test_with_real_pdf(test_pdf_path)))
        # Clean up
        test_pdf_path.unlink(missing_ok=True)
    
    # Test 7: Test with user-provided PDF if available
    if len(sys.argv) > 1:
        user_pdf = Path(sys.argv[1])
        if user_pdf.exists() and user_pdf.suffix.lower() == '.pdf':
            test_results.append(("User PDF Analysis", test_with_real_pdf(user_pdf)))
    
    # Summary
    console.print("\n[bold blue]📊 Test Results Summary[/bold blue]\n")
    
    table = Table()
    table.add_column("Test", style="cyan")
    table.add_column("Result", style="white")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "[green]✓ PASS[/green]" if result else "[red]✗ FAIL[/red]"
        table.add_row(test_name, status)
        if result:
            passed += 1
    
    console.print(table)
    console.print(f"\n[bold]Overall: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All tests passed! The new features are working correctly.[/bold green]")
        console.print("\n[yellow]💡 You can now use these new patterns:[/yellow]")
        console.print("  • type:text, type:image, type:mixed, type:empty")
        console.print("  • size:<500KB, size:>1MB, size:>=2MB, size:<=100KB")
        console.print("  • Boolean combinations with &, |, !")
        return 0
    else:
        console.print(f"\n[bold red]❌ {total - passed} test(s) failed. Please check the implementation.[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
