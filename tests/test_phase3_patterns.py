"""
Phase 3 Enhanced Pattern Extraction Test Module
File: test_phase3_patterns.py

Tests for multi-page and multi-match pattern extraction functionality.
Runnable with pytest but designed as standalone test module.
"""

import tempfile

from pathlib import Path
from rich.console import Console

from pdf_manipulator.renamer.pattern_processor import PatternProcessor, CompactPatternError
from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor
from pdf_manipulator.renamer.filename_generator import FilenameGenerator


console = Console()


class Phase3TestRunner:
    """Test runner for Phase 3 pattern extraction functionality."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []
    
    def test(self, test_name: str, test_func):
        """Run a single test and track results."""
        console.print(f"\n[cyan]Testing: {test_name}[/cyan]")
        
        try:
            result = test_func()
            if result:
                console.print(f"[green]✓ PASS: {test_name}[/green]")
                self.passed += 1
                self.test_results.append((test_name, True, None))
            else:
                console.print(f"[red]✗ FAIL: {test_name}[/red]")
                self.failed += 1
                self.test_results.append((test_name, False, "Test returned False"))
        except Exception as e:
            console.print(f"[red]✗ ERROR: {test_name} - {e}[/red]")
            self.failed += 1
            self.test_results.append((test_name, False, str(e)))
    
    def show_summary(self):
        """Show final test summary."""
        total = self.passed + self.failed
        console.print(f"\n{'='*60}")
        console.print(f"[bold]PHASE 3 TEST SUMMARY[/bold]")
        console.print(f"{'='*60}")
        console.print(f"Tests run: {total}")
        console.print(f"[green]Passed: {self.passed}[/green]")
        console.print(f"[red]Failed: {self.failed}[/red]")
        
        if self.failed > 0:
            console.print(f"\n[red]FAILED TESTS:[/red]")
            for name, passed, error in self.test_results:
                if not passed:
                    console.print(f"  - {name}: {error}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        console.print(f"\nSuccess rate: {success_rate:.1f}%")
        
        return self.failed == 0


def test_pattern_syntax_parsing():
    """Test Phase 3 enhanced syntax parsing."""
    processor = PatternProcessor()
    
    # Test cases: (pattern, should_succeed, expected_features)
    test_cases = [
        # Basic patterns (should still work)
        ("Invoice Number:r1wd1", True, {"basic": True}),
        ("company=Company Name:u1ln1", True, {"basic": True, "variable": True}),
        
        # Page specifications
        ("Invoice:r1wd1pg2", True, {"page_single": True}),
        ("Invoice:r1wd1pg2-4", True, {"page_range": True}),
        ("Invoice:r1wd1pg3-", True, {"page_from": True}),
        ("Invoice:r1wd1pg-2", True, {"page_last": True}),
        ("Invoice:r1wd1pg0", True, {"page_all": True}),
        
        # Match specifications
        ("Invoice:r1wd1mt2", True, {"match_single": True}),
        ("Invoice:r1wd1mt1-3", True, {"match_range": True}),
        ("Invoice:r1wd1mt2-", True, {"match_from": True}),
        ("Invoice:r1wd1mt-2", True, {"match_last": True}),
        ("Invoice:r1wd1mt0", True, {"match_all": True}),
        
        # Combined specifications
        ("Invoice:r1wd1pg2-4mt3", True, {"combined": True}),
        ("ref=Reference:u1r2wd2-pg1mt2", True, {"complex": True}),
        
        # Invalid patterns
        ("Invoice:r1wd1pg", False, {"invalid": True}),
        ("Invoice:r1wd1mt", False, {"invalid": True}),
        ("Invoice:r1wd1pg2-1", False, {"backwards_range": True}),
        ("Invoice:u1d2wd1", False, {"conflicting_movements": True}),  # up and down conflict
        ("Invoice:l1r2wd1", False, {"conflicting_movements": True}),  # left and right conflict
        ("Invalid syntax", False, {"malformed": True}),
    ]
    
    successes = 0
    failures = []
    
    for pattern, should_succeed, features in test_cases:
        try:
            var_name, keyword, extraction_spec = processor.parse_pattern_string(pattern)
            
            if should_succeed:
                # Validate expected features
                if features.get("page_single"):
                    if extraction_spec.get('page_spec', {}).get('type') != 'single':
                        failures.append(f"Pattern '{pattern}' should have single page spec")
                        continue
                
                if features.get("page_range"):
                    if extraction_spec.get('page_spec', {}).get('type') != 'range':
                        failures.append(f"Pattern '{pattern}' should have range page spec")
                        continue
                
                if features.get("match_single"):
                    if extraction_spec.get('match_spec', {}).get('type') != 'single':
                        failures.append(f"Pattern '{pattern}' should have single match spec")
                        continue
                
                console.print(f"  ✓ Parsed: {pattern}")
                successes += 1
            else:
                failures.append(f"Pattern '{pattern}' should have failed but didn't")
                
        except CompactPatternError:
            if should_succeed:
                failures.append(f"Pattern '{pattern}' should have succeeded but failed")
            else:
                console.print(f"  ✓ Correctly rejected: {pattern}")
                successes += 1
        except Exception as e:
            failures.append(f"Unexpected error parsing '{pattern}': {e}")
    
    if failures:
        for failure in failures:
            console.print(f"  [red]✗ {failure}[/red]")
    
    console.print(f"  Parsed {successes}/{len(test_cases)} patterns correctly")
    return len(failures) == 0


def test_range_specification_parsing():
    """Test page and match range specification parsing."""
    processor = PatternProcessor()
    
    # Test range parsing
    test_cases = [
        # (range_string, expected_type, expected_values)
        ("2", "single", {"value": 2}),
        ("2-4", "range", {"start": 2, "end": 4}),
        ("3-", "from", {"start": 3}),
        ("-2", "last", {"count": 2}),
        ("0", "all", {}),
    ]
    
    successes = 0
    for range_str, expected_type, expected_values in test_cases:
        try:
            result = processor._parse_range_spec(range_str, "test")
            
            if result["type"] != expected_type:
                console.print(f"  [red]✗ Range '{range_str}' got type '{result['type']}', expected '{expected_type}'[/red]")
                continue
            
            # Check specific values
            valid = True
            for key, expected_value in expected_values.items():
                if result.get(key) != expected_value:
                    console.print(f"  [red]✗ Range '{range_str}' got {key}={result.get(key)}, expected {expected_value}[/red]")
                    valid = False
                    break
            
            if valid:
                console.print(f"  ✓ Range '{range_str}' -> {result}")
                successes += 1
                
        except Exception as e:
            console.print(f"  [red]✗ Error parsing range '{range_str}': {e}[/red]")
    
    console.print(f"  Parsed {successes}/{len(test_cases)} ranges correctly")
    return successes == len(test_cases)


def test_pattern_validation():
    """Test pattern validation and error handling."""
    processor = PatternProcessor()
    
    # Test duplicate variable names
    patterns_with_duplicates = [
        "invoice=Invoice:r1wd1",
        "invoice=Total:r1nb1"  # Duplicate variable name
    ]
    
    try:
        processor.validate_pattern_list(patterns_with_duplicates)
        console.print(f"  [red]✗ Should have detected duplicate variable names[/red]")
        return False
    except CompactPatternError as e:
        if "duplicate" in str(e).lower():
            console.print(f"  ✓ Correctly detected duplicate variables: {e}")
        else:
            console.print(f"  [red]✗ Wrong error for duplicates: {e}[/red]")
            return False
    
    # Test valid pattern list
    valid_patterns = [
        "invoice=Invoice Number:r1wd1pg2",
        "company=Company Name:u1ln1mt2",
        "amount=Total Amount:r1nb1pg1-3"
    ]
    
    try:
        result = processor.validate_pattern_list(valid_patterns)
        if len(result) == 3:
            console.print(f"  ✓ Validated {len(result)} patterns successfully")
            return True
        else:
            console.print(f"  [red]✗ Expected 3 patterns, got {len(result)}[/red]")
            return False
    except Exception as e:
        console.print(f"  [red]✗ Error validating valid patterns: {e}[/red]")
        return False


def test_enhanced_pattern_examples():
    """Test the enhanced pattern examples."""
    processor = PatternProcessor()
    
    try:
        examples = processor.get_enhanced_pattern_examples()
        
        # Test that examples parse correctly
        successes = 0
        for category, example_info in examples.items():
            pattern = example_info['pattern']
            description = example_info['description']
            
            try:
                var_name, keyword, extraction_spec = processor.parse_pattern_string(pattern)
                console.print(f"  ✓ Example '{category}': {pattern}")
                successes += 1
            except Exception as e:
                console.print(f"  [red]✗ Example '{category}' failed: {e}[/red]")
        
        console.print(f"  Validated {successes}/{len(examples)} examples")
        return successes == len(examples)
        
    except Exception as e:
        console.print(f"  [red]✗ Error getting examples: {e}[/red]")
        return False


def test_filename_generation_integration():
    """Test integration with filename generation."""
    
    # Create a temporary test file (empty is fine for this test)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(b"%PDF-1.4\n%EOF\n")  # Minimal valid PDF
    
    try:
        generator = FilenameGenerator()
        
        # Test basic functionality without actual PDF processing
        patterns = ["invoice=Invoice Number:r1wd1pg2", "amount=Total:r1nb1"]
        template = "{invoice}_{amount}_pages{range}.pdf"
        
        # Test dry-run mode (should work even with minimal PDF)
        output_path, results = generator.generate_smart_filename(
            tmp_path, "01-03", patterns, template, 1, dry_run=True
        )
        
        if output_path and results:
            console.print(f"  ✓ Generated filename: {output_path.name}")
            console.print(f"  ✓ Got extraction results: {len(results.get('variables_extracted', {}))}")
            return True
        else:
            console.print(f"  [red]✗ Failed to generate filename or results[/red]")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error in filename generation: {e}[/red]")
        return False
    finally:
        # Clean up
        try:
            tmp_path.unlink()
        except:
            pass


def test_backward_compatibility():
    """Test that Phase 2 patterns still work."""
    processor = PatternProcessor()
    
    # Test Phase 2 patterns (without pg/mt specifications)
    phase2_patterns = [
        "Invoice Number:r1wd1",
        "company=Company Name:u1ln1",
        "Total Amount:r1nb1-",  # With flexible mode
        "Date:u2r3wd1",  # With chained movements
        "Description:wd0",  # Zero-count extraction
    ]
    
    successes = 0
    for pattern in phase2_patterns:
        try:
            var_name, keyword, extraction_spec = processor.parse_pattern_string(pattern)
            
            # Should not have page_spec or match_spec for Phase 2 patterns
            if 'page_spec' in extraction_spec or 'match_spec' in extraction_spec:
                console.print(f"  [red]✗ Phase 2 pattern '{pattern}' has Phase 3 specs[/red]")
                continue
            
            console.print(f"  ✓ Phase 2 pattern works: {pattern}")
            successes += 1
            
        except Exception as e:
            console.print(f"  [red]✗ Phase 2 pattern failed: {pattern} - {e}[/red]")
    
    console.print(f"  Validated {successes}/{len(phase2_patterns)} Phase 2 patterns")
    return successes == len(phase2_patterns)


def test_error_edge_cases():
    """Test edge cases and error conditions."""
    processor = PatternProcessor()
    
    # Edge cases that should be handled gracefully
    edge_cases = [
        # Empty/invalid inputs
        ("", False, "empty pattern"),
        (":", False, "missing keyword"),
        ("keyword:", False, "missing extraction spec"),
        
        # Invalid ranges
        ("Invoice:r1wd1pg5-2", False, "backwards page range"),
        ("Invoice:r1wd1mt10-5", False, "backwards match range"),
        
        # Very large numbers (should be rejected)
        ("Invoice:r1wd1pg9999", False, "excessive page number"),
        ("Invoice:r1wd1mt9999", False, "excessive match number"),
        
        # Invalid variable names
        ("123invalid=Invoice:r1wd1", False, "invalid variable name"),
        ("inv-alid=Invoice:r1wd1", False, "invalid variable name with dash"),
    ]
    
    successes = 0
    for pattern, should_succeed, description in edge_cases:
        try:
            result = processor.parse_pattern_string(pattern)
            
            if should_succeed:
                console.print(f"  ✓ Edge case handled: {description}")
                successes += 1
            else:
                console.print(f"  [red]✗ Should have failed: {description}[/red]")
        
        except (CompactPatternError, ValueError):
            if not should_succeed:
                console.print(f"  ✓ Correctly rejected: {description}")
                successes += 1
            else:
                console.print(f"  [red]✗ Should have succeeded: {description}[/red]")
        
        except Exception as e:
            console.print(f"  [red]✗ Unexpected error for '{description}': {e}[/red]")
    
    console.print(f"  Handled {successes}/{len(edge_cases)} edge cases correctly")
    return successes == len(edge_cases)


def main():
    """Main test runner."""
    console.print("[bold blue]Phase 3 Enhanced Pattern Extraction Tests[/bold blue]")
    console.print("Testing multi-page and multi-match functionality...\n")
    
    runner = Phase3TestRunner()
    
    # Core functionality tests
    runner.test("Pattern Syntax Parsing", test_pattern_syntax_parsing)
    runner.test("Range Specification Parsing", test_range_specification_parsing)
    runner.test("Pattern Validation", test_pattern_validation)
    runner.test("Enhanced Pattern Examples", test_enhanced_pattern_examples)
    
    # Integration tests
    runner.test("Filename Generation Integration", test_filename_generation_integration)
    runner.test("Backward Compatibility", test_backward_compatibility)
    
    # Edge case and error handling
    runner.test("Error Edge Cases", test_error_edge_cases)
    
    # Show final results
    all_passed = runner.show_summary()
    
    # Return appropriate exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())


# End of file #
