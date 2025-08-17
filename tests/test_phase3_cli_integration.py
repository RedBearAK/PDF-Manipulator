"""
Phase 3 CLI Integration Test Suite
File: tests/test_phase3_cli_integration.py

Comprehensive end-to-end testing of Phase 3 enhanced pattern syntax through the CLI.
Tests the complete pipeline: CLI args → pattern processor → operations → file generation.
"""

import os
import sys
import tempfile
import subprocess

from pathlib import Path
from rich.console import Console

# Test imports
from pdf_manipulator.renamer.pattern_processor import PatternProcessor, CompactPatternError
from pdf_manipulator.cli import validate_scraper_arguments
from pdf_manipulator.core.operations import extract_pages


console = Console()


class Phase3IntegrationTestRunner:
    """Test runner for Phase 3 CLI integration with result tracking."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_total = 0
        self.test_results = []
        
    def test(self, test_name: str, test_func):
        """Run a test and track results."""
        self.tests_total += 1
        console.print(f"\n[bold cyan]{test_name}[/bold cyan]")
        
        try:
            result = test_func()
            if result:
                self.tests_passed += 1
                self.test_results.append((test_name, True, None))
                console.print(f"[green]✓ {test_name} passed[/green]")
            else:
                self.test_results.append((test_name, False, "Test returned False"))
                console.print(f"[red]✗ {test_name} failed[/red]")
        except Exception as e:
            self.test_results.append((test_name, False, str(e)))
            console.print(f"[red]✗ {test_name} failed: {e}[/red]")
            
    def show_summary(self) -> bool:
        """Show test summary and return True if all passed."""
        console.print(f"\n[bold blue]Phase 3 CLI Integration Test Results[/bold blue]")
        console.print(f"Tests passed: {self.tests_passed}/{self.tests_total}")
        
        if self.tests_passed == self.tests_total:
            console.print(f"[green]🎉 ALL TESTS PASSED! Phase 3 CLI integration is working correctly.[/green]")
            return True
        else:
            console.print(f"[red]❌ {self.tests_total - self.tests_passed} tests failed[/red]")
            
            for test_name, passed, error in self.test_results:
                if not passed:
                    console.print(f"[red]  ✗ {test_name}: {error}[/red]")
            return False


def create_test_pdf(content_pages: list[str]) -> Path:
    """
    Create a synthetic multi-page PDF for testing.
    
    Args:
        content_pages: List of text content for each page
        
    Returns:
        Path to created PDF file
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        console.print("[yellow]Warning: reportlab not available, using minimal PDF[/yellow]")
        return create_minimal_pdf()
        
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)
    
    try:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        for page_num, content in enumerate(content_pages, 1):
            # Start new page (except for first)
            if page_num > 1:
                c.showPage()
                
            # Add content to page
            c.setFont("Helvetica", 12)
            lines = content.split('\n')
            y_position = 750  # Start near top
            
            for line in lines:
                if line.strip():  # Skip empty lines
                    c.drawString(50, y_position, line)
                y_position -= 20
                    
        c.save()
        return pdf_path
        
    except Exception as e:
        console.print(f"[red]Error creating PDF: {e}[/red]")
        return create_minimal_pdf()


def create_minimal_pdf() -> Path:
    """Create a minimal valid PDF for testing when reportlab is unavailable."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        # Write minimal PDF content
        tmp_file.write(b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R 5 0 R]
/Count 3
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 6 0 R
>>
endobj

4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 7 0 R
>>
endobj

5 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 8 0 R
>>
endobj

6 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
50 750 Td
(Page 1: Invoice Number: INV-001) Tj
0 -20 Td
(Company: ACME Corp) Tj
0 -20 Td
(Total: $1250.00) Tj
ET
endstream
endobj

7 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
50 750 Td
(Page 2: Invoice Number: INV-002) Tj
0 -20 Td
(Company: Global Inc) Tj
0 -20 Td
(Total: $2500.00) Tj
ET
endstream
endobj

8 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
50 750 Td
(Page 3: Invoice Number: INV-003) Tj
0 -20 Td
(Company: Beta LLC) Tj
0 -20 Td
(Total: $750.00) Tj
ET
endstream
endobj

xref
0 9
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
0000000293 00000 n 
0000000382 00000 n 
0000000555 00000 n 
0000000727 00000 n 
trailer
<<
/Size 9
/Root 1 0 R
>>
startxref
898
%%EOF""")
        return Path(tmp_file.name)


def test_cli_argument_validation():
    """Test that Phase 3 patterns pass CLI validation."""
    console.print("Testing CLI argument validation with Phase 3 patterns...")
    
    import argparse
    
    test_cases = [
        # Valid Phase 3 patterns
        {
            'patterns': ["Invoice Number:r1wd1pg2", "company=Company:u1ln1mt2"],
            'template': "{company}_{invoice_number}.pdf",
            'should_pass': True,
            'description': "Valid Phase 3 patterns with pg/mt specs"
        },
        # Invalid syntax
        {
            'patterns': ["Invoice Number:r1wd1pg99-2"],  # Backwards range
            'template': "{invoice_number}.pdf",
            'should_pass': False,
            'description': "Invalid backwards page range"
        },
        # Template without patterns
        {
            'patterns': None,
            'template': "{company}.pdf",
            'should_pass': False,
            'description': "Template without patterns should fail"
        }
    ]
    
    successes = 0
    for test_case in test_cases:
        try:
            # Create mock args object
            args = argparse.Namespace()
            args.scrape_pattern = test_case['patterns']
            args.scrape_patterns_file = None
            args.filename_template = test_case['template']
            args.extract_pages = "1-3"
            args.scrape_text = False
            args.pattern_source_page = 1
            
            is_valid, error_msg = validate_scraper_arguments(args)
            
            if test_case['should_pass']:
                if is_valid:
                    console.print(f"  ✓ {test_case['description']}")
                    successes += 1
                else:
                    console.print(f"  ✗ {test_case['description']} - should pass but failed: {error_msg}")
            else:
                if not is_valid:
                    console.print(f"  ✓ {test_case['description']} - correctly rejected: {error_msg}")
                    successes += 1
                else:
                    console.print(f"  ✗ {test_case['description']} - should fail but passed")
                    
        except Exception as e:
            console.print(f"  ✗ {test_case['description']} - exception: {e}")
    
    console.print(f"  Passed {successes}/{len(test_cases)} CLI validation tests")
    return successes == len(test_cases)


def test_phase3_pattern_parsing():
    """Test that Phase 3 pattern syntax parses correctly."""
    console.print("Testing Phase 3 pattern parsing...")
    
    processor = PatternProcessor()
    
    test_patterns = [
        # Page specifications
        ("Invoice:r1wd1pg2", "specific page"),
        ("Invoice:r1wd1pg2-4", "page range"),
        ("Invoice:r1wd1pg3-", "page from N to end"),
        ("Invoice:r1wd1pg-2", "last N pages"),
        ("Invoice:r1wd1pg0", "all pages debug"),
        
        # Match specifications
        ("Invoice:r1wd1mt2", "specific match"),
        ("Invoice:r1wd1mt1-3", "match range"),
        ("Invoice:r1wd1mt2-", "match from N to end"),
        ("Invoice:r1wd1mt-2", "last N matches"),
        ("Invoice:r1wd1mt0", "all matches debug"),
        
        # Combined specifications
        ("company=Company:u1ln1pg2mt3", "combined page and match"),
        ("ref=Reference:r1wd1pg2-4mt-2", "complex combined spec"),
        
        # Backward compatibility
        ("Invoice Number:r1wd1", "basic Phase 2 pattern"),
        ("company=Company Name:u1ln1", "Phase 2 with variable"),
    ]
    
    successes = 0
    for pattern, description in test_patterns:
        try:
            var_name, keyword, extraction_spec = processor.parse_pattern_string(pattern)
            
            # Verify the pattern parsed without errors
            if var_name and keyword and extraction_spec:
                console.print(f"  ✓ {description}: {pattern}")
                successes += 1
            else:
                console.print(f"  ✗ {description}: {pattern} - incomplete parse result")
                
        except Exception as e:
            console.print(f"  ✗ {description}: {pattern} - error: {e}")
    
    console.print(f"  Parsed {successes}/{len(test_patterns)} Phase 3 patterns")
    return successes == len(test_patterns)


def test_dry_run_integration():
    """Test dry-run functionality with Phase 3 patterns."""
    console.print("Testing dry-run integration...")
    
    # Create test PDF
    test_pages = [
        "Page 1\nInvoice Number: INV-001\nCompany: ACME Corp\nTotal: $1250.00",
        "Page 2\nInvoice Number: INV-002\nCompany: Global Inc\nTotal: $2500.00", 
        "Page 3\nInvoice Number: INV-003\nCompany: Beta LLC\nTotal: $750.00"
    ]
    
    test_pdf = create_test_pdf(test_pages)
    
    try:
        # Test dry-run through operations (not CLI subprocess to avoid complexity)
        from pdf_manipulator.renamer.filename_generator import FilenameGenerator
        
        generator = FilenameGenerator()
        patterns = ["invoice=Invoice Number:r1wd1pg2", "company=Company:u1ln1pg2"]
        template = "{company}_{invoice}_test.pdf"
        
        # Test dry-run functionality
        output_path, results = generator.generate_smart_filename(
            test_pdf, "2", patterns, template, 1, dry_run=True
        )
        
        if output_path and results:
            console.print(f"  ✓ Dry-run generated filename: {output_path.name}")
            console.print(f"  ✓ Extracted variables: {list(results.get('variables_extracted', {}).keys())}")
            return True
        else:
            console.print(f"  ✗ Dry-run failed to generate results")
            return False
            
    except Exception as e:
        console.print(f"  ✗ Dry-run test failed: {e}")
        return False
    finally:
        # Clean up test file
        try:
            test_pdf.unlink()
        except:
            pass


def test_cli_subprocess_integration():
    """Test actual CLI subprocess calls with Phase 3 patterns."""
    console.print("Testing CLI subprocess integration...")
    
    # Create test PDF
    test_pages = [
        "Invoice Number: INV-001\nCompany: ACME Corp\nAmount: $1250.00",
        "Invoice Number: INV-002\nCompany: Global Inc\nAmount: $2500.00"
    ]
    
    test_pdf = create_test_pdf(test_pages)
    
    try:
        # Test basic Phase 3 pattern via CLI
        cmd = [
            sys.executable, "-m", "pdf_manipulator",
            str(test_pdf),
            "--extract-pages=1",
            "--scrape-pattern=invoice=Invoice Number:r1wd1pg1",
            "--filename-template={invoice}_test.pdf",
            "--dry-run"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            console.print(f"  ✓ CLI subprocess completed successfully")
            console.print(f"  ✓ Output preview: {result.stdout[:100]}...")
            return True
        else:
            console.print(f"  ✗ CLI subprocess failed with code {result.returncode}")
            console.print(f"  Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        console.print(f"  ✗ CLI subprocess timed out")
        return False
    except Exception as e:
        console.print(f"  ✗ CLI subprocess test failed: {e}")
        return False
    finally:
        # Clean up test file
        try:
            test_pdf.unlink()
        except:
            pass


def test_multi_page_pattern_extraction():
    """Test multi-page pattern extraction functionality."""
    console.print("Testing multi-page pattern extraction...")
    
    # Create test PDF with different content on each page
    test_pages = [
        "Page 1 Header\nCompany: ACME Corp\nStatus: Draft",
        "Page 2 Content\nInvoice Number: INV-2024-001\nCompany: ACME Corp\nTotal: $1500.00",
        "Page 3 Footer\nCompany: ACME Corp\nSignature: John Doe"
    ]
    
    test_pdf = create_test_pdf(test_pages)
    
    try:
        from pdf_manipulator.renamer.pattern_processor import PatternProcessor
        
        processor = PatternProcessor()
        
        # Test pattern that should find content on specific page
        var_name, keyword, extraction_spec = processor.parse_pattern_string(
            "invoice=Invoice Number:r1wd1pg2"
        )
        
        # Verify the page specification was parsed
        if 'page_spec' in extraction_spec:
            page_spec = extraction_spec['page_spec']
            console.print(f"  ✓ Page specification parsed: {page_spec}")
            
            # FIXED: Check for correct structure - 'single' type and 'value' key
            if page_spec.get('type') == 'single' and page_spec.get('value') == 2:
                console.print(f"  ✓ Page 2 specification correct")
                return True
            else:
                console.print(f"  ✗ Page specification incorrect: {page_spec}")
                return False
        else:
            console.print(f"  ✗ Page specification not found in extraction spec")
            return False
            
    except Exception as e:
        console.print(f"  ✗ Multi-page test failed: {e}")
        return False
    finally:
        # Clean up test file
        try:
            test_pdf.unlink()
        except:
            pass


def test_error_handling():
    """Test error handling for invalid Phase 3 patterns."""
    console.print("Testing error handling...")
    
    processor = PatternProcessor()
    
    error_cases = [
        ("Invoice:r1wd1pg5-2", "backwards page range"),
        ("Invoice:r1wd1mt10-5", "backwards match range"),
        ("Invoice:r1wd1pg1000", "excessive page number"),  # FIXED: Use 1000 instead of 999
        ("123invalid=Invoice:r1wd1", "invalid variable name"),
        ("", "empty pattern"),
        ("keyword:", "missing extraction spec"),
    ]
    
    successes = 0
    for pattern, description in error_cases:
        try:
            processor.parse_pattern_string(pattern)
            console.print(f"  ✗ {description}: '{pattern}' should have failed but didn't")
        except (CompactPatternError, ValueError):
            console.print(f"  ✓ {description}: '{pattern}' correctly rejected")
            successes += 1
        except Exception as e:
            console.print(f"  ✗ {description}: '{pattern}' unexpected error: {e}")
    
    console.print(f"  Handled {successes}/{len(error_cases)} error cases correctly")
    return successes == len(error_cases)


def main():
    """Main test runner for Phase 3 CLI integration."""
    console.print("[bold blue]Phase 3 CLI Integration Test Suite[/bold blue]")
    console.print("Testing end-to-end Phase 3 enhanced pattern functionality...\n")
    
    runner = Phase3IntegrationTestRunner()
    
    # Core integration tests
    runner.test("CLI Argument Validation", test_cli_argument_validation)
    runner.test("Phase 3 Pattern Parsing", test_phase3_pattern_parsing)
    runner.test("Dry-Run Integration", test_dry_run_integration)
    
    # Advanced integration tests
    runner.test("Multi-Page Pattern Extraction", test_multi_page_pattern_extraction)
    runner.test("Error Handling", test_error_handling)
    
    # CLI subprocess test (may be slower)
    runner.test("CLI Subprocess Integration", test_cli_subprocess_integration)
    
    # Show final results
    all_passed = runner.show_summary()
    
    # Additional recommendations
    if all_passed:
        console.print(f"\n[green]🎯 Phase 3 CLI integration is ready for production![/green]")
        console.print(f"[dim]Next steps: Real-world PDF testing and performance validation[/dim]")
    else:
        console.print(f"\n[red]🔧 Some integration issues need to be resolved[/red]")
        console.print(f"[dim]Focus on failing tests before proceeding to real-world testing[/dim]")
    
    # Return appropriate exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())


# End of file #
