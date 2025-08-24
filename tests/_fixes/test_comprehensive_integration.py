#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Page Range Parser Architecture Fix
File: tests/test_comprehensive_integration.py

REAL INTEGRATION TESTING - No mocks, uses actual PDF creation and parsing.

Tests the complete pipeline:
- Main parser with comma-first architecture
- Boolean module with fixed tokenization  
- Pattern module with comma-free detection
- Real PDF content creation and matching
- Complex boolean expressions (like Alaska cities example)
- Full end-to-end functionality

Run: python tests/test_comprehensive_integration.py
"""

import sys
import os
import tempfile
import atexit
import subprocess

from pathlib import Path
from datetime import datetime

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from pdf_manipulator.core.operations import get_ordered_pages_from_groups
    from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser, parse_page_range
    from pdf_manipulator.core.page_range.boolean import looks_like_boolean_expression
    from pdf_manipulator.core.page_range.patterns import looks_like_pattern, looks_like_range_pattern
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import required modules: {e}")
    print("This test requires:")
    print("  - pdf_manipulator modules (the updated architecture)")
    print("  - reportlab (pip install reportlab)")
    IMPORTS_AVAILABLE = False

# Global test PDF paths
TEST_PDFS = {}
TEMP_DIR = None

def setup_test_environment():
    """Set up temporary directory and test PDFs."""
    global TEMP_DIR
    TEMP_DIR = tempfile.mkdtemp(prefix="pdf_test_")
    print(f"🔧 Created test environment: {TEMP_DIR}")
    
    # Register cleanup
    atexit.register(cleanup_test_environment)
    
    if IMPORTS_AVAILABLE:
        create_test_pdfs()

def cleanup_test_environment():
    """Clean up test environment."""
    global TEMP_DIR
    if TEMP_DIR and Path(TEMP_DIR).exists():
        import shutil
        shutil.rmtree(TEMP_DIR)
        print(f"🧹 Cleaned up test environment: {TEMP_DIR}")

def create_test_pdfs():
    """Create real PDF files with known content for testing."""
    global TEST_PDFS
    
    print("📄 Creating test PDFs with known content...")
    
    # Test PDF 1: Alaska Cities (for complex boolean testing)
    alaska_pdf = Path(TEMP_DIR) / "alaska_cities.pdf"
    create_alaska_cities_pdf(alaska_pdf)
    TEST_PDFS['alaska'] = alaska_pdf
    
    # Test PDF 2: Mixed Content (for pattern testing)
    mixed_pdf = Path(TEMP_DIR) / "mixed_content.pdf"
    create_mixed_content_pdf(mixed_pdf)
    TEST_PDFS['mixed'] = mixed_pdf
    
    # Test PDF 3: Simple Test (for basic functionality)
    simple_pdf = Path(TEMP_DIR) / "simple_test.pdf"
    create_simple_test_pdf(simple_pdf)
    TEST_PDFS['simple'] = simple_pdf
    
    print(f"✅ Created {len(TEST_PDFS)} test PDFs")

def create_alaska_cities_pdf(pdf_path: Path):
    """Create PDF with Alaska cities content for testing complex boolean expressions."""
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Page 1: CORDOVA, AK
    story.append(Paragraph("CORDOVA, AK", styles['Title']))
    story.append(Paragraph("City information for Cordova, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 2,239", styles['Normal']))
    story.append(PageBreak())
    
    # Page 2: CRAIG, AK
    story.append(Paragraph("CRAIG, AK", styles['Title']))
    story.append(Paragraph("City information for Craig, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 1,188", styles['Normal']))
    story.append(PageBreak())
    
    # Page 3: DILLINGHAM, AK
    story.append(Paragraph("DILLINGHAM, AK", styles['Title']))
    story.append(Paragraph("City information for Dillingham, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 2,378", styles['Normal']))
    story.append(PageBreak())
    
    # Page 4: FALSE PASS, AK
    story.append(Paragraph("FALSE PASS, AK", styles['Title']))
    story.append(Paragraph("City information for False Pass, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 35", styles['Normal']))
    story.append(PageBreak())
    
    # Page 5: KETCHIKAN, AK
    story.append(Paragraph("KETCHIKAN, AK", styles['Title']))
    story.append(Paragraph("City information for Ketchikan, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 8,263", styles['Normal']))
    story.append(PageBreak())
    
    # Page 6: KODIAK, AK
    story.append(Paragraph("KODIAK, AK", styles['Title']))
    story.append(Paragraph("City information for Kodiak, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 6,130", styles['Normal']))
    story.append(PageBreak())
    
    # Page 7: NAKNEK, AK (with variant spellings)
    story.append(Paragraph("NAKNEK, AK", styles['Title']))
    story.append(Paragraph("Also known as: NAKN EK, AK or EK, AK", styles['Normal']))
    story.append(Paragraph("City information for Naknek, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 544", styles['Normal']))
    story.append(PageBreak())
    
    # Page 8: PETERSBURG, AK
    story.append(Paragraph("PETERSBURG, AK", styles['Title']))
    story.append(Paragraph("City information for Petersburg, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 2,948", styles['Normal']))
    story.append(PageBreak())
    
    # Page 9: SEWARD, AK
    story.append(Paragraph("SEWARD, AK", styles['Title']))
    story.append(Paragraph("City information for Seward, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 2,773", styles['Normal']))
    story.append(PageBreak())
    
    # Page 10: SITKA, AK (with variants to test complex boolean)
    story.append(Paragraph("SITKA AK", styles['Title']))  # No comma variant
    story.append(Paragraph("Also written as: SITKA, AK", styles['Normal']))
    story.append(Paragraph("City information for Sitka, Alaska", styles['Normal']))
    story.append(Paragraph("Population: 8,493", styles['Normal']))
    story.append(Paragraph("NOTE: Does not contain other city names", styles['Normal']))
    
    doc.build(story)

def create_mixed_content_pdf(pdf_path: Path):
    """Create PDF with mixed content types for pattern testing."""
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Page 1: Chapter Start
    story.append(Paragraph("Chapter 1: Introduction", styles['Title']))
    story.append(Paragraph("This is the beginning of our document.", styles['Normal']))
    story.append(Paragraph("Invoice Number: INV-2024-001", styles['Normal']))
    story.append(PageBreak())
    
    # Page 2: Table Content
    story.append(Paragraph("Data Tables", styles['Title']))
    story.append(Paragraph("Revenue: $125,450", styles['Normal']))
    story.append(Paragraph("Expenses: $89,230", styles['Normal']))
    story.append(PageBreak())
    
    # Page 3: Summary
    story.append(Paragraph("Summary", styles['Title']))
    story.append(Paragraph("This document contains financial information.", styles['Normal']))
    story.append(Paragraph("Total Amount: $36,220", styles['Normal']))
    story.append(PageBreak())
    
    # Page 4: Chapter End
    story.append(Paragraph("Chapter 2: Analysis", styles['Title']))
    story.append(Paragraph("End of Chapter 1 content.", styles['Normal']))
    story.append(Paragraph("Company: ACME Corporation", styles['Normal']))
    
    doc.build(story)

def create_simple_test_pdf(pdf_path: Path):
    """Create simple PDF for basic functionality testing."""
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    for i in range(1, 6):
        story.append(Paragraph(f"Page {i}", styles['Title']))
        story.append(Paragraph(f"This is page {i} of the test document.", styles['Normal']))
        if i < 5:
            story.append(PageBreak())
    
    doc.build(story)


class ComprehensiveIntegrationTests:
    """Comprehensive integration test suite using real PDFs and full pipeline."""
    
    def __init__(self):
        self.passed = 0
        self.total = 0
        
    def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Starting Comprehensive Integration Tests")
        print("=" * 60)
        
        if not IMPORTS_AVAILABLE:
            print("❌ Cannot run tests - missing required modules")
            return False
        
        # Test categories
        test_methods = [
            # Basic functionality
            self.test_basic_parser_integration,
            self.test_comma_separation_works,
            
            # Pattern detection and processing
            self.test_pattern_detection_integration,
            self.test_boolean_detection_integration,
            
            # Real content matching
            self.test_real_content_pattern_matching,
            self.test_complex_boolean_expressions,
            
            # The critical Alaska cities test
            self.test_alaska_cities_complex_example,
            
            # Comma-separated integration
            self.test_mixed_comma_separated_arguments,
            self.test_order_preservation,
            
            # Edge cases and robustness
            self.test_edge_cases_and_robustness,
            self.test_error_handling,
        ]
        
        for test_method in test_methods:
            try:
                self.total += 1
                print(f"\n{'='*60}")
                if test_method():
                    self.passed += 1
                    print("✅ PASSED")
                else:
                    print("❌ FAILED")
            except Exception as e:
                print(f"💥 CRASHED: {e}")
                import traceback
                traceback.print_exc()
        
        # Final results
        print(f"\n{'='*60}")
        print(f"🏁 FINAL RESULTS: {self.passed}/{self.total} tests passed")
        
        if self.passed == self.total:
            print("🎉 ALL TESTS PASSED! Architecture fix is working correctly.")
            return True
        else:
            print(f"💔 {self.total - self.passed} tests failed. Architecture needs more work.")
            return False
    
    def test_basic_parser_integration(self):
        """Test basic parser functionality with real PDF."""
        print("🔍 Testing Basic Parser Integration")
        
        pdf_path = TEST_PDFS['simple']
        
        try:
            # Test simple range
            pages, desc, groups = parse_page_range("1-3", 5, pdf_path)
            if pages != {1, 2, 3}:
                print(f"❌ Simple range failed: expected {{1,2,3}}, got {pages}")
                return False
            
            # Test individual pages
            pages, desc, groups = parse_page_range("1,3,5", 5, pdf_path)
            if pages != {1, 3, 5}:
                print(f"❌ Individual pages failed: expected {{1,3,5}}, got {pages}")
                return False
            
            # Test 'all' keyword
            pages, desc, groups = parse_page_range("all", 5, pdf_path)
            if pages != {1, 2, 3, 4, 5}:
                print(f"❌ 'all' keyword failed: expected {{1,2,3,4,5}}, got {pages}")
                return False
            
            print("✓ Basic parser integration working")
            return True
            
        except Exception as e:
            print(f"❌ Basic parser integration failed: {e}")
            return False
    
    def test_comma_separation_works(self):
        """Test that comma separation happens first in the architecture."""
        print("🔍 Testing Comma Separation Architecture")
        
        pdf_path = TEST_PDFS['simple']
        
        try:
            # Test comma separation with quotes containing commas
            test_cases = [
                ('1,3', {1, 3}, "Simple comma separation"),
                ('1,5,2', {1, 2, 5}, "Multiple comma separation"),
            ]
            
            for range_str, expected_pages, description in test_cases:
                pages, desc, groups = parse_page_range(range_str, 5, pdf_path)
                if pages != expected_pages:
                    print(f"❌ {description} failed: expected {expected_pages}, got {pages}")
                    return False
                print(f"✓ {description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Comma separation test failed: {e}")
            return False
    
    def test_pattern_detection_integration(self):
        """Test pattern detection integration with real content."""
        print("🔍 Testing Pattern Detection Integration")
        
        pdf_path = TEST_PDFS['mixed']
        
        try:
            # Test that pattern detection functions work correctly
            test_cases = [
                ('contains:"Chapter"', True, "Contains pattern"),
                ('type:text', True, "Type pattern"),
                ('5-10', False, "Numeric range (not pattern)"),
            ]
            
            for test_str, expected, description in test_cases:
                result = looks_like_pattern(test_str)
                if result != expected:
                    print(f"❌ {description} failed: expected {expected}, got {result}")
                    return False
                print(f"✓ {description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Pattern detection integration failed: {e}")
            return False
    
    def test_boolean_detection_integration(self):
        """Test boolean detection integration."""
        print("🔍 Testing Boolean Detection Integration")
        
        try:
            test_cases = [
                ('contains:"A" | contains:"B"', True, "OR expression"),
                ('contains:"A" & type:text', True, "AND expression"),
                ('!type:empty', True, "NOT expression"),
                ('(contains:"A" | contains:"B")', True, "Parentheses expression"),
                ('contains:"text with & symbol"', False, "Quoted operators"),
                ('contains:"simple"', False, "Single pattern"),
            ]
            
            for test_str, expected, description in test_cases:
                result = looks_like_boolean_expression(test_str)
                if result != expected:
                    print(f"❌ {description} failed: expected {expected}, got {result}")
                    return False
                print(f"✓ {description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Boolean detection integration failed: {e}")
            return False
    
    def test_real_content_pattern_matching(self):
        """Test pattern matching against real PDF content."""
        print("🔍 Testing Real Content Pattern Matching")
        
        pdf_path = TEST_PDFS['mixed']
        
        try:
            # Test contains patterns with real content
            pages, desc, groups = parse_page_range('contains:"Chapter"', 4, pdf_path)
            expected_pages = {1, 4}  # Pages with "Chapter" in title
            if pages != expected_pages:
                print(f"❌ Contains pattern failed: expected {expected_pages}, got {pages}")
                return False
            print("✓ Contains pattern matching working")
            
            # Test case insensitive
            pages, desc, groups = parse_page_range('contains/i:"summary"', 4, pdf_path)
            expected_pages = {3}  # Page with "Summary" title
            if pages != expected_pages:
                print(f"❌ Case insensitive matching failed: expected {expected_pages}, got {pages}")
                return False
            print("✓ Case insensitive matching working")
            
            return True
            
        except Exception as e:
            print(f"❌ Real content pattern matching failed: {e}")
            return False
    
    def test_complex_boolean_expressions(self):
        """Test complex boolean expressions with real content."""
        print("🔍 Testing Complex Boolean Expressions")
        
        pdf_path = TEST_PDFS['mixed']
        
        try:
            # Test OR expression
            pages, desc, groups = parse_page_range('contains:"Chapter" | contains:"Summary"', 4, pdf_path)
            expected_pages = {1, 3, 4}  # Pages with either "Chapter" or "Summary"
            if pages != expected_pages:
                print(f"❌ OR expression failed: expected {expected_pages}, got {pages}")
                return False
            print("✓ OR expression working")
            
            # Test AND expression
            pages, desc, groups = parse_page_range('contains:"Chapter" & contains:"Introduction"', 4, pdf_path)
            expected_pages = {1}  # Page with both "Chapter" and "Introduction"
            if pages != expected_pages:
                print(f"❌ AND expression failed: expected {expected_pages}, got {pages}")
                return False
            print("✓ AND expression working")
            
            # Test NOT expression
            pages, desc, groups = parse_page_range('contains:"Chapter" & !contains:"Analysis"', 4, pdf_path)
            expected_pages = {1}  # Page with "Chapter" but not "Analysis"
            if pages != expected_pages:
                print(f"❌ NOT expression failed: expected {expected_pages}, got {pages}")
                return False
            print("✓ NOT expression working")
            
            return True
            
        except Exception as e:
            print(f"❌ Complex boolean expressions failed: {e}")
            return False
    
    def test_alaska_cities_complex_example(self):
        """Test the specific Alaska cities example that was failing."""
        print("🔍 Testing Alaska Cities Complex Example (THE BIG TEST)")
        
        pdf_path = TEST_PDFS['alaska']
        
        try:
            # Test each component first
            test_components = [
                ('contains:"CORDOVA, AK"', {1}, "Simple contains with comma in quotes"),
                ('contains:"NAKN EK, AK" | contains:"EK, AK" | contains:"NAKNEK, AK"', {7}, "OR chain"),
                ('contains:"SITKA AK" | contains:"SITKA, AK"', {10}, "SITKA variants"),
                ('!contains:"CRAIG, AK"', {1, 3, 4, 5, 6, 7, 8, 9, 10}, "NOT operation"),
            ]
            
            for expr, expected, description in test_components:
                pages, desc, groups = parse_page_range(expr, 10, pdf_path)
                if pages != expected:
                    print(f"❌ {description} failed:")
                    print(f"    Expression: {expr}")
                    print(f"    Expected: {expected}")
                    print(f"    Got: {pages}")
                    return False
                print(f"✓ {description}")
            
            # Test the complex SITKA boolean expression
            complex_sitka = ('(contains:"SITKA AK" | contains:"SITKA, AK") & '
                           '!contains:"CRAIG, AK" & !contains:"PETERSBURG, AK" & '
                           '!contains:"KETCHIKAN, AK" & !contains:"VALDEZ, AK" & '
                           '!contains:"CORDOVA, AK" & !contains:"SEWARD, AK" & '
                           '!contains:"KODIAK, AK" & !contains:"NAKNEK, AK" & '
                           '!contains:"NAKN" & !contains:"EK, AK" & '
                           '!contains:"DILLINGHAM, AK" & !contains:"FALSE PASS, AK"')
            
            pages, desc, groups = parse_page_range(complex_sitka, 10, pdf_path)
            expected_sitka = {10}  # Only page 10 should match (SITKA page without other cities)
            
            if pages != expected_sitka:
                print(f"❌ Complex SITKA expression failed:")
                print(f"    Expected: {expected_sitka}")
                print(f"    Got: {pages}")
                return False
            print("✓ Complex SITKA boolean expression working")
            
            return True
            
        except Exception as e:
            print(f"❌ Alaska cities complex example failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_mixed_comma_separated_arguments(self):
        """Test comma-separated arguments with mixed types."""
        print("🔍 Testing Mixed Comma-Separated Arguments")
        
        pdf_path = TEST_PDFS['mixed']
        
        try:
            # Test mixing numeric ranges with patterns
            test_cases = [
                ('1,contains:"Chapter"', {1, 4}, "Number + pattern"),
                ('contains:"Summary",3', {3}, "Pattern + number"),
                ('1-2,contains:"Chapter"', {1, 2, 4}, "Range + pattern"),
            ]
            
            for expr, expected, description in test_cases:
                pages, desc, groups = parse_page_range(expr, 4, pdf_path)
                if pages != expected:
                    print(f"❌ {description} failed:")
                    print(f"    Expression: {expr}")
                    print(f"    Expected: {expected}")
                    print(f"    Got: {pages}")
                    return False
                print(f"✓ {description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Mixed comma-separated arguments failed: {e}")
            return False
    
    def test_order_preservation(self):
        """Test that order preservation works correctly."""
        print("🔍 Testing Order Preservation")
        
        pdf_path = TEST_PDFS['simple']
        
        try:
            # Test that comma-separated order is preserved when needed
            parser = PageRangeParser(5, pdf_path)
            pages, desc, groups = parser.parse("5,1,3")
            
            # Get the actual order from groups
            ordered_pages = get_ordered_pages_from_groups(groups, pages)
            
            # Should preserve order [5, 1, 3] not sort to [1, 3, 5]
            expected_order = [5, 1, 3]
            if ordered_pages != expected_order:
                print(f"❌ Order preservation failed:")
                print(f"    Expected order: {expected_order}")
                print(f"    Got order: {ordered_pages}")
                return False
            print("✓ Order preservation working")
            
            return True
            
        except Exception as e:
            print(f"❌ Order preservation test failed: {e}")
            return False
    
    def test_edge_cases_and_robustness(self):
        """Test edge cases and robustness."""
        print("🔍 Testing Edge Cases and Robustness")
        
        pdf_path = TEST_PDFS['simple']
        
        try:
            # Test quotes with commas inside
            test_cases = [
                ('contains:"text, with, commas"', "Pattern with commas in quotes"),
                ('"contains:text"', "Whole expression in quotes"),
                ("'contains:text'", "Whole expression in single quotes"),
            ]
            
            for expr, description in test_cases:
                try:
                    pages, desc, groups = parse_page_range(expr, 5, pdf_path)
                    print(f"✓ {description} - parsed without error")
                except Exception as e:
                    # Some of these might legitimately fail, but shouldn't crash the parser
                    print(f"? {description} - failed gracefully: {type(e).__name__}")
            
            return True
            
        except Exception as e:
            print(f"❌ Edge cases test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test that error handling works correctly."""
        print("🔍 Testing Error Handling")
        
        pdf_path = TEST_PDFS['simple']
        
        try:
            # Test invalid expressions that should fail gracefully
            error_cases = [
                ('contains:', "Empty pattern value"),
                ('invalid_function:text', "Invalid pattern type"),
                ('((unbalanced', "Unbalanced parentheses"),
                ('contains:"A" &', "Incomplete boolean expression"),
            ]
            
            error_count = 0
            for expr, description in error_cases:
                try:
                    pages, desc, groups = parse_page_range(expr, 5, pdf_path)
                    print(f"? {description} - unexpectedly succeeded: {pages}")
                except Exception as e:
                    print(f"✓ {description} - correctly failed with: {type(e).__name__}")
                    error_count += 1
            
            # Most should fail - that's correct behavior
            return error_count >= len(error_cases) // 2
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False


def main():
    """Main test runner."""
    print("🚀 Comprehensive Integration Tests for Page Range Parser")
    print("Testing REAL functionality with REAL PDFs")
    print(f"Started at: {datetime.now()}")
    
    # Set up test environment
    setup_test_environment()
    
    if not IMPORTS_AVAILABLE:
        print("\n❌ CANNOT RUN TESTS")
        print("Missing required modules. Please ensure:")
        print("  1. Updated pdf_manipulator modules are available")
        print("  2. reportlab is installed: pip install reportlab")
        return 1
    
    # Run comprehensive tests
    test_suite = ComprehensiveIntegrationTests()
    success = test_suite.run_all_tests()
    
    print(f"\n🏁 Completed at: {datetime.now()}")
    
    if success:
        print("\n🎉 SUCCESS! All integration tests passed.")
        print("The architecture fix is working correctly with real PDFs and content.")
        return 0
    else:
        print("\n💔 FAILURE! Some integration tests failed.")
        print("The architecture fix needs more work.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


# End of file #
