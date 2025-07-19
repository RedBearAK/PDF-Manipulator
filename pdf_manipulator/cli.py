"""Command-line interface and argument parsing."""

import sys
import argparse
from pathlib import Path
from rich.console import Console

from pdf_manipulator._version import __version__
from pdf_manipulator.core.folder_operations import handle_folder_operations
from pdf_manipulator.core.scanner import scan_folder, scan_file
from pdf_manipulator.core.processor import process_single_file_operations
from pdf_manipulator.ui import display_pdf_table

console = Console()


epilog_for_argparse = """
Operations:
    --strip-first       Strip multi-page PDFs to first page only (alias for --extract-pages=1)
    --extract-pages     Extract specific pages (flexible syntax - see examples)
    --split-pages       Split multi-page PDFs into individual pages
    --optimize          Optimize PDF file sizes
    --analyze           Analyze PDFs to understand file sizes

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

Modes:
    --interactive       Process each PDF interactively (ask for each file)
    --batch             Process all matching PDFs without prompting

Examples:
    %(prog)s                           # Scan current directory
    %(prog)s /path/to/folder           # Scan specific folder
    %(prog)s file.pdf                  # Process single file
    %(prog)s --version                 # Show version information
    %(prog)s file.pdf --analyze        # Analyze single PDF
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
    operations.add_argument('--extract-pages', type=str, metavar='RANGE',
        help='Extract specific pages (e.g., "5", "3-7", "first 3", "last 2", "1-3,7,9-11", "::2")')
    operations.add_argument('--split-pages', action='store_true',
        help='Split multi-page PDFs into individual page files')
    operations.add_argument('--optimize', action='store_true',
        help='Optimize PDF file sizes')
    operations.add_argument('--analyze', action='store_true',
        help='Analyze PDFs to understand file sizes')

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

    # Safety options
    safety = parser.add_argument_group('safety options')
    safety.add_argument('--replace', action='store_true',
        help='Replace original files after processing (CAREFUL!)')

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

    operations_count = sum([bool(args.extract_pages), args.split_pages, args.optimize, args.analyze])
    if operations_count > 1:
        console.print("[red]Error: Please specify only one operation at a time[/red]")
        sys.exit(1)

    # Determine if path is file or folder
    is_file = args.path.is_file()
    is_folder = args.path.is_dir()

    if not is_file and not is_folder:
        console.print(f"[red]Error: {args.path} is not a valid file or directory[/red]")
        sys.exit(1)

    # Process based on input type - delegate to specialized functions
    if is_file:
        console.print(f"[blue]Processing file: {args.path.absolute()}[/blue]\n")
        pdf_files = scan_file(args.path)
        if not pdf_files:
            console.print("[red]Failed to read PDF file[/red]")
            sys.exit(1)
        display_pdf_table(pdf_files, title="PDF File Assessment")
        process_single_file_operations(args, pdf_files)
    else:
        console.print(f"[blue]Scanning {args.path.absolute()}...[/blue]\n")
        pdf_files = scan_folder(args.path)
        if not pdf_files:
            console.print("[yellow]No PDF files found![/yellow]")
            sys.exit(0)
        display_pdf_table(pdf_files)
        handle_folder_operations(args, pdf_files)


if __name__ == "__main__":
    main()
