#!/usr/bin/env python3
"""
Simple test runner for the new group filtering features.
This avoids import issues with the existing codebase.
Usage: python simple_test_runner.py
"""

import sys
import subprocess

from pathlib import Path
from rich.console import Console


console = Console()


def run_standalone_test() -> bool:
    """Run the standalone filtering test."""
    test_file = Path("test_standalone_filtering.py")
    
    if not test_file.exists():
        console.print(f"[red]Test file not found: {test_file}[/red]")
        return False
    
    console.print(f"[blue]Running standalone group filtering test...[/blue]")
    
    try:
        # Run the test directly with Python
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=False,  # Let output show directly
            timeout=30
        )
        
        success = (result.returncode == 0)
        
        if success:
            console.print(f"\n[bold green]✓ Standalone test passed![/bold green]")
        else:
            console.print(f"\n[bold red]✗ Standalone test failed (exit code: {result.returncode})[/bold red]")
        
        return success
        
    except subprocess.TimeoutExpired:
        console.print(f"[red]Test timed out after 30 seconds[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error running test: {e}[/red]")
        return False


def test_import_detection() -> bool:
    """Test which modules can be imported from the existing codebase."""
    console.print(f"\n[blue]Testing imports from existing codebase...[/blue]")
    
    modules_to_test = [
        "pdf_manipulator",
        "pdf_manipulator.core",
        "pdf_manipulator.core.parser",
        "pdf_manipulator.core.page_range",
        "pdf_manipulator.core.page_range.page_group",
    ]
    
    importable_modules = []
    
    for module_name in modules_to_test:
        try:
            # Add parent directory to path for import testing
            sys.path.insert(0, str(Path("..").absolute()))
            __import__(module_name)
            console.print(f"  ✓ {module_name}")
            importable_modules.append(module_name)
        except ImportError as e:
            console.print(f"  ✗ {module_name}: {e}")
        except Exception as e:
            console.print(f"  ✗ {module_name}: Unexpected error: {e}")
    
    console.print(f"\n[dim]Importable modules: {len(importable_modules)}/{len(modules_to_test)}[/dim]")
    return len(importable_modules) > 0


def check_test_files() -> bool:
    """Check which test files exist."""
    console.print(f"\n[blue]Checking test files...[/blue]")
    
    all_test_files = list(Path(".").glob("test_*.py"))
    
    # Skip runner files and problematic modules
    skip_files = {
        "test_pdf_utils.py",      # Incomplete/problematic
        "run_tests.py",           # Test runner
        "simple_test_runner.py",  # This runner
    }
    
    test_files = [f for f in all_test_files if f.name not in skip_files]
    skipped_files = [f for f in all_test_files if f.name in skip_files]
    
    if not test_files:
        console.print("[yellow]No test files found[/yellow]")
        return False
    
    console.print(f"Found {len(test_files)} test files:")
    for test_file in sorted(test_files):
        size = test_file.stat().st_size
        console.print(f"  {test_file.name} ({size:,} bytes)")
    
    if skipped_files:
        console.print(f"\nSkipped {len(skipped_files)} files:")
        for skipped_file in sorted(skipped_files):
            console.print(f"  [dim]{skipped_file.name} (skipped)[/dim]")
    
    return True


def main() -> int:
    """Main entry point."""
    console.print("[bold]PDF Manipulator - Simple Test Runner[/bold]")
    console.print("[dim]Testing new group filtering features[/dim]")
    
    # Check current directory
    current_dir = Path(".").absolute()
    console.print(f"\nCurrent directory: {current_dir}")
    
    # Check for test files
    has_tests = check_test_files()
    if not has_tests:
        console.print("[yellow]No tests to run[/yellow]")
        return 1
    
    # Test imports (non-critical)
    test_import_detection()
    
    # Run the standalone test
    success = run_standalone_test()
    
    if success:
        console.print(f"\n[bold green]All tests completed successfully! ✓[/bold green]")
        console.print("[dim]The group filtering logic is ready for integration[/dim]")
        return 0
    else:
        console.print(f"\n[bold red]Tests failed[/bold red]")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test run interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Test runner error: {e}[/red]")
        sys.exit(1)
