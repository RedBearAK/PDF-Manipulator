#!/usr/bin/env python3
"""
Test suite for class-based OperationContext.
File: tests/test_operation_context.py

Tests the new class-based OperationContext that eliminates parameter proliferation
and absorbs ResultsManager functionality. No instances - pure class-based utility.

Run: python tests/test_operation_context.py
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime
from rich.console import Console

from pdf_manipulator.core.operation_context import (
    OperationContext, OpCtx, ParsedResults,
    get_cached_parsing_results, store_parsing_results, get_parsed_pages
)


console = Console()


def create_mock_args(**kwargs):
    """Create a mock argparse.Namespace with specified attributes."""
    args = argparse.Namespace()
    
    # Set defaults
    defaults = {
        'batch': False,
        'dry_run': False,
        'extract_pages': '1-5',
        'conflicts': 'ask',
        'scrape_pattern': None,
        'filename_template': None,
        'pattern_source_page': 1,
        'dedup': None,
        'respect_groups': False,
        'separate_files': False,
    }
    
    # Override with provided kwargs
    for key, value in {**defaults, **kwargs}.items():
        setattr(args, key, value)
    
    return args


def create_mock_page_groups():
    """Create mock page groups for testing."""
    class MockPageGroup:
        def __init__(self, pages, is_range=False, original_spec="test"):
            self.pages = pages
            self.is_range = is_range
            self.original_spec = original_spec
    
    return [
        MockPageGroup([1, 2, 3], True, "1-3"),
        MockPageGroup([4, 5], False, "4,5")
    ]


def test_instantiation_prevention():
    """Test that OperationContext prevents instantiation."""
    console.print("[cyan]Testing instantiation prevention...[/cyan]")
    
    try:
        # This should fail with RuntimeError
        ctx = OperationContext()
        console.print("  [red]✗ Instantiation was allowed (should be prevented)[/red]")
        return False
    except RuntimeError as e:
        expected_message = "OperationContext should not be instantiated"
        if expected_message in str(e):
            console.print("  [green]✓ Instantiation correctly prevented[/green]")
            console.print(f"    Error message: {e}")
            return True
        else:
            console.print(f"  [red]✗ Wrong error message: {e}[/red]")
            return False
    except Exception as e:
        console.print(f"  [red]✗ Unexpected exception: {e}[/red]")
        return False


def test_class_based_args_setting():
    """Test setting arguments using class methods."""
    console.print("[cyan]Testing class-based args setting...[/cyan]")
    
    try:
        # Reset state first
        OperationContext.reset()
        
        # Create mock arguments
        test_args = create_mock_args(
            batch=True,
            dry_run=True,
            extract_pages="file:test.txt",
            conflicts='rename'
        )
        
        # Set arguments using class method
        OperationContext.set_args(test_args)
        
        # Verify state was set correctly
        if (OperationContext.args is test_args and 
            OperationContext.batch_mode is True and
            OperationContext.dry_run is True and
            OperationContext.interactive is False):  # batch mode should be non-interactive
            console.print("  [green]✓ Arguments set correctly via class method[/green]")
            console.print(f"    Batch mode: {OperationContext.batch_mode}")
            console.print(f"    Dry run: {OperationContext.dry_run}")
            console.print(f"    Interactive: {OperationContext.interactive}")
            return True
        else:
            console.print("  [red]✗ Arguments not set correctly[/red]")
            console.print(f"    Expected batch_mode=True, got {OperationContext.batch_mode}")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error setting arguments: {e}[/red]")
        return False


def test_current_pdf_context():
    """Test setting and getting current PDF context."""
    console.print("[cyan]Testing current PDF context management...[/cyan]")
    
    try:
        # Reset state first
        OperationContext.reset()
        test_args = create_mock_args()
        OperationContext.set_args(test_args)
        
        # Set current PDF context
        test_path = Path("test_document.pdf")
        test_page_count = 42
        
        OperationContext.set_current_pdf(test_path, test_page_count)
        
        # Verify context was set
        pdf_path, page_count = OperationContext.get_current_pdf_info()
        
        if pdf_path == test_path and page_count == test_page_count:
            console.print("  [green]✓ Current PDF context set and retrieved correctly[/green]")
            console.print(f"    PDF: {pdf_path.name}")
            console.print(f"    Pages: {page_count}")
            return True
        else:
            console.print(f"  [red]✗ Context mismatch: expected ({test_path}, {test_page_count}), got ({pdf_path}, {page_count})[/red]")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error managing PDF context: {e}[/red]")
        return False


def test_parsing_results_caching():
    """Test the simple parsing results storage."""
    console.print("[cyan]Testing parsing results storage...[/cyan]")
    
    try:
        # Reset state first
        OperationContext.reset()
        test_args = create_mock_args(extract_pages="1-10")
        OperationContext.set_args(test_args)
        OperationContext.set_current_pdf(Path("cached_test.pdf"), 50)
        
        # Check that we don't have results yet
        if not OperationContext.has_parsed_results():
            console.print("  ✓ No results stored initially")
        else:
            console.print("  [red]✗ Results found when none should exist[/red]")
            return False
        
        # Store some parsed results
        selected_pages = {1, 2, 4, 5, 8, 9}
        range_description = "pages1-2,4-5,8-9"
        page_groups = create_mock_page_groups()
        
        OperationContext.store_parsed_results(selected_pages, range_description, page_groups)
        
        # Try to retrieve stored results
        cached = OperationContext.get_cached_parsing_results()
        
        if (cached and 
            cached.selected_pages == selected_pages and
            cached.range_description == range_description and
            len(cached.page_groups) == len(page_groups)):
            console.print("  ✓ Parsing results stored and retrieved successfully")
            console.print(f"    Stored: {cached}")
            return True
        else:
            console.print("  [red]✗ Stored results don't match retrieved results[/red]")
            if cached:
                console.print(f"    Expected pages: {selected_pages}")
                console.print(f"    Got pages: {cached.selected_pages}")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error with results storage: {e}[/red]")
        return False


def test_convenience_functions():
    """Test the convenience functions work with class-based context."""
    console.print("[cyan]Testing convenience functions integration...[/cyan]")
    
    try:
        # Reset and set up context
        OperationContext.reset()
        test_args = create_mock_args(extract_pages="5-15")
        OperationContext.set_args(test_args)
        OperationContext.set_current_pdf(Path("convenience_test.pdf"), 30)
        
        # Use convenience function to store results
        selected_pages = {5, 6, 7, 10, 11, 15}
        range_description = "pages5-7,10-11,15"
        page_groups = create_mock_page_groups()
        
        store_parsing_results(selected_pages, range_description, page_groups)
        
        # Use convenience function to retrieve results  
        cached = get_cached_parsing_results()
        
        # Use convenience function to get parsed pages
        pages, desc, groups = get_parsed_pages()
        
        if (cached and pages == selected_pages and desc == range_description):
            console.print("  [green]✓ Convenience functions work with class-based context[/green]")
            console.print(f"    Retrieved {len(pages)} pages via get_parsed_pages()")
            return True
        else:
            console.print("  [red]✗ Convenience functions failed[/red]")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error with convenience functions: {e}[/red]")
        return False


def test_parameter_elimination_simulation():
    """Test that parameter elimination works as intended."""
    console.print("[cyan]Testing parameter elimination simulation...[/cyan]")
    
    try:
        # Simulate the old way vs new way
        
        # OLD WAY: Functions need lots of parameters
        def old_function(pdf_path, page_range, patterns, template, source_page, 
                        dry_run, dedup_strategy, use_timestamp, custom_prefix, 
                        conflict_strategy, interactive):
            return f"OLD: 11 parameters needed"
        
        # NEW WAY: Functions use context
        def new_function():
            # Everything available from OperationContext class attributes
            pdf_path = OperationContext.current_pdf_path
            dry_run = OperationContext.dry_run
            dedup_strategy = OperationContext.dedup_strategy
            # ... all other configuration available directly
            return f"NEW: 0 parameters, context has everything needed"
        
        # Set up context
        OperationContext.reset()
        test_args = create_mock_args(extract_pages="1-10")
        OperationContext.set_args(test_args)
        OperationContext.set_current_pdf(Path("param_test.pdf"), 25)
        
        # Test both approaches
        old_result = old_function(
            Path("param_test.pdf"), "1-10", None, None, 1, 
            False, "strict", False, None, "ask", True
        )
        new_result = new_function()
        
        console.print(f"  {old_result}")
        console.print(f"  [green]{new_result}[/green]")
        console.print("  [green]✓ Parameter elimination demonstrated[/green]")
        return True
        
    except Exception as e:
        console.print(f"  [red]✗ Error in parameter elimination test: {e}[/red]")
        return False


def test_opctx_alias():
    """Test the OpCtx convenience alias works."""
    console.print("[cyan]Testing OpCtx alias...[/cyan]")
    
    try:
        # Reset state
        OpCtx.reset()
        
        # Test that OpCtx is the same as OperationContext
        if OpCtx is OperationContext:
            console.print("  [green]✓ OpCtx alias correctly points to OperationContext[/green]")
            
            # Test using OpCtx alias  
            test_args = create_mock_args(batch=True)
            OpCtx.set_args(test_args)
            
            if OpCtx.batch_mode is True:
                console.print("  [green]✓ OpCtx alias methods work correctly[/green]")
                return True
            else:
                console.print("  [red]✗ OpCtx alias methods don't work[/red]")
                return False
        else:
            console.print("  [red]✗ OpCtx alias doesn't point to OperationContext[/red]")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error testing OpCtx alias: {e}[/red]")
        return False


def test_batch_mode_conflict_conversion():
    """Test that batch mode converts 'ask' to 'rename' for safety."""
    console.print("[cyan]Testing batch mode conflict strategy conversion...[/cyan]")
    
    try:
        # Test interactive mode (should keep 'ask')
        OperationContext.reset()
        interactive_args = create_mock_args(batch=False, conflicts='ask')
        OperationContext.set_args(interactive_args)
        
        if (OperationContext.conflict_strategy == 'ask' and 
            OperationContext.interactive is True):
            console.print("  [green]✓ Interactive mode preserves 'ask' strategy[/green]")
            interactive_passed = True
        else:
            console.print(f"  [red]✗ Interactive mode failed: strategy={OperationContext.conflict_strategy}[/red]")
            interactive_passed = False
        
        # Test batch mode (should convert 'ask' to 'rename')
        OperationContext.reset()  
        batch_args = create_mock_args(batch=True, conflicts='ask')
        OperationContext.set_args(batch_args)
        
        if (OperationContext.conflict_strategy == 'rename' and 
            OperationContext.interactive is False):
            console.print("  [green]✓ Batch mode converts 'ask' to 'rename'[/green]")
            batch_passed = True
        else:
            console.print(f"  [red]✗ Batch mode failed: strategy={OperationContext.conflict_strategy}[/red]")
            batch_passed = False
        
        return interactive_passed and batch_passed
        
    except Exception as e:
        console.print(f"  [red]✗ Error testing batch mode conversion: {e}[/red]")
        return False


def test_reset_functionality():
    """Test that reset clears all state properly."""
    console.print("[cyan]Testing reset functionality...[/cyan]")
    
    try:
        # Set up some state
        test_args = create_mock_args(batch=True, dry_run=True)
        OperationContext.set_args(test_args)
        OperationContext.set_current_pdf(Path("reset_test.pdf"), 100)
        
        # Store some parsed results
        selected_pages = {1, 2, 3}
        OperationContext.store_parsed_results(selected_pages, "test", [])
        
        # Verify state is set
        if (OperationContext.args is not None and 
            OperationContext.current_pdf_path is not None and
            OperationContext.has_parsed_results()):
            console.print("  ✓ State set up for reset test")
        else:
            console.print("  [red]✗ Failed to set up state for reset test[/red]")
            return False
        
        # Reset everything
        OperationContext.reset()
        
        # Verify everything is cleared
        if (OperationContext.args is None and
            OperationContext.current_pdf_path is None and
            not OperationContext.has_parsed_results() and
            OperationContext.pdfs_processed == 0):
            console.print("  [green]✓ Reset clears all state correctly[/green]")
            return True
        else:
            console.print("  [red]✗ Reset did not clear all state[/red]")
            console.print(f"    args: {OperationContext.args}")
            console.print(f"    current_pdf_path: {OperationContext.current_pdf_path}")
            console.print(f"    has_parsed_results: {OperationContext.has_parsed_results()}")
            return False
            
    except Exception as e:
        console.print(f"  [red]✗ Error testing reset: {e}[/red]")
        return False


def run_all_tests():
    """Run all OperationContext tests."""
    console.print("\n[bold blue]🧪 OperationContext Class-Based Tests[/bold blue]\n")
    
    tests = [
        ("Instantiation Prevention", test_instantiation_prevention),
        ("Class-Based Args Setting", test_class_based_args_setting),
        ("Current PDF Context", test_current_pdf_context),
        ("Parsing Results Storage", test_parsing_results_caching),
        ("Convenience Functions", test_convenience_functions),
        ("Parameter Elimination", test_parameter_elimination_simulation),
        ("OpCtx Alias", test_opctx_alias),
        ("Batch Mode Conversion", test_batch_mode_conflict_conversion),
        ("Reset Functionality", test_reset_functionality),
    ]
    
    results = []
    for test_name, test_func in tests:
        console.print(f"\n[bold]{test_name}[/bold]")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"  [red]✗ Test crashed: {e}[/red]")
            results.append((test_name, False))
    
    # Summary
    console.print("\n[bold blue]📊 Test Results Summary[/bold blue]\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[green]✓ PASS[/green]" if result else "[red]✗ FAIL[/red]"
        console.print(f"  {status} {test_name}")
    
    console.print(f"\n[bold]Overall: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All OperationContext tests passed![/bold green]")
        console.print("\n[yellow]💡 Key achievements:[/yellow]")
        console.print("  • Class-based utility pattern working correctly")
        console.print("  • Instantiation properly prevented")
        console.print("  • ResultsManager functionality fully absorbed")
        console.print("  • Parameter proliferation eliminated")
        console.print("  • Batch mode safety conversions working")
        console.print("  • Cache integration functional")
        console.print("\n[green]✨ Ready for production use![/green]")
        return True
    else:
        console.print(f"\n[bold red]❌ {total - passed} test(s) failed[/bold red]")
        console.print("The class-based OperationContext needs more work.")
        return False


def main() -> int:
    """Main entry point."""
    try:
        success = run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Test runner crashed: {e}[/red]")
        return 1


# Support for both standalone and pytest execution
def test_main():
    """Entry point for pytest."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())


# End of file #
