"""
Phase 4 Fixed Comprehensive Test Module
File: tests/test_phase4_fixed.py

Tests the fixes for number trimming and regex validation.
"""

import re
from rich.console import Console

# Updated functions with fixes
from pdf_manipulator.scraper.extractors.trimming import (
    parse_trimmer_block,
    apply_single_trimmer,
    apply_trimmers,
    TrimmingError
)


console = Console()


def test_fixed_number_trimming():
    """Test the fixed number trimming implementation."""
    console.print("\n[cyan]Testing Fixed Number Trimming...[/cyan]")
    
    test_cases = [
        # (content, count, from_start, expected_result, description)
        ("Account123Extra", 1, False, "Account", "Basic number trimming from end"),
        ("123Account456", 1, True, "Account456", "Basic number trimming from start"),
        ("Ref-2024-001-TEMP", 1, False, "Ref-2024-", "Trim last number with suffix"),
        ("Ref-2024-001-TEMP", 2, False, "Ref-", "Trim last 2 numbers"),
        ("Invoice 1,250.00 Total", 1, False, "Invoice ", "Formatted number trimming"),
        ("OLD-123-REF-456-NEW", 1, True, "-REF-456-NEW", "First number trimming"),
        ("NoNumbers", 1, True, "", "No numbers to trim"),
        ("123", 1, True, "", "Trim only number"),
    ]
    
    successes = 0
    for content, count, from_start, expected, description in test_cases:
        try:
            result = apply_single_trimmer(content, 'nb', count, from_start)
            direction = "start" if from_start else "end"
            
            if result == expected:
                console.print(f"  ✓ {description}: '{content}' → '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ {description}: '{content}' got '{result}', expected '{expected}'[/red]")
                
        except Exception as e:
            console.print(f"  [red]✗ Error in {description}: {e}[/red]")
    
    console.print(f"  Fixed number trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_fixed_combined_trimming():
    """Test fixed combined trimming scenarios."""
    console.print("\n[cyan]Testing Fixed Combined Trimming...[/cyan]")
    
    test_cases = [
        # (content, start_trimmers, end_trimmers, expected_result, description)
        (
            "CompanyNameACMECorporation", 
            [('ch', 11)], 
            [('ch', 11)], 
            "ACME",
            "Extract middle part with char trimming"
        ),
        (
            "OLD REF 2024 001 TEMP DRAFT", 
            [('wd', 1), ('ch', 4)], 
            [('wd', 2)], 
            "2024 001",
            "Mixed word and character trimming"
        ),
        (
            "Invoice INV-2024-001-TEMP", 
            [('wd', 1)], 
            [('nb', 1)], 
            "INV-2024-",
            "Word start, number end trimming (FIXED)"
        ),
        (
            "OLD-REF-2024-001-TEMP-DRAFT",
            [('ch', 4)],   # Remove "OLD-"
            [('nb', 1)],   # Remove last number "001" and everything after
            "REF-2024-",
            "Complex OCR cleanup (FIXED)"
        ),
        (
            "$1,250.00",
            [('ch', 1)],   # Remove "$"
            [],
            "1,250.00",
            "Currency removal"
        ),
    ]
    
    successes = 0
    for content, start_trimmers, end_trimmers, expected, description in test_cases:
        try:
            result = apply_trimmers(content, start_trimmers, end_trimmers)
            
            if result == expected:
                console.print(f"  ✓ {description}: '{content}' → '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ {description}: '{content}' got '{result}', expected '{expected}'[/red]")
                
        except Exception as e:
            console.print(f"  [red]✗ Error in {description}: {e}[/red]")
    
    console.print(f"  Fixed combined trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_regex_validation_fixes():
    """Test regex validation with stray character detection."""
    console.print("\n[cyan]Testing Regex Validation Fixes...[/cyan]")
    
    # Enhanced regex pattern
    COMPACT_PATTERN = re.compile(
        r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})([_\-]*)'
        r'(\^(?:(?:wd|ln|nb|ch)\d{1,3})+)?'  # Start trimmers (+ means 1 or more)
        r'(\$(?:(?:wd|ln|nb|ch)\d{1,3})+)?'  # End trimmers (+ means 1 or more)
        r'(pg(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?'
        r'(mt(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?$'
    )
    
    def validate_pattern(spec):
        """Validate pattern with both regex and stray character checks."""
        # Check for invalid stray ^ or $ characters
        if '^' in spec and not re.search(r'\^(?:wd|ln|nb|ch)\d{1,3}', spec):
            return False, f"Invalid '^' character without valid trimmer operations"
        
        if '$' in spec and not re.search(r'\$(?:wd|ln|nb|ch)\d{1,3}', spec):
            return False, f"Invalid '$' character without valid trimmer operations"
        
        # Check regex match
        match = COMPACT_PATTERN.match(spec)
        if not match:
            return False, "Pattern does not match regex"
        
        return True, "Valid"
    
    test_cases = [
        # (pattern, should_be_valid, description)
        ("wd1^ch5", True, "Valid start trimmer"),
        ("wd1$ch3", True, "Valid end trimmer"),
        ("wd1^ch5$ch3", True, "Valid both trimmers"),
        ("r1wd1", True, "No trimmers (backward compatibility)"),
        ("wd1^ch5wd1nb2", True, "Multiple start trimmers"),
        
        # Should be invalid
        ("wd1^", False, "Empty start trimmer"),
        ("wd1$", False, "Empty end trimmer"),
        ("wd1^ch5$", False, "Valid start, empty end"),
        ("wd1^$ch3", False, "Empty start, valid end"),
        ("^ch5", False, "Missing base extraction"),
        ("$ch3", False, "Missing base extraction"),
        ("wd1^ch", False, "Missing count in trimmer"),
        ("wd1^xy5", False, "Invalid trimmer type"),
    ]
    
    successes = 0
    for pattern, should_be_valid, description in test_cases:
        is_valid, message = validate_pattern(pattern)
        
        if is_valid == should_be_valid:
            status = "✓" if should_be_valid else "✓ (correctly rejected)"
            console.print(f"  {status} {description}: '{pattern}'")
            successes += 1
        else:
            expected = "valid" if should_be_valid else "invalid"
            actual = "valid" if is_valid else "invalid"
            console.print(f"  [red]✗ {description}: '{pattern}' expected {expected}, got {actual}[/red]")
            console.print(f"    {message}")
    
    console.print(f"  Regex validation: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_real_world_scenarios_fixed():
    """Test real-world scenarios with fixes applied."""
    console.print("\n[cyan]Testing Real-World Scenarios (Fixed)...[/cyan]")
    
    scenarios = [
        {
            'name': 'Company Name Extraction',
            'content': 'CompanyNameACMECorporation',
            'pattern_spec': 'wd1^ch11$ch11',
            'start_trimmers': [('ch', 11)],
            'end_trimmers': [('ch', 11)],
            'expected': 'ACME'
        },
        {
            'name': 'Currency Removal', 
            'content': '$1,250.00',
            'pattern_spec': 'wd1^ch1',
            'start_trimmers': [('ch', 1)],
            'end_trimmers': [],
            'expected': '1,250.00'
        },
        {
            'name': 'Reference Code Cleanup (FIXED)',
            'content': 'OLD-REF-2024-001-TEMP',
            'pattern_spec': 'wd1^ch4$nb1',
            'start_trimmers': [('ch', 4)],
            'end_trimmers': [('nb', 1)],
            'expected': 'REF-2024-'
        },
        {
            'name': 'Invoice Number with Space Cleanup',
            'content': 'I N V - 2 0 2 4 - 0 0 1',
            'pattern_spec': 'wd3_^ch2',  # Get 3 words, exclude spaces, trim 2 chars
            'start_trimmers': [('ch', 2)],
            'end_trimmers': [],
            'expected': 'V-2024-001',  # After space removal: "INV-2024-001", then trim "IN"
            'exclude_spaces': True
        },
        {
            'name': 'Account Code Extraction',
            'content': 'Account123Extra',
            'pattern_spec': 'wd1$nb1',
            'start_trimmers': [],
            'end_trimmers': [('nb', 1)],
            'expected': 'Account'
        }
    ]
    
    successes = 0
    for scenario in scenarios:
        try:
            content = scenario['content']
            
            # Apply space exclusion if specified
            if scenario.get('exclude_spaces', False):
                content = content.replace(' ', '')
                console.print(f"  After space exclusion: '{content}'")
            
            result = apply_trimmers(
                content, 
                scenario['start_trimmers'], 
                scenario['end_trimmers']
            )
            
            if result == scenario['expected']:
                console.print(f"  ✓ {scenario['name']}: '{scenario['content']}' → '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ {scenario['name']}: '{scenario['content']}' got '{result}', expected '{scenario['expected']}'[/red]")
                
        except Exception as e:
            console.print(f"  [red]✗ Error in {scenario['name']}: {e}[/red]")
    
    console.print(f"  Real-world scenarios: {successes}/{len(scenarios)} tests passed")
    return successes == len(scenarios)


def main():
    """Run all fixed Phase 4 tests."""
    console.print("[bold blue]Phase 4 Fixed Comprehensive Tests[/bold blue]")
    console.print("Testing fixes for number trimming and regex validation...\n")
    
    tests = [
        ("Fixed Number Trimming", test_fixed_number_trimming),
        ("Fixed Combined Trimming", test_fixed_combined_trimming), 
        ("Regex Validation Fixes", test_regex_validation_fixes),
        ("Real-World Scenarios (Fixed)", test_real_world_scenarios_fixed),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            console.print(f"[red]✗ {test_name} crashed: {e}[/red]")
            failed += 1
    
    total = passed + failed
    console.print(f"\n{'='*60}")
    console.print(f"[bold]PHASE 4 FIXED TEST SUMMARY[/bold]")
    console.print(f"{'='*60}")
    console.print(f"Tests run: {total}")
    console.print(f"[green]Passed: {passed}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    console.print(f"Success rate: {success_rate:.1f}%")
    
    if failed == 0:
        console.print(f"\n[bold green]🎉 ALL TESTS PASSED! Phase 4 implementation is working correctly![/bold green]")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())


# End of file #
