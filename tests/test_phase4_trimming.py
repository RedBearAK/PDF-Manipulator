"""
Phase 4 Trimming Logic Test Module
File: tests/test_phase4_trimming.py

Tests for the core trimming functionality before regex integration.
"""

from rich.console import Console

from pdf_manipulator.scraper.extractors.trimming import (
    parse_trimmer_block,
    apply_single_trimmer,
    apply_trimmers,
    validate_trimming_feasibility,
    TrimmingError
)


console = Console()


def test_trimmer_block_parsing():
    """Test parsing of trimmer block strings."""
    console.print("\n[cyan]Testing Trimmer Block Parsing...[/cyan]")
    
    test_cases = [
        # (input, expected_result, should_succeed)
        ("ch5", [('ch', 5)], True),
        ("wd1ch2", [('wd', 1), ('ch', 2)], True),
        ("ch3wd2nb1", [('ch', 3), ('wd', 2), ('nb', 1)], True),
        ("wd1ch5nb2ln3", [('wd', 1), ('ch', 5), ('nb', 2), ('ln', 3)], True),
        ("", [], True),  # Empty string should return empty list
        ("ch0", None, False),  # Zero count should fail
        ("invalid", None, False),  # Invalid trimmer type
        ("ch5xy2", None, False),  # Invalid characters mixed in
        ("ch999", [('ch', 999)], True),  # Large but valid count
    ]
    
    successes = 0
    for input_str, expected, should_succeed in test_cases:
        try:
            result = parse_trimmer_block(input_str)
            
            if should_succeed:
                if result == expected:
                    console.print(f"  ✓ '{input_str}' → {result}")
                    successes += 1
                else:
                    console.print(f"  [red]✗ '{input_str}' got {result}, expected {expected}[/red]")
            else:
                console.print(f"  [red]✗ '{input_str}' should have failed but got {result}[/red]")
                
        except TrimmingError:
            if not should_succeed:
                console.print(f"  ✓ '{input_str}' correctly rejected")
                successes += 1
            else:
                console.print(f"  [red]✗ '{input_str}' should have succeeded but failed[/red]")
        except Exception as e:
            console.print(f"  [red]✗ '{input_str}' unexpected error: {e}[/red]")
    
    console.print(f"  Parsing: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_character_trimming():
    """Test character trimming operations."""
    console.print("\n[cyan]Testing Character Trimming...[/cyan]")
    
    test_cases = [
        # (content, count, from_start, expected_result)
        ("CompanyNameACME", 11, True, "ACME"),  # Start trimming
        ("CompanyNameACME", 4, False, "CompanyName"),  # End trimming
        ("Hello", 2, True, "llo"),
        ("Hello", 2, False, "Hel"),
        ("A", 1, True, ""),  # Trim everything
        ("AB", 5, True, ""),  # Over-trimming
        ("", 1, True, ""),  # Empty content
    ]
    
    successes = 0
    for content, count, from_start, expected in test_cases:
        try:
            result = apply_single_trimmer(content, 'ch', count, from_start)
            direction = "start" if from_start else "end"
            
            if result == expected:
                console.print(f"  ✓ '{content}' trim {count} chars from {direction} → '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ '{content}' trim {count} chars from {direction} got '{result}', expected '{expected}'[/red]")
                
        except Exception as e:
            console.print(f"  [red]✗ Error trimming '{content}': {e}[/red]")
    
    console.print(f"  Character trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_word_trimming():
    """Test word trimming operations."""
    console.print("\n[cyan]Testing Word Trimming...[/cyan]")
    
    test_cases = [
        # (content, count, from_start, expected_result)
        ("OLD REF 2024 001 TEMP", 1, True, "REF 2024 001 TEMP"),
        ("OLD REF 2024 001 TEMP", 2, False, "OLD REF 2024"),
        ("Company Name ACME Corp", 2, True, "ACME Corp"),
        ("Single", 1, True, ""),
        ("One Two", 3, True, ""),  # Over-trimming
        ("", 1, True, ""),  # Empty content
    ]
    
    successes = 0
    for content, count, from_start, expected in test_cases:
        try:
            result = apply_single_trimmer(content, 'wd', count, from_start)
            direction = "start" if from_start else "end"
            
            if result == expected:
                console.print(f"  ✓ '{content}' trim {count} words from {direction} → '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ '{content}' trim {count} words from {direction} got '{result}', expected '{expected}'[/red]")
                
        except Exception as e:
            console.print(f"  [red]✗ Error trimming '{content}': {e}[/red]")
    
    console.print(f"  Word trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_number_trimming():
    """Test number trimming operations."""
    console.print("\n[cyan]Testing Number Trimming...[/cyan]")
    
    test_cases = [
        # (content, count, from_start, expected_result, description)
        ("Account123Extra", 1, False, "Account", "Trim number from end"),
        ("123Account456", 1, True, "Account456", "Trim number from start"),
        ("Ref-2024-001-TEMP", 1, False, "Ref-2024-", "Trim last number"),
        ("Ref-2024-001-TEMP", 2, False, "Ref-", "Trim last 2 numbers"),
        ("Invoice 1,250.00 Total", 1, False, "Invoice ", "Trim formatted number"),
        ("OLD-123-REF-456-NEW", 1, True, "-REF-456-NEW", "Trim first number"),
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
    
    console.print(f"  Number trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_combined_trimming():
    """Test applying multiple trimming operations."""
    console.print("\n[cyan]Testing Combined Trimming...[/cyan]")
    
    test_cases = [
        # (content, start_trimmers, end_trimmers, expected_result, description)
        (
            "CompanyNameACME", 
            [('ch', 11)], 
            [('ch', 4)], 
            "",  # 11 chars from start leaves "ACME", 4 from end leaves nothing
            "Character trimming from both ends"
        ),
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
            "Word start, number end trimming"
        ),
        (
            "Short", 
            [('ch', 10)], 
            [], 
            "",
            "Over-trimming should result in empty string"
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
    
    console.print(f"  Combined trimming: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_validation_warnings():
    """Test trimming feasibility validation."""
    console.print("\n[cyan]Testing Validation Warnings...[/cyan]")
    
    test_cases = [
        # (content, start_trimmers, end_trimmers, expected_warning_count, description)
        ("Hello", [('ch', 3)], [('ch', 3)], 1, "Character over-trimming"),
        ("One Two", [('wd', 1)], [('wd', 2)], 1, "Word over-trimming"),
        ("Line1\nLine2", [('ln', 1)], [('ln', 2)], 1, "Line over-trimming"),
        ("Normal content", [('ch', 2)], [('ch', 2)], 0, "Safe trimming"),
        ("", [('ch', 1)], [], 1, "Empty content trimming"),
        ("OK", [], [], 0, "No trimming operations"),
    ]
    
    successes = 0
    for content, start_trimmers, end_trimmers, expected_warnings, description in test_cases:
        try:
            warnings = validate_trimming_feasibility(content, start_trimmers, end_trimmers)
            warning_count = len(warnings)
            
            if warning_count == expected_warnings:
                console.print(f"  ✓ {description}: {warning_count} warnings as expected")
                successes += 1
            else:
                console.print(f"  [red]✗ {description}: got {warning_count} warnings, expected {expected_warnings}[/red]")
                if warnings:
                    for warning in warnings:
                        console.print(f"    Warning: {warning}")
                
        except Exception as e:
            console.print(f"  [red]✗ Error in {description}: {e}[/red]")
    
    console.print(f"  Validation: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_real_world_scenarios():
    """Test real-world OCR and PDF extraction scenarios."""
    console.print("\n[cyan]Testing Real-World Scenarios...[/cyan]")
    
    scenarios = [
        {
            'name': 'OCR spaced text cleanup',
            'content': 'I N V O I C E - 2 0 2 4 - 0 0 1',
            'start_trimmers': [('ch', 2)],  # Remove "I "
            'end_trimmers': [('ch', 2)],    # Remove " 1"
            'expected': 'N V O I C E - 2 0 2 4 - 0 0'
        },
        {
            'name': 'Company name extraction',
            'content': 'CompanyNameACMECorporation',
            'start_trimmers': [('ch', 11)],  # Remove "CompanyName"
            'end_trimmers': [('ch', 11)],    # Remove "Corporation"
            'expected': 'ACME'
        },
        # {
        #     'name': 'Reference code cleanup',
        #     'content': 'OLD-REF-2024-001-TEMP-DRAFT',
        #     'start_trimmers': [('wd', 1)],   # Remove "OLD-REF-2024-001-TEMP-DRAFT" -> can't remove words from this
        #     'end_trimmers': [('ch', 6)],     # Remove "-DRAFT"
        #     'expected': 'OLD-REF-2024-001-TEMP'  # This won't work as expected because no spaces
        # },
        {
            'name': 'Reference code cleanup',
            'content': 'OLD-REF-2024-001-TEMP-DRAFT',
            'start_trimmers': [('ch', 4)],   # Remove "OLD-" 
            'end_trimmers': [('ch', 6)],     # Remove "-DRAFT"
            'expected': 'REF-2024-001-TEMP'
        },

        {
            'name': 'Amount without currency',
            'content': '$1,250.00',
            'start_trimmers': [('ch', 1)],   # Remove "$"
            'end_trimmers': [],
            'expected': '1,250.00'
        },
        {
            'name': 'Invoice number extraction',
            'content': 'Invoice Number: INV-2024-001 (Draft)',
            'start_trimmers': [('wd', 2)],   # Remove "Invoice Number:"
            'end_trimmers': [('wd', 1)],     # Remove "(Draft)"
            'expected': 'INV-2024-001'
        }
    ]
    
    successes = 0
    for scenario in scenarios:
        try:
            result = apply_trimmers(
                scenario['content'], 
                scenario['start_trimmers'], 
                scenario['end_trimmers']
            )
            
            if result == scenario['expected']:
                console.print(f"  ✓ {scenario['name']}: '{result}'")
                successes += 1
            else:
                console.print(f"  [red]✗ {scenario['name']}: got '{result}', expected '{scenario['expected']}'[/red]")
                console.print(f"    Input: '{scenario['content']}'")
                
        except Exception as e:
            console.print(f"  [red]✗ Error in {scenario['name']}: {e}[/red]")
    
    console.print(f"  Real-world scenarios: {successes}/{len(scenarios)} tests passed")
    return successes == len(scenarios)


def main():
    """Run all trimming logic tests."""
    console.print("[bold blue]Phase 4 Trimming Logic Tests[/bold blue]")
    console.print("Testing core trimming functionality before regex integration...\n")
    
    tests = [
        ("Trimmer Block Parsing", test_trimmer_block_parsing),
        ("Character Trimming", test_character_trimming),
        ("Word Trimming", test_word_trimming),
        ("Number Trimming", test_number_trimming),
        ("Combined Trimming", test_combined_trimming),
        ("Validation Warnings", test_validation_warnings),
        ("Real-World Scenarios", test_real_world_scenarios),
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
    console.print(f"[bold]TRIMMING LOGIC TEST SUMMARY[/bold]")
    console.print(f"{'='*60}")
    console.print(f"Tests run: {total}")
    console.print(f"[green]Passed: {passed}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    console.print(f"Success rate: {success_rate:.1f}%")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())


# End of file #
