"""
CLI Help Rendering Test Module
File: tests/test_cli_help.py

Pins a regression where bare '%' characters in the argparse epilog (from the
Phase 4 %-trimmer documentation) crashed --help entirely: argparse renders
epilog/help text through printf-style formatting, so '%ch' must be written
'%%ch' in source. Nothing else exercised --help, so the crash shipped.

Run: python tests/test_cli_help.py   (or pytest)
"""

import sys
import subprocess

from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console


console = Console()

PROJECT_ROOT = Path(__file__).parent.parent


def test_help_renders():
    """--help exits 0 and renders the full epilog including trimmer syntax."""
    console.print("\n[cyan]Testing --help rendering...[/cyan]")

    result = subprocess.run(
        [sys.executable, '-m', 'pdf_manipulator', '--help'],
        capture_output=True, text=True, timeout=60,
        cwd=str(PROJECT_ROOT),
        env={'PYTHONPATH': str(PROJECT_ROOT), 'PATH': '/usr/bin:/bin:/usr/local/bin'},
    )

    output = result.stdout + result.stderr

    checks = [
        (result.returncode == 0, "exit code 0"),
        ('usage:' in output, "usage line present"),
        ('Traceback' not in output, "no traceback in output"),
        # The escaped '%%ch' in source must render as '%ch' for the user
        ('%chN' in output, "end trimmer syntax renders as %chN"),
        ('%%' not in output, "no double-percent escapes leak into output"),
        # A sampling of flags across argument groups
        (all(flag in output for flag in (
            '--extract-pages', '--scrape-text', '--dump-text',
            '--scrape-pattern', '--filename-template', '--text-file',
            '--separate-files', '--respect-groups',
        )), "core flags present across argument groups"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def main():
    """Run the CLI help tests and report the score."""
    console.print("[bold blue]CLI Help Rendering Tests[/bold blue]")

    tests = [
        ("Help Renders", test_help_renders),
    ]

    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                console.print(f"[red]✗ {test_name} failed[/red]")
        except Exception as e:
            console.print(f"[red]✗ {test_name} crashed: {e}[/red]")

    console.print(f"\nScore: {passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    exit(main())


# End of file #
