#!/usr/bin/env python3
"""
Simple test runner for PDF Manipulator test modules.
Usage: python run_tests.py [test_module_name]

Runs from tests/ directory and discovers test modules automatically.
"""

import sys
import importlib
import subprocess

from pathlib import Path
from rich.console import Console
from rich.table import Table


console = Console()


def find_test_modules() -> list[Path]:
    """Find all test modules in the current directory."""
    test_files = []
    
    # Skip problematic or incomplete test modules
    skip_modules = {
        "test_pdf_utils.py",  # Incomplete/problematic module
        "run_tests.py",       # This runner itself
        "simple_test_runner.py",  # Other runner
    }
    
    for file_path in Path('.').glob('test_*.py'):
        if file_path.name not in skip_modules:
            test_files.append(file_path)
    
    return sorted(test_files)


def run_single_test(test_file: Path) -> tuple[bool, float, str]:
    """Run a single test module and return (success, duration, output)."""
    import time
    import importlib.util
    
    module_name = test_file.stem
    
    try:
        start_time = time.time()
        
        # Try to import and run the module's main function
        spec = importlib.util.spec_from_file_location(module_name, test_file)
        if spec is None or spec.loader is None:
            return False, 0.0, f"Could not load module {module_name}"
        
        module = importlib.util.module_from_spec(spec)
        
        # Try to execute the module
        try:
            spec.loader.exec_module(module)
        except ImportError as e:
            duration = time.time() - start_time
            return False, duration, f"Import error: {e}"
        except ModuleNotFoundError as e:
            duration = time.time() - start_time
            return False, duration, f"Module not found: {e}"
        except Exception as e:
            duration = time.time() - start_time
            return False, duration, f"Module execution error: {e}"
        
        # Look for main function
        if hasattr(module, 'main'):
            try:
                result = module.main()
                duration = time.time() - start_time
                success = (result == 0)
                return success, duration, f"Exit code: {result}"
            except Exception as e:
                duration = time.time() - start_time
                return False, duration, f"Main function error: {e}"
        else:
            duration = time.time() - start_time
            return False, duration, "No main() function found"
            
    except Exception as e:
        duration = time.time() - start_time
        return False, duration, f"Unexpected error: {e}"


def run_with_pytest(test_file: Path) -> tuple[bool, float, str]:
    """Run test with pytest as fallback."""
    import time
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v'],
            capture_output=True,
            text=True,
            timeout=60
        )
        duration = time.time() - start_time
        
        success = (result.returncode == 0)
        output = result.stdout if result.stdout else result.stderr
        
        return success, duration, f"pytest exit code: {result.returncode}"
        
    except subprocess.TimeoutExpired:
        return False, 60.0, "Test timed out (60s)"
    except Exception as e:
        return False, 0.0, f"pytest error: {e}"


def run_all_tests() -> tuple[int, int]:
    """Run all test modules and return (passed, total)."""
    test_files = find_test_modules()
    
    if not test_files:
        console.print("[yellow]No test modules found (test_*.py)[/yellow]")
        return 0, 0
    
    console.print(f"\n[bold blue]Running {len(test_files)} test modules[/bold blue]")
    
    # Create results table
    table = Table(title="Test Results")
    table.add_column("Module", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Duration", justify="right", style="blue")
    table.add_column("Details", style="dim")
    
    passed = 0
    total = len(test_files)
    
    for test_file in test_files:
        console.print(f"\n[cyan]Running {test_file.name}...[/cyan]")
        
        # Try running directly first
        success, duration, details = run_single_test(test_file)
        
        # If direct run failed, try pytest
        if not success and "Could not load module" not in details:
            console.print(f"[dim]  Direct run failed, trying pytest...[/dim]")
            success, duration, details = run_with_pytest(test_file)
        
        # Update results
        if success:
            passed += 1
            status = "[green]PASS[/green]"
        else:
            status = "[red]FAIL[/red]"
        
        duration_str = f"{duration:.2f}s"
        table.add_row(test_file.stem, status, duration_str, details)
    
    console.print(f"\n")
    console.print(table)
    
    return passed, total


def run_specific_test(module_name: str) -> bool:
    """Run a specific test module."""
    test_file = Path(f"{module_name}.py")
    
    if not test_file.exists():
        # Try with test_ prefix if not provided
        test_file = Path(f"test_{module_name}.py")
        
    if not test_file.exists():
        console.print(f"[red]Test module not found: {module_name}[/red]")
        console.print("[dim]Available modules:[/dim]")
        for f in find_test_modules():
            console.print(f"  {f.stem}")
        return False
    
    console.print(f"\n[bold blue]Running {test_file.name}[/bold blue]")
    
    success, duration, details = run_single_test(test_file)
    
    if success:
        console.print(f"[bold green]✓ {test_file.stem} passed ({duration:.2f}s)[/bold green]")
    else:
        console.print(f"[bold red]✗ {test_file.stem} failed ({duration:.2f}s)[/bold red]")
        console.print(f"[dim]{details}[/dim]")
    
    return success


def main() -> int:
    """Main entry point."""
    console.print("[bold]PDF Manipulator Test Runner[/bold]")
    
    # Check if we're in the tests directory
    current_path = Path('.').absolute()
    if current_path.name != 'tests':
        console.print(f"[yellow]Warning: Not running from tests/ directory[/yellow]")
        console.print(f"[dim]Current directory: {current_path}[/dim]")
        console.print(f"[dim]Expected directory name: 'tests', found: '{current_path.name}'[/dim]")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Run specific test
        module_name = sys.argv[1]
        success = run_specific_test(module_name)
        return 0 if success else 1
    else:
        # Run all tests
        passed, total = run_all_tests()
        
        console.print(f"\n[bold]Summary: {passed}/{total} test modules passed[/bold]")
        
        if passed == total:
            console.print("[bold green]All tests passed! ✓[/bold green]")
            return 0
        else:
            console.print(f"[bold red]{total - passed} test modules failed[/bold red]")
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
