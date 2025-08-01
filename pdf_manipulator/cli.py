"""Command-line interface and argument parsing with Ghostscript integration."""

import sys
import signal
import argparse

from pathlib import Path
from rich.console import Console

from pdf_manipulator.ui import display_pdf_table
from pdf_manipulator._version import __version__
from pdf_manipulator.core.scanner import scan_folder, scan_file
from pdf_manipulator.core.processor import process_single_file_operations
from pdf_manipulator.core.folder_operations import handle_folder_operations
from pdf_manipulator.core.malformation_checker import (
    check_and_fix_malformation_batch, check_and_fix_malformation_early
)


console = Console()


def setup_signal_handlers():
    """Setup graceful handling of Ctrl+C interruptions."""
    def signal_handler(sig, frame):
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    
    signal.signal(signal.SIGINT, signal_handler)


# Add this wrapper for all interactive prompts
def safe_prompt(prompt_func, *args, **kwargs):
    """Wrapper for Rich prompts that handles KeyboardInterrupt gracefully."""
    try:
        return prompt_func(*args, **kwargs)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)


epilog_for_argparse = """
Operations:
    --strip-first       Strip multi-page PDFs to first page only (alias for --extract-pages=1)
    --extract-pages     Extract specific pages (flexible syntax - see examples)
    --split-pages       Split multi-page PDFs into individual pages
    --optimize          Optimize PDF file sizes
    --analyze           Analyze PDFs to understand file sizes
    --gs-fix            Fix malformed PDFs using Ghostscript (deduplicates resources)
    --gs-batch-fix      Fix all malformed PDFs in folder using Ghostscript

Page Range Syntax for --extract-pages:
    Single page:        5
    Range:              3-7  or  3:7  or  3..7
    Open-ended:         3-   (page 3 to end)
                        -7   (start to page 7)
    First N pages:      first-3  or  "first 3"
    Last N pages:       last-2   or  "last 2"
    Multiple:           "1-3,7,9-11"  (use quotes)
    Step syntax:        ::2       (odd pages)
                        2::2      (even pages)
                        5:20:3    (every 3rd page from 5 to 20)

Extraction Options:
    --separate-files    Extract pages as separate documents (one file per page)
                        Default: extract as single document combining all pages
                        Interactive mode will ask unless this flag is specified

Ghostscript Options:
    --gs-quality        Quality setting: screen, ebook, printer, prepress, default
    --recursive         Process subdirectories recursively (for --gs-batch-fix)
    --dry-run           Show what would be done without actually doing it
    --replace-originals Replace original files with Ghostscript fixed versions

Modes:
    --interactive       Process each PDF interactively (ask for each file)
    --batch             Process all matching PDFs without prompting

Examples:
    %(prog)s                           # Scan current directory
    %(prog)s /path/to/folder           # Scan specific folder
    %(prog)s file.pdf                  # Process single file
    %(prog)s --version                 # Show version information
    %(prog)s file.pdf --analyze        # Analyze single PDF
    %(prog)s file.pdf --gs-fix         # Fix malformed PDF with Ghostscript
    %(prog)s --gs-batch-fix --dry-run  # See what PDFs would be fixed
    %(prog)s --gs-batch-fix --recursive --gs-quality=ebook  # Fix all PDFs recursively
    %(prog)s file.pdf --optimize       # Optimize single PDF
    %(prog)s --strip-first             # Interactive: ask which PDFs to strip
    %(prog)s --extract-pages=3-7       # Extract pages 3-7 as single document
    %(prog)s --extract-pages=3-7 --separate-files  # Extract pages 3-7 as separate files
    %(prog)s --extract-pages="1-3,7,9-11" --respect-groups  # Extract respecting groups
    %(prog)s --extract-pages="1-3,7"   # Extract pages 1-3 and 7 (asks: single or separate)
    %(prog)s --extract-pages="last 2"  # Extract last 2 pages
    %(prog)s --extract-pages=::2       # Extract odd pages
    %(prog)s --split-pages             # Interactive: ask which PDFs to split
    %(prog)s --strip-first --batch     # Strip ALL multi-page PDFs (careful!)
    %(prog)s file.pdf --split-pages    # Split single PDF into pages

Safety options:
    --replace         Replace/delete originals after processing (still asks!)
    --replace-originals  Replace originals with Ghostscript fixed versions (CAREFUL!)
    --strip-first --batch --replace    # Most dangerous: strips all and replaces

Note: No short arguments are provided to ensure clarity and prevent accidents.
"""


def main():
    """
    Main entry point for the PDF Manipulator.

    Design note: This tool intentionally uses only long arguments (--flag) 
    without short versions (-f) to ensure clarity and prevent accidental 
    misuse, especially for potentially destructive operations.
    """
    setup_signal_handlers()

    parser = argparse.ArgumentParser(
        description="PDF Manipulator - Assess and manipulate PDF pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog_for_argparse
    )

    parser.add_argument('path', type=Path, default=Path('.'), nargs='?',
        help='PDF file or folder containing PDF files (default: current directory)')

    # Version
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}',
        help='Show program version and exit')

    # Operations
    operations = parser.add_argument_group('operations')
    operations.add_argument('--strip-first', action='store_true',
        help='Strip multi-page PDFs to first page only (alias for --extract-pages=1)')
    operations.add_argument('--extract-pages', type=str, metavar='RANGE', nargs='?', const='all',
        help=('Extract specific pages (e.g., "5", "3-7", "all", "first 3", "last 2", "1-3,7,9-11", '
                '"::2"). [Defaults to "all" if no range specified.]'))
    operations.add_argument('--split-pages', action='store_true',
        help='Split multi-page PDFs into individual page files')
    operations.add_argument('--optimize', action='store_true',
        help='Optimize PDF file sizes')
    operations.add_argument('--analyze', action='store_true',
        help='Analyze PDFs to understand file sizes')

    # Ghostscript operations
    ghostscript = parser.add_argument_group('ghostscript operations')
    ghostscript.add_argument('--gs-fix', action='store_true',
        help='Fix malformed PDFs using Ghostscript (deduplicates resources)')
    ghostscript.add_argument('--gs-batch-fix', action='store_true',
        help='Fix all malformed PDFs in folder using Ghostscript')
    ghostscript.add_argument('--gs-quality', choices=['screen', 'ebook', 'printer', 'prepress', 'default'],
        default='default', help='Ghostscript quality setting (default: default)')

    # Extraction options
    extraction = parser.add_argument_group('extraction options')
    extraction.add_argument('--separate-files', action='store_true',
        help='Extract pages as separate documents (one file per page). Default: single document')
    extraction.add_argument('--respect-groups', action='store_true',
        help='Respect comma-separated groupings: ranges→multi-page files, individuals→single files')

    # Processing modes
    modes = parser.add_argument_group('processing modes')
    modes.add_argument('--interactive', action='store_true',
        help='Process PDFs interactively (default for operations)')
    modes.add_argument('--batch', action='store_true',
        help='Process all matching PDFs without individual prompts')
    modes.add_argument('--recursive', action='store_true',
        help='Process subdirectories recursively (for --gs-batch-fix)')
    modes.add_argument('--dry-run', action='store_true',
        help='Show what would be done without actually doing it')

    # Safety options
    safety = parser.add_argument_group('safety options')
    safety.add_argument('--replace', action='store_true',
        help='Replace original files after processing (CAREFUL!)')
    safety.add_argument('--replace-originals', action='store_true',
        help='Replace original files with Ghostscript fixed versions (CAREFUL!)')

    args = parser.parse_args()

    # Handle --strip-first as alias for --extract-pages=1
    if args.strip_first:
        if args.extract_pages:
            console.print("[red]Error: Cannot use both --strip-first and --extract-pages[/red]")
            sys.exit(1)
        args.extract_pages = "1"

    # Validate arguments
    if args.batch and args.interactive:
        console.print("[red]Error: Cannot use both --batch and --interactive[/red]")
        sys.exit(1)

    # Validate --separate-files usage
    if (args.separate_files or args.respect_groups) and not args.extract_pages:
        console.print("[red]Error: --separate-files and --respect-groups can only be used with --extract-pages[/red]")
        sys.exit(1)

    if args.separate_files and args.respect_groups:
        console.print("[red]Error: Cannot use both --separate-files and --respect-groups[/red]")
        sys.exit(1)

    # Validate Ghostscript arguments
    if args.gs_fix and args.gs_batch_fix:
        console.print("[red]Error: Cannot use both --gs-fix and --gs-batch-fix[/red]")
        sys.exit(1)

    if args.recursive and not args.gs_batch_fix:
        console.print("[red]Error: --recursive can only be used with --gs-batch-fix[/red]")
        sys.exit(1)

    if args.replace_originals and not (args.gs_fix or args.gs_batch_fix):
        console.print("[red]Error: --replace-originals can only be used with Ghostscript operations[/red]")
        sys.exit(1)

    if args.dry_run and not args.gs_batch_fix:
        console.print("[red]Error: --dry-run can only be used with --gs-batch-fix[/red]")
        sys.exit(1)

    # Count operations
    regular_operations = sum([bool(args.extract_pages), args.split_pages, args.optimize, args.analyze])
    ghostscript_operations = sum([args.gs_fix, args.gs_batch_fix])
    
    if regular_operations > 1:
        console.print("[red]Error: Please specify only one regular operation at a time[/red]")
        sys.exit(1)

    if ghostscript_operations > 1:
        console.print("[red]Error: Please specify only one Ghostscript operation at a time[/red]")
        sys.exit(1)

    if regular_operations > 0 and ghostscript_operations > 0:
        console.print("[red]Error: Cannot mix regular operations with Ghostscript operations[/red]")
        sys.exit(1)

    # Determine if path is file or folder
    is_file = args.path.is_file()
    is_folder = args.path.is_dir()

    if not is_file and not is_folder:
        console.print(f"[red]Error: {args.path} is not a valid file or directory[/red]")
        sys.exit(1)

    # Handle Ghostscript operations first
    if args.gs_fix or args.gs_batch_fix:
        handle_ghostscript_operations(args, is_file, is_folder)
        return

    # Process regular operations based on input type
    if is_file:
        console.print(f"[blue]Processing file: {args.path.absolute()}[/blue]\n")
        pdf_files = scan_file(args.path)
        if not pdf_files:
            console.print("[red]Failed to read PDF file[/red]")
            sys.exit(1)
        
        # NEW: Check for malformation immediately after scanning
        pdf_files = check_and_fix_malformation_early(pdf_files, args)
        
        display_pdf_table(pdf_files, title="PDF File Assessment")
        process_single_file_operations(args, pdf_files)
    else:
        console.print(f"[blue]Scanning {args.path.absolute()}...[/blue]\n")
        pdf_files = scan_folder(args.path)
        if not pdf_files:
            console.print("[yellow]No PDF files found![/yellow]")
            sys.exit(0)
        
        pdf_files = check_and_fix_malformation_batch(pdf_files, args)
        
        display_pdf_table(pdf_files)
        handle_folder_operations(args, pdf_files)


def handle_ghostscript_operations(args: argparse.Namespace, is_file: bool, is_folder: bool):
    """Handle Ghostscript-specific operations."""
    try:
        from pdf_manipulator.core.ghostscript import (
            check_ghostscript_availability, 
            fix_malformed_pdf, 
            safe_batch_fix_pdfs,
            detect_malformed_pdf
        )
    except ImportError:
        console.print("[red]Error: Ghostscript integration not available. "
                        "Make sure pdf_manipulator.core.ghostscript module exists.[/red]")
        sys.exit(1)

    # Check if Ghostscript is available
    if not check_ghostscript_availability():
        console.print("[red]Error: Ghostscript not found. Please install Ghostscript:[/red]")
        console.print("  macOS: brew install ghostscript")
        console.print("  Ubuntu: sudo apt-get install ghostscript")
        console.print("  Windows: Download from https://www.ghostscript.com/download/")
        sys.exit(1)

    if args.gs_fix:
        # Single file Ghostscript fix
        if not is_file:
            console.print("[red]Error: --gs-fix can only be used with a single PDF file[/red]")
            sys.exit(1)

        console.print(f"[blue]Ghostscript fix: {args.path.absolute()}[/blue]\n")
        
        # Check if file is malformed
        is_malformed, description = detect_malformed_pdf(args.path)
        if is_malformed:
            console.print(f"[yellow]Detected: {description}[/yellow]\n")
        else:
            console.print(f"[yellow]No obvious malformation detected, but proceeding anyway[/yellow]\n")

        try:
            output_path, new_size = fix_malformed_pdf(args.path, quality=args.gs_quality)
            
            if output_path and output_path.exists():
                if args.replace_originals:
                    from rich.prompt import Confirm
                    if Confirm.ask(f"Replace original file with {output_path.name}?", default=False):
                        backup_path = args.path.with_suffix('.pdf.backup')
                        args.path.rename(backup_path)
                        output_path.rename(args.path)
                        console.print(f"[green]✓ Replaced original (backup: {backup_path.name})[/green]")
                    else:
                        console.print("[yellow]Original file preserved[/yellow]")
            else:
                console.print("[red]Failed to create fixed PDF[/red]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]Error fixing PDF: {e}[/red]")
            sys.exit(1)

    elif args.gs_batch_fix:
        # Batch Ghostscript fix
        if not is_folder:
            console.print("[red]Error: --gs-batch-fix can only be used with a folder[/red]")
            sys.exit(1)

        console.print(f"[blue]Ghostscript batch fix: {args.path.absolute()}[/blue]\n")

        try:
            results = safe_batch_fix_pdfs(
                folder_path=args.path,
                recursive=args.recursive,
                dry_run=args.dry_run,
                preserve_originals=not args.replace_originals
            )

            if results:
                console.print(f"\n[blue]Summary:[/blue]")
                for file_path, message in results:
                    console.print(f"  {file_path.name}: {message}")
            else:
                console.print("[green]No files needed fixing or operation was cancelled[/green]")

        except Exception as e:
            console.print(f"[red]Error during batch fix: {e}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
