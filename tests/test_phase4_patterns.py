"""
Phase 4 Enhanced Pattern Processor Test Module
File: tests/test_phase4_patterns.py

Tests for Phase 4 start/end trimming integration with pattern parsing.
Uses external regex imports to avoid corruption.
"""

import re
from rich.console import Console

# Import the actual regex patterns from subsection files
from pdf_manipulator.renamer.renamer_regex_patterns import COMPACT_PATTERN_RGX
from pdf_manipulator.scraper.extractors.trimming import parse_trimmer_block, TrimmingError


console = Console()


class CleanPatternProcessor:
    """Clean pattern processor that imports regex from external files."""
    
    def __init__(self):
        # Use the actual regex pattern from the external file
        self.COMPACT_PATTERN = COMPACT_PATTERN_RGX
    
    def test_regex_matching(self, pattern_string):
        """Test if pattern matches regex with business logic validation."""
        match = self.COMPACT_PATTERN.match(pattern_string)
        if not match:
            return {'matched': False, 'reason': 'No regex match'}
        
        # Additional validation for zero counts using business logic
        start_trimmers = match.group(6)
        end_trimmers = match.group(7)
        
        # Pattern to detect zero counts
        zero_count_rgx = re.compile(r'(wd|ln|nb|ch)0')
        
        if start_trimmers and zero_count_rgx.search(start_trimmers):
            return {'matched': False, 'reason': 'Zero count in start trimmer'}
        
        if end_trimmers and zero_count_rgx.search(end_trimmers):
            return {'matched': False, 'reason': 'Zero count in end trimmer'}
        
        return {
            'matched': True,
            'groups': match.groups(),
            'movement1': match.group(1),
            'movement2': match.group(2),
            'extract_type': match.group(3),
            'extract_count': match.group(4),
            'flags': match.group(5),
            'start_trimmers': match.group(6),
            'end_trimmers': match.group(7),
            'page_spec': match.group(8),
            'match_spec': match.group(9)
        }


def test_phase4_regex_patterns():
    """Test that Phase 4 enhanced regex patterns match correctly."""
    console.print("\n[cyan]Testing Phase 4 Regex Pattern Matching...[/cyan]")
    
    processor = CleanPatternProcessor()
    
    test_cases = [
        # Basic Phase 4 patterns
        ("wd1^ch5", True, "Valid start trimmer"),
        ("wd1$ch3", True, "Valid end trimmer"),
        ("wd3^ch5$ch3", True, "Valid both trimmers"),
        ("wd4_^wd1ch2$ch4", True, "With flags and complex trimmers"),
        ("wd2-^ch8$wd1", True, "With cross-newline flag"),
        ("wd2_-^ch8$wd1", True, "With both flags"),
        ("r1wd1^ch4$ch2", True, "With movements"),
        ("d1r2wd3_^ch5$wd1ch3", True, "Complex with movements"),
        ("wd1^ch2pg3", True, "With page spec"),
        ("r1wd2_^ch3$ch4pg2-4mt2", True, "Full complex pattern"),
        ("wd1^ch5wd1nb2", True, "Multiple start trimmers"),
        ("wd1$wd2ch3ln1", True, "Multiple end trimmers"),
        ("wd1^ch2wd1$nb1ch3wd2", True, "Multiple both trimmers"),
        
        # Backward compatibility
        ("r1wd1", True, "Basic Phase 2 pattern"),
        ("wd3-", True, "Phase 2 flexible extraction"),
        ("r1wd1pg2-4mt3", True, "Phase 3 multi-page pattern"),
        
        # Invalid patterns that should be rejected
        ("wd1^", False, "Empty start trimmer"),
        ("wd1$", False, "Empty end trimmer"),
        ("wd1^ch5$", False, "Valid start, empty end"),
        ("wd1^$ch3", False, "Empty start, valid end"),
        ("wd1^ch0", False, "Zero count in start trimmer"),
        ("wd1$ch0", False, "Zero count in end trimmer"),
        ("wd1^ch", False, "Missing count in trimmer"),
        ("wd1^xy5", False, "Invalid trimmer type"),
        ("^ch5", False, "Missing base extraction"),
        ("$ch3", False, "Missing base extraction"),
    ]
    
    successes = 0
    for pattern, should_match, description in test_cases:
        result = processor.test_regex_matching(pattern)
        is_match = result['matched']
        
        if is_match == should_match:
            status = "✓" if should_match else "✓ (correctly rejected)"
            console.print(f"  {status} {description}: '{pattern}'")
            successes += 1
        else:
            expected = "match" if should_match else "reject"
            actual = "matched" if is_match else "rejected"
            console.print(f"  [red]✗ {description}: '{pattern}' expected {expected}, got {actual}[/red]")
            if 'reason' in result:
                console.print(f"    Reason: {result['reason']}")
    
    console.print(f"  Regex matching: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_trimmer_block_parsing():
    """Test parsing of trimmer blocks extracted from regex."""
    console.print("\n[cyan]Testing Trimmer Block Parsing from Regex...[/cyan]")
    
    test_cases = [
        ("ch5", [('ch', 5)], True, "Single character trimmer"),
        ("wd1ch2", [('wd', 1), ('ch', 2)], True, "Two trimmers"),
        ("ch5wd1nb2", [('ch', 5), ('wd', 1), ('nb', 2)], True, "Three trimmers"),
        ("wd1ch5nb2ln3", [('wd', 1), ('ch', 5), ('nb', 2), ('ln', 3)], True, "Four trimmers"),
        ("ch999", [('ch', 999)], True, "Large count"),
        ("ch0", None, False, "Zero count should fail"),
        ("xy5", None, False, "Invalid trimmer type"),
        ("ch5xy2", None, False, "Mixed valid/invalid"),
        ("", [], True, "Empty should return empty list"),
    ]
    
    successes = 0
    for trimmer_block, expected, should_succeed, description in test_cases:
        try:
            result = parse_trimmer_block(trimmer_block)
            
            if should_succeed:
                if result == expected:
                    console.print(f"  ✓ {description}: '{trimmer_block}' → {result}")
                    successes += 1
                else:
                    console.print(f"  [red]✗ {description}: '{trimmer_block}' got {result}, expected {expected}[/red]")
            else:
                console.print(f"  [red]✗ {description}: '{trimmer_block}' should have failed but got {result}[/red]")
                
        except TrimmingError:
            if not should_succeed:
                console.print(f"  ✓ {description}: '{trimmer_block}' correctly rejected")
                successes += 1
            else:
                console.print(f"  [red]✗ {description}: '{trimmer_block}' should have succeeded but failed[/red]")
        except Exception as e:
            console.print(f"  [red]✗ {description}: '{trimmer_block}' unexpected error: {e}[/red]")
    
    console.print(f"  Trimmer parsing: {successes}/{len(test_cases)} tests passed")
    return successes == len(test_cases)


def test_complete_pattern_parsing():
    """Test complete pattern string parsing with Phase 4 syntax."""
    console.print("\n[cyan]Testing Complete Pattern String Parsing...[/cyan]")
    
    processor = CleanPatternProcessor()
    
    pattern_examples = [
        # Valid patterns
        ("invoice=Invoice Number:r1wd1^ch4", True, "Invoice with start trimming"),
        ("company=Company:r1wd3_^ch8$ch12", True, "Company with space exclusion and both-end trimming"),
        ("amount=Total:r1nb1_^ch1", True, "Amount without currency symbol"),
        ("ref=Reference:r1wd4_^wd2ch3$wd1pg2", True, "Complex reference with page specification"),
        ("code=Code:r1wd1$nb1", True, "Code with numeric suffix removal"),
        ("title=Title:u1ln1^ch5$ch3pg2-4mt2", True, "Multi-page title with character trimming"),
        
        # Backward compatibility
        ("old_style=Invoice:r1wd1", True, "Phase 2 style pattern"),
        ("flexible=Description:r1wd0-", True, "Phase 2 flexible extraction"),
        ("multi_page=Summary:d1wd5pg3-", True, "Phase 3 multi-page pattern"),
        
        # Invalid patterns  
        ("invalid1=Keyword:wd1^", False, "Empty start trimmer"),
        ("invalid2=Keyword:wd1^ch0", False, "Zero count trimmer"),
        ("invalid3=Keyword:wd1^xy5", False, "Invalid trimmer type"),
        ("invalid4=Keyword:wd1$", False, "Empty end trimmer"),
        ("invalid5=Keyword:^ch5", False, "Missing base extraction"),
    ]
    
    successes = 0
    for pattern_str, should_parse, description in pattern_examples:
        # Extract just the extraction spec part for testing
        if ':' in pattern_str:
            _, extraction_spec = pattern_str.rsplit(':', 1)
            result = processor.test_regex_matching(extraction_spec)
            
            if should_parse:
                if result['matched']:
                    console.print(f"  ✓ {description}: '{pattern_str}'")
                    successes += 1
                else:
                    console.print(f"  [red]✗ {description}: '{pattern_str}' should have parsed[/red]")
                    if 'reason' in result:
                        console.print(f"    Reason: {result['reason']}")
            else:
                if not result['matched']:
                    console.print(f"  ✓ {description}: '{pattern_str}' correctly rejected")
                    successes += 1
                else:
                    console.print(f"  [red]✗ {description}: '{pattern_str}' should have been rejected[/red]")
        else:
            console.print(f"  [red]✗ {description}: Invalid pattern format[/red]")
    
    console.print(f"  Complete parsing: {successes}/{len(pattern_examples)} tests passed")
    return successes == len(pattern_examples)


def test_real_world_scenarios():
    """Test real-world OCR and PDF scenarios that Phase 4 is designed to handle."""
    console.print("\n[cyan]Testing Real-World Phase 4 Scenarios...[/cyan]")
    
    processor = CleanPatternProcessor()
    
    scenarios = [
        {
            'name': 'OCR Invoice Number Cleanup',
            'pattern': 'r2wd3_^ch2',
            'description': 'Clean up spaced OCR text'
        },
        {
            'name': 'Company Name Extraction',
            'pattern': 'r2wd1^ch11$ch4',
            'description': 'Extract core company name from merged text'
        },
        {
            'name': 'Currency Amount Cleanup',
            'pattern': 'r2wd5_^ch1$ch3',
            'description': 'Clean currency formatting'
        },
        {
            'name': 'Reference Code Processing',
            'pattern': 'r2wd1^ch4$nb1',
            'description': 'Extract clean reference code'
        },
        {
            'name': 'Serial Number Extraction',
            'pattern': 'r2wd1^ch2$nb1',
            'description': 'Extract core serial number'
        },
        {
            'name': 'Multi-Page Complex Pattern',
            'pattern': 'd1r2wd3_^ch5$wd1ch3pg2-4mt2',
            'description': 'Complex multi-page pattern with trimming'
        }
    ]
    
    successes = 0
    for scenario in scenarios:
        pattern = scenario['pattern']
        result = processor.test_regex_matching(pattern)
        
        if result['matched']:
            console.print(f"  ✓ {scenario['name']}: Pattern '{pattern}' is valid")
            successes += 1
        else:
            console.print(f"  [red]✗ {scenario['name']}: Pattern '{pattern}' invalid[/red]")
            console.print(f"    Description: {scenario['description']}")
            if 'reason' in result:
                console.print(f"    Reason: {result['reason']}")
    
    console.print(f"  Real-world scenarios: {successes}/{len(scenarios)} patterns valid")
    return successes == len(scenarios)


def main():
    """Run all Phase 4 pattern processor tests."""
    console.print("[bold blue]Phase 4 Enhanced Pattern Processor Tests[/bold blue]")
    console.print("Testing regex integration and trimming system with clean imports...\n")
    
    tests = [
        ("Phase 4 Regex Pattern Matching", test_phase4_regex_patterns),
        ("Trimmer Block Parsing", test_trimmer_block_parsing),
        ("Complete Pattern Parsing", test_complete_pattern_parsing),
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
    console.print(f"[bold]PHASE 4 PATTERN PROCESSOR TEST SUMMARY[/bold]")
    console.print(f"{'='*60}")
    console.print(f"Tests run: {total}")
    console.print(f"[green]Passed: {passed}[/green]")
    console.print(f"[red]Failed: {failed}[/red]")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    console.print(f"Success rate: {success_rate:.1f}%")
    
    if failed == 0:
        console.print(f"\n[bold green]🎉 ALL TESTS PASSED! Phase 4 patterns working correctly![/bold green]")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())


# End of file #
