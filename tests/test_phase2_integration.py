"""
Comprehensive test suite for Phase 2 integration components.
File: test_phase2_integration.py

Tests all enhanced components working together:
- Enhanced PatternExtractor with chained movements and zero-count extraction
- Updated PatternProcessor using enhanced features
- Operations integration with smart filename generation
- End-to-end pattern extraction and template substitution
"""

import tempfile

from pathlib import Path
from rich.console import Console

# Test imports - these would be the actual enhanced modules
from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor
from pdf_manipulator.renamer.pattern_processor import PatternProcessor
from pdf_manipulator.renamer.template_engine import TemplateEngine
from pdf_manipulator.renamer.filename_generator import FilenameGenerator


console = Console()


def test_enhanced_pattern_extractor():
    """Test enhanced PatternExtractor with new features."""
    console.print("\n[cyan]Testing Enhanced PatternExtractor...[/cyan]")
    
    extractor = PatternExtractor()
    
    # Test text for pattern extraction
    test_text = """Company: ACME Corporation
Invoice Number: INV-2024-001
Date: March 15, 2024

Description: Software License
Amount: $1,250.00
Tax: $125.00
Total: $1,375.00

Thank you for your business!
"""
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Basic single movement (backward compatibility)
    total_tests += 1
    try:
        pattern = {
            'keyword': 'Invoice Number:',
            'direction': 'right',
            'distance': 1,
            'extract_type': 'word'
        }
        result = extractor.extract_pattern(test_text, pattern)
        expected = "INV-2024-001"
        if result == expected:
            console.print(f"[green]✓ Basic movement: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Basic movement: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Basic movement failed: {e}[/red]")
    
    # Test 2: Enhanced format with single movement
    total_tests += 1
    try:
        pattern = {
            'keyword': 'Amount:',
            'movements': [('r', 1)],
            'extract_type': 'nb',
            'extract_count': 1,
            'flexible': False
        }
        result = extractor.extract_pattern(test_text, pattern)
        if result and '1250' in result:  # Should extract the number part
            console.print(f"[green]✓ Enhanced single movement: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Enhanced single movement: got '{result}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Enhanced single movement failed: {e}[/red]")
    
    # Test 3: Chained movements
    total_tests += 1
    try:
        pattern = {
            'keyword': 'Invoice Number:',
            'movements': [('d', 2), ('r', 1)],  # Down 2 lines, right 1 word
            'extract_type': 'wd',
            'extract_count': 1,
            'flexible': False
        }
        result = extractor.extract_pattern(test_text, pattern)
        expected = "Software"  # Should land on "Description: Software License"
        if result == expected:
            console.print(f"[green]✓ Chained movements: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Chained movements: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Chained movements failed: {e}[/red]")
    
    # Test 4: Zero-count extraction (until end)
    total_tests += 1
    try:
        pattern = {
            'keyword': 'Description:',
            'movements': [('r', 1)],
            'extract_type': 'wd',
            'extract_count': 0,  # Until end of line
            'flexible': False
        }
        result = extractor.extract_pattern(test_text, pattern)
        expected = "Software License"
        if result == expected:
            console.print(f"[green]✓ Zero-count extraction: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Zero-count extraction: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Zero-count extraction failed: {e}[/red]")
    
    # Test 5: Flexible extraction mode
    total_tests += 1
    try:
        pattern = {
            'keyword': 'Total:',
            'movements': [('r', 1)],
            'extract_type': 'nb',
            'extract_count': 1,
            'flexible': True  # Should handle $ and commas gracefully
        }
        result = extractor.extract_pattern(test_text, pattern)
        if result and '1375' in result:
            console.print(f"[green]✓ Flexible extraction: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Flexible extraction: got '{result}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Flexible extraction failed: {e}[/red]")
    
    # Test 6: Zero movements (extract at keyword location)
    total_tests += 1
    try:
        pattern = {
            'keyword': 'ACME',
            'movements': [],  # No movements
            'extract_type': 'wd',
            'extract_count': 1,
            'flexible': False
        }
        result = extractor.extract_pattern(test_text, pattern)
        expected = "Corporation"  # Should get word after ACME
        if result == expected:
            console.print(f"[green]✓ Zero movements: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Zero movements: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Zero movements failed: {e}[/red]")
    
    console.print(f"[cyan]Enhanced PatternExtractor: {success_count}/{total_tests} tests passed[/cyan]")
    return success_count == total_tests


def test_updated_pattern_processor():
    """Test updated PatternProcessor with enhanced features."""
    console.print("\n[cyan]Testing Updated PatternProcessor...[/cyan]")
    
    processor = PatternProcessor()
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Compact pattern parsing with chained movements
    total_tests += 1
    try:
        var_name, keyword, spec = processor.parse_pattern_string("invoice=Invoice Number:d1r2wd1")
        expected_spec = {
            'movements': [('d', 1), ('r', 2)],
            'extract_type': 'wd',
            'extract_count': 1,
            'flexible': False
        }
        
        if (var_name == "invoice" and keyword == "Invoice Number" and 
            spec['movements'] == expected_spec['movements'] and
            spec['extract_type'] == expected_spec['extract_type']):
            console.print(f"[green]✓ Chained movement parsing: {spec['movements']}[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Chained movement parsing failed[/red]")
    except Exception as e:
        console.print(f"[red]✗ Chained movement parsing failed: {e}[/red]")
    
    # Test 2: Zero-count extraction parsing
    total_tests += 1
    try:
        var_name, keyword, spec = processor.parse_pattern_string("description=Description:r1wd0-")
        
        if (spec['extract_count'] == 0 and spec['flexible'] == True and
            spec['extract_type'] == 'wd'):
            console.print(f"[green]✓ Zero-count flexible parsing: count={spec['extract_count']}, flexible={spec['flexible']}[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Zero-count flexible parsing failed[/red]")
    except Exception as e:
        console.print(f"[red]✗ Zero-count flexible parsing failed: {e}[/red]")
    
    # Test 3: Enhanced pattern conversion
    total_tests += 1
    try:
        var_name, keyword, spec = processor.parse_pattern_string("total=Total:u1r1nb1-")
        enhanced_pattern = processor.convert_to_enhanced_pattern(keyword, spec)
        
        expected_pattern = {
            'keyword': 'Total',
            'movements': [('u', 1), ('r', 1)],
            'extract_type': 'nb',
            'extract_count': 1,
            'flexible': True
        }
        
        if enhanced_pattern == expected_pattern:
            console.print(f"[green]✓ Enhanced pattern conversion[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Enhanced pattern conversion failed[/red]")
    except Exception as e:
        console.print(f"[red]✗ Enhanced pattern conversion failed: {e}[/red]")
    
    # Test 4: Pattern list validation
    total_tests += 1
    try:
        patterns = [
            "invoice=Invoice Number:r1wd1",
            "company=Company:u1ln1",
            "total=Total:d3nb1-"
        ]
        parsed_patterns = processor.validate_pattern_list(patterns)
        
        if len(parsed_patterns) == 3:
            console.print(f"[green]✓ Pattern list validation: {len(parsed_patterns)} patterns[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Pattern list validation failed[/red]")
    except Exception as e:
        console.print(f"[red]✗ Pattern list validation failed: {e}[/red]")
    
    # Test 5: Constraint validation (should fail)
    total_tests += 1
    try:
        # This should fail - conflicting directions
        processor.parse_pattern_string("bad=Test:u1d1wd1")
        console.print(f"[red]✗ Constraint validation failed to catch error[/red]")
    except Exception as e:
        console.print(f"[green]✓ Constraint validation caught error: {e}[/green]")
        success_count += 1
    
    console.print(f"[cyan]Updated PatternProcessor: {success_count}/{total_tests} tests passed[/cyan]")
    return success_count == total_tests


def test_template_engine_integration():
    """Test template engine with enhanced variables."""
    console.print("\n[cyan]Testing Template Engine Integration...[/cyan]")
    
    engine = TemplateEngine()
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Basic template substitution
    total_tests += 1
    try:
        template = "{company}_{invoice}_{amount}.pdf"
        variables = {
            'company': 'ACME-Corp',
            'invoice': 'INV-2024-001',
            'amount': '1250-00'
        }
        
        result = engine.substitute_variables(template, variables)
        expected = "ACME-Corp_INV-2024-001_1250-00.pdf"
        
        if result == expected:
            console.print(f"[green]✓ Basic substitution: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Basic substitution: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Basic substitution failed: {e}[/red]")
    
    # Test 2: Fallback handling
    total_tests += 1
    try:
        template = "{company}_{missing|NO-DATA}_{invoice}.pdf"
        variables = {
            'company': 'ACME-Corp',
            'invoice': 'INV-001'
        }
        
        result = engine.substitute_variables(template, variables)
        expected = "ACME-Corp_NO-DATA_INV-001.pdf"
        
        if result == expected:
            console.print(f"[green]✓ Fallback handling: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Fallback handling: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Fallback handling failed: {e}[/red]")
    
    # Test 3: Built-in variables
    total_tests += 1
    try:
        template = "{company}_{invoice}_pages{range}.pdf"
        variables = {'company': 'ACME', 'invoice': 'INV-001'}
        built_ins = {'range': '01-03'}
        
        result = engine.substitute_variables(template, variables, built_ins)
        expected = "ACME_INV-001_pages01-03.pdf"
        
        if result == expected:
            console.print(f"[green]✓ Built-in variables: '{result}'[/green]")
            success_count += 1
        else:
            console.print(f"[red]✗ Built-in variables: got '{result}', expected '{expected}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Built-in variables failed: {e}[/red]")
    
    console.print(f"[cyan]Template Engine Integration: {success_count}/{total_tests} tests passed[/cyan]")
    return success_count == total_tests


def test_filename_generator_integration():
    """Test FilenameGenerator with full integration."""
    console.print("\n[cyan]Testing FilenameGenerator Integration...[/cyan]")
    
    generator = FilenameGenerator()
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Smart filename generation with simulated extraction
    total_tests += 1
    try:
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            patterns = [
                "invoice=Invoice Number:r1wd1",
                "company=Company:u1ln1"
            ]
            template = "{company}_{invoice}_pages{range}.pdf"
            
            # Use dry-run mode to simulate extraction
            output_path, results = generator.generate_smart_filename(
                tmp_path, "01-03", patterns, template, 1, dry_run=True
            )
            
            if results.get('variables_extracted') and not results.get('fallback_used'):
                console.print(f"[green]✓ Smart filename generation: {output_path.name}[/green]")
                success_count += 1
            else:
                console.print(f"[red]✗ Smart filename generation failed[/red]")
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        console.print(f"[red]✗ Smart filename generation failed: {e}[/red]")
    
    # Test 2: Fallback to simple naming
    total_tests += 1
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            # No patterns or template - should fallback
            output_path, results = generator.generate_smart_filename(
                tmp_path, "01-03", None, None, 1, dry_run=True
            )
            
            if results.get('fallback_used') and 'pages01-03' in output_path.name:
                console.print(f"[green]✓ Fallback to simple naming: {output_path.name}[/green]")
                success_count += 1
            else:
                console.print(f"[red]✗ Fallback to simple naming failed[/red]")
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        console.print(f"[red]✗ Fallback to simple naming failed: {e}[/red]")
    
    # Test 3: Preview functionality
    total_tests += 1
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            patterns = ["invoice=Invoice:r1wd1"]
            template = "{invoice}_test.pdf"
            
            preview = generator.preview_filename_generation(
                tmp_path, "01", patterns, template, 1
            )
            
            if ('extraction_preview' in preview and 
                'filename_preview' in preview and
                'invoice' in preview['extraction_preview']):
                console.print(f"[green]✓ Preview functionality: {preview['filename_preview']}[/green]")
                success_count += 1
            else:
                console.print(f"[red]✗ Preview functionality failed[/red]")
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        console.print(f"[red]✗ Preview functionality failed: {e}[/red]")
    
    console.print(f"[cyan]FilenameGenerator Integration: {success_count}/{total_tests} tests passed[/cyan]")
    return success_count == total_tests


def test_end_to_end_workflow():
    """Test complete end-to-end workflow simulation."""
    console.print("\n[cyan]Testing End-to-End Workflow...[/cyan]")
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Complete pattern processing workflow
    total_tests += 1
    try:
        # Step 1: Parse patterns
        processor = PatternProcessor()
        patterns = [
            "invoice=Invoice Number:r1wd1",
            "total=Total:r1nb1-"
        ]
        parsed_patterns = processor.validate_pattern_list(patterns)
        
        # Step 2: Convert to enhanced format
        enhanced_patterns = []
        for var_name, keyword, spec in parsed_patterns:
            enhanced_pattern = processor.convert_to_enhanced_pattern(keyword, spec)
            enhanced_patterns.append((var_name, enhanced_pattern))
        
        # Step 3: Generate template
        template = "{invoice}_{total}_extracted.pdf"
        engine = TemplateEngine()
        template_vars = engine.get_required_variables(template)
        
        # Step 4: Validate workflow consistency
        pattern_vars = {var_name for var_name, _ in enhanced_patterns}
        
        if template_vars.issubset(pattern_vars):
            console.print(f"[green]✓ End-to-end workflow: variables consistent[/green]")
            success_count += 1
        else:
            missing = template_vars - pattern_vars
            console.print(f"[red]✗ End-to-end workflow: missing variables {missing}[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ End-to-end workflow failed: {e}[/red]")
    
    # Test 2: Error handling in workflow
    total_tests += 1
    try:
        # Test with invalid pattern - should handle gracefully
        processor = PatternProcessor()
        try:
            processor.parse_pattern_string("invalid:pattern:syntax")
            console.print(f"[red]✗ Error handling failed to catch invalid pattern[/red]")
        except Exception:
            console.print(f"[green]✓ Error handling caught invalid pattern[/green]")
            success_count += 1
            
    except Exception as e:
        console.print(f"[red]✗ Error handling test failed: {e}[/red]")
    
    console.print(f"[cyan]End-to-End Workflow: {success_count}/{total_tests} tests passed[/cyan]")
    return success_count == total_tests


def run_all_tests():
    """Run all Phase 2 integration tests."""
    console.print("[bold blue]Phase 2 Integration Test Suite[/bold blue]")
    console.print("=" * 60)
    
    test_results = []
    
    # Run individual test suites
    test_results.append(test_enhanced_pattern_extractor())
    test_results.append(test_updated_pattern_processor())
    test_results.append(test_template_engine_integration())
    test_results.append(test_filename_generator_integration())
    test_results.append(test_end_to_end_workflow())
    
    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    console.print("\n" + "=" * 60)
    if passed_tests == total_tests:
        console.print(f"[bold green]🎉 ALL TESTS PASSED: {passed_tests}/{total_tests}[/bold green]")
        console.print("[green]Phase 2 integration is ready for production![/green]")
        return True
    else:
        console.print(f"[bold red]❌ TESTS FAILED: {passed_tests}/{total_tests} passed[/bold red]")
        console.print("[red]Phase 2 integration needs more work[/red]")
        return False


def main():
    """Main test runner."""
    success = run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())


# End of file #
