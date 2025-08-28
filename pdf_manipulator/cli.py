"""Command-line interface enhanced with scraper integration and compact pattern syntax."""

import sys
import signal
import argparse

from pathlib import Path
from rich.console import Console

from pdf_manipulator.ui import display_pdf_table
from pdf_manipulator._version import __version__
from pdf_manipulator.core.scanner import scan_folder, scan_file
from pdf_manipulator.core.processor import process_single_file_operations
from pdf_manipulator.core.operations import (
    extract_pages,
    extract_pages_separate,
    extract_pages_grouped
)
from pdf_manipulator.core.operation_context import OpCtx
from pdf_manipulator.core.folder_operations import (
    handle_folder_operations,
    _extract_pattern_and_template_args
)
from pdf_manipulator.core.malformation_utils import (
    check_and_fix_malformation_batch,
    check_and_fix_malformation_early
)
from pdf_manipulator.renamer import PatternProcessor
from pdf_manipulator.renamer.template_engine import validate_template_against_variables


console = Console()


def setup_signal_handlers():
    """Setup graceful handling of Ctrl+C interruptions."""
    def signal_handler(sig, frame):
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    
    signal.signal(signal.SIGINT, signal_handler)


# Enhanced epilog with compact pattern syntax documentation
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

Content-Based Selection:
    Text patterns:      contains[/i]:"text"     (case-insensitive with /i)
                        regex[/i]:"pattern"     (regular expressions)
                        line-starts[/i]:"text"  (lines starting with text)
    
    Page types:         type:text      (text-heavy pages)
                        type:image     (scanned/image pages)
                        type:mixed     (pages with both text and images)
                        type:empty     (blank or nearly blank pages)
    
    Size filtering:     size:<500KB    (pages under 500KB)
                        size:>1MB      (pages over 1MB)
                        size:>=2MB     (pages 2MB or larger)
                        size:<=100KB   (pages 100KB or smaller)

Boolean Expressions:
    AND logic:          "contains:'Invoice' & contains:'Total'"
    OR logic:           "type:text | type:mixed"
    NOT logic:          "all & !type:empty"  (all pages except empty ones)
    Complex:            "type:text & size:<500KB"  (small text pages)

Smart Filename Generation:
    Pattern Extraction:
        Compact Syntax: [var=]keyword:movements+extraction_type+count[-]
        
        Movements (1-99, max 2):
            u/d = up/down lines       r/l = right/left words
            Examples: u1 (up 1), r2 (right 2), u1r2 (up 1, right 2)
        
        Extraction Types:
            wd0-99 = words (0=until end of line)
            ln0-99 = lines (0=until end of document)  
            nb0-99 = numbers (0=until non-numeric)
            
        Flexibility: Add '-' suffix for format-tolerant extraction
        
        Examples:
            "Invoice Number:r1wd1"              # Right 1, get 1 word
            "company=Company Name:u1ln1"        # Up 1, get 1 line (named variable)
            "Total:d1r1nb1-"                    # Down 1, right 1, get 1 number (flexible)
            "Description:d2wd0"                 # Down 2, get words until end
    
    Template Syntax:
        Variables:      {variable_name}
        Fallbacks:      {variable_name|fallback_value}
        Built-ins:      {range}, {original_name}, {page_count}
        
        Examples:
            "{company}_{invoice}_pages{range}.pdf"
            "{vendor|Unknown}_{amount|NO-AMT}_{date}.pdf"

Extraction Options:
    --separate-files    Extract pages as separate documents (one file per page)
                        Default: extract as single document combining all pages
    --respect-groups    Respect comma-separated groupings in extraction
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
    
    Basic operations:
    %(prog)s file.pdf --analyze        # Analyze single PDF
    %(prog)s file.pdf --optimize       # Optimize single PDF
    %(prog)s --strip-first             # Interactive: ask which PDFs to strip
    %(prog)s --split-pages             # Interactive: ask which PDFs to split
    
    Smart filename extraction:
    %(prog)s invoice.pdf --extract-pages="1" \\
        --scrape-pattern="invoice=Invoice Number:r1wd1" \\
        --scrape-pattern="company=Company Name:u1ln1" \\
        --filename-template="{company}_{invoice}.pdf"
    
    Complex pattern extraction:
    %(prog)s statements/*.pdf --extract-pages="1-2" \\
        --scrape-pattern="account=Account Number:r2wd1-" \\
        --scrape-pattern="date=Statement Date:u1r1wd3-" \\
        --scrape-pattern="balance=Balance:d25r10nb1-" \\
        --filename-template="{account}_{date}_{balance}_pages{range}.pdf" \\
        --dry-run
    
    Content-based extraction:
    %(prog)s file.pdf --extract-pages="type:text"              # Extract text pages
    %(prog)s file.pdf --extract-pages="type:image"             # Extract image pages
    %(prog)s file.pdf --extract-pages="size:>1MB"              # Extract large pages
    %(prog)s file.pdf --extract-pages="contains:'Chapter'"     # Pages with "Chapter"
    
    Boolean combinations:
    %(prog)s file.pdf --extract-pages="type:text & size:<500KB"    # Small text pages
    %(prog)s file.pdf --extract-pages="type:image | type:mixed"    # Visual content
    %(prog)s file.pdf --extract-pages="all & !type:empty"          # All non-empty pages
    
    Standalone scraper mode:
    %(prog)s invoices/*.pdf --scrape-text \\
        --scrape-pattern="Invoice Number:r1wd1" \\
        --scrape-pattern="Amount:d1nb1" \\
        --output extracted_data.tsv
    
    Debugging mode:
    %(prog)s file.pdf --dump-text --output raw_text.txt

Enhanced Pattern Syntax (Phase 3):
    Base syntax:        [var=]keyword:movements+type+count[-][pg<pages>][mt<matches>]
    
    Movements:          u/d + 1-99: up/down lines
                        l/r + 1-99: left/right words
    
    Extraction Types:   wd + 0-99: words (0 = until end of line)
                        ln + 0-99: lines (0 = until end of document)  
                        nb + 0-99: numbers only (extracts numeric data from mixed content)
    
    Page Specs (NEW):   pg3: page 3 only
                        pg2-4: pages 2 through 4
                        pg3-: page 3 to end
                        pg-2: last 2 pages
                        pg0: all pages (debug mode)
    
    Match Specs (NEW):  mt2: second match of keyword
                        mt1-3: matches 1 through 3
                        mt2-: match 2 to end
                        mt-2: last 2 matches
                        mt0: all matches (debug mode)

Phase 3 Pattern Examples:
    Basic patterns:
    %(prog)s invoice.pdf --extract-pages="1" \\
        --scrape-pattern="Invoice Number:r1wd1" \\
        --scrape-pattern="company=Company Name:u1ln1" \\
        --filename-template="{company}_{invoice_number}.pdf"
    
    Enhanced multi-page patterns:
    %(prog)s statements/*.pdf --extract-pages="1-3" \\
        --scrape-pattern="account=Account Number:r2wd1pg2" \\
        --scrape-pattern="date=Statement Date:u1r1wd3mt2" \\
        --scrape-pattern="balance=Balance:d25r10nb1-pg-2" \\
        --filename-template="{account}_{date}_{balance}_pages{range}.pdf" \\
        --dry-run
    
    Number extraction examples:
    %(prog)s invoices/*.pdf --extract-pages="all" \\
        --scrape-pattern="amount=Total:r1nb1" \\          # Extracts "1250" from "Total: $1,250.00"
        --scrape-pattern="tax=Tax:r1nb1-" \\              # Extracts all numbers until non-numeric
        --filename-template="{amount}_{tax}_invoice.pdf"

Safety options:
    --no-auto-fix     Disable automatic malformation fixing in batch mode
    --replace         Replace/delete originals after processing (still asks!)
    --replace-originals  Replace originals with Ghostscript fixed versions (CAREFUL!)

Note: No short arguments are provided to ensure clarity and prevent accidents.
      Use quotes around complex expressions with spaces or special characters.
"""


def validate_scraper_arguments(args: argparse.Namespace) -> tuple[bool, str]:
    """Validate scraper-related arguments for consistency and syntax."""
    
    # Check mutually exclusive pattern sources
    if args.scrape_pattern and args.scrape_patterns_file:
        return False, "Cannot use both --scrape-pattern and --scrape-patterns-file"
    
    # Pattern arguments require --extract-pages (except in standalone scraper mode)
    pattern_args_used = args.scrape_pattern or args.scrape_patterns_file or args.filename_template
    if pattern_args_used and not args.extract_pages and not args.scrape_text:
        return False, "Pattern and template arguments require --extract-pages (or --scrape-text for standalone mode)"
    
    # Template requires patterns
    if args.filename_template and not (args.scrape_pattern or args.scrape_patterns_file):
        return False, "--filename-template requires pattern arguments"
    
    # Validate pattern syntax early
    if args.scrape_pattern:
        try:
            processor = PatternProcessor()
            processor.validate_pattern_list(args.scrape_pattern)
        except Exception as e:
            return False, f"Invalid pattern syntax: {e}"
    
    # Validate template syntax
    if args.filename_template:
        from pdf_manipulator.renamer.template_engine import TemplateEngine
        engine = TemplateEngine()
        is_valid, error = engine.validate_template(args.filename_template)
        if not is_valid:
            return False, f"Invalid template syntax: {error}"
    
    # Validate source page
    if args.pattern_source_page < 1:
        return False, "Pattern source page must be >= 1"
    
    return True, ""


def main():
    """
    Main entry point for the PDF Manipulator with scraper integration.

    Design note: This tool intentionally uses only long arguments (--flag) 
    without short versions (-f) to ensure clarity and prevent accidental 
    misuse, especially for potentially destructive operations.
    """
    setup_signal_handlers()

    parser = argparse.ArgumentParser(
        prog="pdf-manipulator",
        description="PDF Manipulator - Assess and manipulate PDF pages with intelligent naming",
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
    operations.add_argument('--analyze-detailed', action='store_true',
        help='Detailed page-by-page analysis to help craft boolean expressions')

    # Scraper operations (standalone modes)
    scraper_ops = parser.add_argument_group('scraper operations')
    scraper_ops.add_argument('--scrape-text', action='store_true',
        help='Extract text content using scraper patterns (standalone scraper mode)')
    scraper_ops.add_argument('--dump-text', action='store_true',
        help='Extract and display raw text from PDFs (debugging mode)')

    # Ghostscript operations
    ghostscript = parser.add_argument_group('ghostscript operations')
    ghostscript.add_argument('--gs-fix', action='store_true',
        help='Fix malformed PDFs using Ghostscript (deduplicates resources)')
    ghostscript.add_argument('--gs-batch-fix', action='store_true',
        help='Fix all malformed PDFs in folder using Ghostscript')
    ghostscript.add_argument('--gs-quality', choices=['screen', 'ebook', 'printer', 'prepress', 'default'],
        default='default', help='Ghostscript quality setting (default: default)')

    # Pattern extraction (NEW)
    patterns = parser.add_argument_group('pattern extraction')
    patterns.add_argument('--scrape-pattern', action='append', metavar='PATTERN',
        help=('Content extraction pattern with enhanced Phase 3 syntax: '
            '"[var=]keyword:movements+type+count[-][pg<pages>][mt<matches>]" '
            '(can be used multiple times). Examples: "Invoice Number:r1wd1", '
            '"company=Company:u1ln1pg2", "total=Total:r1nb1mt2"'))
    patterns.add_argument('--scrape-patterns-file', metavar='FILE',
        help='File containing extraction patterns, one per line')
    patterns.add_argument('--pattern-source-page', type=int, default=1, metavar='N',
        help='Page number to extract patterns from (default: 1, overridden by pg specs)')

    # NEW: Smart filename options
    naming = parser.add_argument_group('intelligent naming')
    naming.add_argument('--filename-template', metavar='TEMPLATE',
        help=('Template for naming files: "{variable|fallback}_pages{range}.pdf". '
            'Built-in variables: {range}, {original_name}, {page_count}. '
            'Works with Phase 3 enhanced pattern extraction.'))

    # NEW: Enhanced naming options
    naming.add_argument('--smart-names', action='store_true',
        help='Use smart filename generation to avoid unwieldy names for complex extractions')
    naming.add_argument('--name-prefix', metavar='PREFIX',
        help='Custom prefix for output filenames (instead of timestamp)')
    naming.add_argument('--no-timestamp', action='store_true',
        help='Disable timestamp prefixes in generated filenames')

    # Extraction options
    extraction = parser.add_argument_group('extraction options')
    extraction.add_argument('--separate-files', action='store_true',
        help='Extract pages as separate documents (one file per page). Default: single document')
    extraction.add_argument('--respect-groups', action='store_true',
        help='Respect comma-separated groupings: ranges→multi-page files, individuals→single files')
    extraction.add_argument('--dedup', 
        choices=['none', 'strict', 'groups', 'warn', 'fail'], 
        metavar='STRATEGY',
        help=('Deduplication strategy: none (disable), strict (no dupes in entire set), '
            'groups (dedupe within groups), warn (show warning), fail (error on dupes)'))
    extraction.add_argument('--conflicts', 
        choices=['ask', 'overwrite', 'skip', 'rename', 'fail'],
        default='ask',
        metavar='STRATEGY', 
        help=('File conflict resolution: ask (interactive), overwrite (replace existing), '
            'skip (keep existing), rename (add suffix), fail (stop on conflict)'))

    # Group filtering and boundary options
    filtering = parser.add_argument_group('group filtering and boundaries')
    filtering.add_argument('--filter-matches', type=str, metavar='CRITERIA',
        help=('Filter extracted page groups by index (e.g., "1,3,4") or content criteria '
            '(e.g., "contains:\'Important\'", "type:text & !37-96"). '
            'Only matching groups will be kept.'))
    filtering.add_argument('--group-start', type=str, metavar='PATTERN',
        help='Start new groups at pages matching pattern (e.g., "contains:\'Chapter\'", "type:text")')
    filtering.add_argument('--group-end', type=str, metavar='PATTERN', 
        help='End current groups at pages matching pattern (e.g., "contains:\'Summary\'", "size:>1MB")')

    # Output options (for scraper modes)
    output = parser.add_argument_group('output options')
    output.add_argument('--output', '-o', metavar='FILE',
        help='Output file for scraper modes (TSV for --scrape-text, text for --dump-text)')

    # Processing modes
    modes = parser.add_argument_group('processing modes')
    # modes.add_argument('--interactive', action='store_true',
    #     help='Process PDFs interactively (default for operations)')
    modes.add_argument('--batch', action='store_true',
        help='Process all matching PDFs without individual prompts')
    modes.add_argument('--recursive', action='store_true',
        help='Process subdirectories recursively (for --gs-batch-fix)')
    modes.add_argument('--dry-run', action='store_true',
        help='Show what would be done without actually doing it')

    # File operation (output) previewing, conflict resolution
    preview = parser.add_argument_group('preview and conflict resolution')
    preview.add_argument('--preview', action='store_true',
        help='Show file operation preview (what files created/overwritten) before executing')

    # Safety options
    safety = parser.add_argument_group('safety options')
    safety.add_argument('--no-auto-fix', action='store_true',
        help='Disable automatic malformation fixing in batch mode')
    safety.add_argument('--replace', action='store_true',
        help='Replace original files after processing (CAREFUL!)')
    safety.add_argument('--replace-originals', action='store_true',
        help='Replace original files with Ghostscript fixed versions (CAREFUL!)')

    args = parser.parse_args()

    # Set up OperationContext immediately after argument parsing
    OpCtx.reset()           # Clear any previous state
    OpCtx.set_args(args)    # Set the arguments cache, they won't change

    # Handle --strip-first as alias for --extract-pages=1
    if args.strip_first:
        if args.extract_pages:
            console.print("[red]Error: Cannot use both --strip-first and --extract-pages[/red]")
            sys.exit(1)
        args.extract_pages = "1"

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

    if args.dry_run and not (args.gs_batch_fix or args.extract_pages or args.scrape_text):
        console.print("[red]Error: --dry-run requires an operation that supports it[/red]")
        sys.exit(1)

    # Validate group filtering arguments
    if args.filter_matches and not args.extract_pages:
        console.print("[red]Error: --filter-matches can only be used with --extract-pages[/red]")
        sys.exit(1)

    if (args.group_start or args.group_end) and not args.extract_pages:
        console.print("[red]Error: --group-start and --group-end can only be used with --extract-pages[/red]")
        sys.exit(1)

    # Validate filter syntax early
    if args.filter_matches:
        from pdf_manipulator.core.page_range.group_filtering import validate_filter_syntax
        is_valid, error_msg = validate_filter_syntax(args.filter_matches)
        if not is_valid:
            console.print(f"[red]Error: Invalid filter syntax: {error_msg}[/red]")
            sys.exit(1)

    # NEW: Validate scraper arguments
    is_valid, error_msg = validate_scraper_arguments(args)
    if not is_valid:
        console.print(f"[red]Error: {error_msg}[/red]")
        sys.exit(1)

    # Count operations
    regular_operations = sum([
        bool(args.extract_pages),
        args.split_pages,
        args.optimize,
        args.analyze,
        args.analyze_detailed
        ])
    ghostscript_operations = sum([args.gs_fix, args.gs_batch_fix])
    scraper_operations = sum([args.scrape_text, args.dump_text])
    
    if regular_operations > 1:
        console.print("[red]Error: Please specify only one regular operation at a time[/red]")
        sys.exit(1)

    if ghostscript_operations > 1:
        console.print("[red]Error: Please specify only one Ghostscript operation at a time[/red]")
        sys.exit(1)

    if scraper_operations > 1:
        console.print("[red]Error: Please specify only one scraper operation at a time[/red]")
        sys.exit(1)

    if sum([regular_operations > 0, ghostscript_operations > 0, scraper_operations > 0]) > 1:
        console.print("[red]Error: Cannot mix different operation types[/red]")
        sys.exit(1)

    # Determine if path is file or folder
    is_file = args.path.is_file()
    is_folder = args.path.is_dir()

    if not is_file and not is_folder:
        console.print(f"[red]Error: {args.path} is not a valid file or directory[/red]")
        sys.exit(1)

    # Handle different operation types
    if args.gs_fix or args.gs_batch_fix:
        handle_ghostscript_operations(args, is_file, is_folder)
        return
    elif args.scrape_text or args.dump_text:
        handle_scraper_operations(args, is_file, is_folder)
        return

    # Process regular operations based on input type
    if is_file:
        console.print(f"[blue]Processing file: {args.path.absolute()}[/blue]\n")
        pdf_files = scan_file(args.path)
        if not pdf_files:
            console.print("[red]Failed to read PDF file[/red]")
            sys.exit(1)
        
        # Check for malformation immediately after scanning
        pdf_files = check_and_fix_malformation_early(pdf_files, args)
        
        display_pdf_table(pdf_files, title="PDF File Assessment")

        # Extract PDF info and set current PDF context globally
        pdf_path, page_count, file_size = pdf_files[0]
        OpCtx.set_current_pdf(pdf_path, page_count)

        process_single_file_operations(args, pdf_files)
    else:
        console.print(f"[blue]Scanning {args.path.absolute()}...[/blue]\n")
        pdf_files = scan_folder(args.path)
        if not pdf_files:
            console.print("[yellow]No PDF files found![/yellow]")
            sys.exit(0)
        
        pdf_files = check_and_fix_malformation_batch(pdf_files, "scanning")
        
        display_pdf_table(pdf_files)
        handle_folder_operations(args, pdf_files)


def is_interactive_mode(args) -> bool:
    """Determine if we're in interactive mode (default unless --batch specified)."""
    return not getattr(args, 'batch', False)


def get_conflict_strategy(args) -> str:
    """Get conflict resolution strategy, adjusting for batch mode."""
    strategy = getattr(args, 'conflicts', 'ask')
    # In batch mode, convert 'ask' to 'rename' since we can't prompt
    if getattr(args, 'batch', False) and strategy == 'ask':
        return 'rename'
    return strategy


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


def handle_scraper_operations(args: argparse.Namespace, is_file: bool, is_folder: bool):
    """Handle standalone scraper operations."""
    console.print("[blue]Scraper operations not yet implemented in Phase 1[/blue]")
    console.print("[dim]This will integrate the existing scraper CLI functionality[/dim]")
    # TODO: Implement in Phase 2
    sys.exit(0)


def extract_enhanced_args(args) -> dict:
    """
    Extract enhanced arguments for PDF operations.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Dictionary with processed enhanced arguments
    """
    # Determine deduplication strategy
    dedup_strategy = determine_default_dedup_strategy(args)
    
    # Extract base conflict resolution strategy  
    base_conflict_strategy = getattr(args, 'conflicts', 'ask')
    
    # CRITICAL: Apply batch mode safety conversion
    is_batch = getattr(args, 'batch', False)
    if is_batch and base_conflict_strategy == 'ask':
        # Can't ask in batch mode - convert to safe rename strategy
        conflict_strategy = 'rename'
        console.print("[cyan]Batch mode: converting 'ask' conflict strategy to 'rename' for safety[/cyan]")
    else:
        # Keep the specified strategy for interactive mode or explicit batch strategies
        conflict_strategy = base_conflict_strategy
    
    # FLATTENED STRUCTURE - no nested dictionaries
    return {
        # Core behavior flags
        'interactive': not is_batch,
        'preview': getattr(args, 'preview', False),
        
        # Strategy settings
        'dedup_strategy': dedup_strategy,
        'conflict_strategy': conflict_strategy,  # Now with batch mode conversion
        
        # Naming options (flattened)
        'smart_names': getattr(args, 'smart_names', False),
        'name_prefix': getattr(args, 'name_prefix', None),
        'no_timestamp': getattr(args, 'no_timestamp', False),
        'template': getattr(args, 'filename_template', None)
    }


def determine_default_dedup_strategy(args) -> str:
    """
    Determine the default deduplication strategy based on output mode.
    """
    if hasattr(args, 'dedup') and args.dedup:
        return args.dedup
    elif hasattr(args, 'respect_groups') and args.respect_groups:
        return 'groups'  # Allow dupes between groups
    elif hasattr(args, 'separate_files') and args.separate_files:
        return 'strict'  # No duplicate page files
    else:
        return 'strict'  # Single file - no duplicate pages


def process_extraction_with_enhancements(args, pdf_path: Path, total_pages: int) -> bool:
    """
    Process extraction with all enhancements applied.
    
    Args:
        args: Parsed command line arguments
        pdf_path: PDF file to process
        total_pages: Number of pages in PDF
        
    Returns:
        True if extraction succeeded, False otherwise
    """
    from pdf_manipulator.core.parser import parse_page_range_from_args
    from pdf_manipulator.core.deduplication import detect_duplicates
    from pdf_manipulator.core.file_conflicts import resolve_file_conflicts, preview_file_operations
    from pdf_manipulator.core.smart_filenames import generate_smart_description
    from pdf_manipulator.ui import decide_extraction_mode
    
    # Extract enhanced arguments
    enhanced_args = extract_enhanced_args(args)
    
    try:
        # Parse page range and detect issues
        pages_to_extract, desc, groups = parse_page_range_from_args(args, total_pages, pdf_path)
        
        # Detect duplicates early
        duplicate_info = detect_duplicates(groups)
        
        # Interactive confirmation if requested
        if enhanced_args['interactive']:
            if duplicate_info['has_duplicates']:
                from pdf_manipulator.ui_enhanced import confirm_deduplication_strategy
                enhanced_args['dedup_strategy'] = confirm_deduplication_strategy(
                    duplicate_info, 
                    'grouped' if args.respect_groups else 'single',
                    enhanced_args['dedup_strategy']
                )
        
        # Generate smart description if enabled
        if enhanced_args['smart_names']:
            page_args = [args.extract_pages] if hasattr(args, 'extract_pages') else []
            smart_desc = generate_smart_description(page_args, len(pages_to_extract))
            desc = smart_desc
        
        # Determine extraction mode
        if args.respect_groups:
            extraction_mode = 'grouped'
        elif args.separate_files:
            extraction_mode = 'separate'
        elif enhanced_args['interactive']:
            extraction_mode = decide_extraction_mode(pages_to_extract, groups, True)
        else:
            extraction_mode = 'single'
        
        # Plan output files
        planned_paths = plan_output_files(
            pdf_path, desc, extraction_mode, groups, enhanced_args['naming']
        )
        
        # Resolve file conflicts
        resolved_paths, skipped_paths = resolve_file_conflicts(
            planned_paths, 
            enhanced_args['conflict_strategy'],
            enhanced_args['interactive']
        )
        
        # Show preview if requested
        if enhanced_args['preview']:
            preview_file_operations(planned_paths, resolved_paths, skipped_paths)
            from rich.prompt import Confirm
            if not Confirm.ask("Proceed with extraction?", default=True):
                console.print("[yellow]Extraction cancelled by user[/yellow]")
                return False
        
        # Perform extraction with resolved paths
        success = perform_extraction(
            pdf_path, args, extraction_mode, resolved_paths, 
            enhanced_args['dedup_strategy']
        )
        
        return success
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return False


def plan_output_files(pdf_path: Path, desc: str, mode: str, groups: list, naming_options: dict) -> list[Path]:
    """
    Plan output file paths based on extraction parameters.
    """
    from pdf_manipulator.core.smart_filenames import generate_extraction_filename
    
    if mode == 'single':
        # Single output file
        output_path = generate_extraction_filename(
            pdf_path, desc, mode,
            timestamp=not naming_options['no_timestamp'],
            custom_prefix=naming_options['name_prefix']
        )
        return [output_path]
    
    elif mode == 'separate':
        # One file per page
        paths = []
        for group in groups:
            if hasattr(group, 'pages') and group.pages:
                for page in group.pages:
                    page_desc = f"page{page}"
                    output_path = generate_extraction_filename(
                        pdf_path, page_desc, mode,
                        timestamp=not naming_options['no_timestamp'],
                        custom_prefix=naming_options['name_prefix']
                    )
                    paths.append(output_path)
        return paths
    
    elif mode == 'grouped':
        # One file per group
        paths = []
        for group_idx, group in enumerate(groups):
            if hasattr(group, 'pages') and group.pages:
                group_desc = getattr(group, 'original_spec', f"group{group_idx+1}")
                output_path = generate_extraction_filename(
                    pdf_path, group_desc, mode,
                    timestamp=not naming_options['no_timestamp'],
                    custom_prefix=naming_options['name_prefix']
                )
                paths.append(output_path)
        return paths
    
    return []


def perform_extraction(pdf_path: Path, args, mode: str) -> bool:
    """
    Perform the actual extraction with specified parameters.
    """
    
    # Extract pattern and template args
    patterns, template, source_page = _extract_pattern_and_template_args(args)
    dry_run = getattr(args, 'dry_run', False)
    
    # Extract enhanced args
    enhanced_args = extract_enhanced_args(args)
    
    try:
        if mode == 'single':
            output_path, file_size = extract_pages(
                pdf_path=pdf_path,
                page_range=args.extract_pages,
                patterns=patterns,
                template=template,
                source_page=source_page,
                dry_run=dry_run,
                dedup_strategy=enhanced_args['dedup_strategy'],      # Use from enhanced_args
                use_timestamp=getattr(args, 'timestamp', False),
                custom_prefix=getattr(args, 'name_prefix', None),
                conflict_strategy=enhanced_args['conflict_strategy']  # ADD THIS LINE
            )

            if output_path:
                console.print(f"[green]✓ Created: {output_path.name} ({file_size:.2f} MB)[/green]")
                return True
                

        elif mode == 'separate':
            output_files = extract_pages_separate(
                pdf_path=pdf_path, 
                page_range=args.extract_pages, 
                patterns=patterns, 
                template=template, 
                source_page=source_page, 
                dry_run=dry_run, 
                dedup_strategy=enhanced_args['dedup_strategy'],      # Use from enhanced_args
                use_timestamp=getattr(args, 'timestamp', False),
                custom_prefix=getattr(args, 'name_prefix', None),
                conflict_strategy=enhanced_args['conflict_strategy']  # ADD THIS LINE
            )

            if output_files:
                console.print(f"[green]✓ Created {len(output_files)} separate files[/green]")
                return True
                

        elif mode == 'grouped':
            output_files = extract_pages_grouped(
                pdf_path=pdf_path, 
                page_range=args.extract_pages, 
                patterns=patterns, 
                template=template, 
                source_page=source_page, 
                dry_run=dry_run, 
                dedup_strategy=enhanced_args['dedup_strategy'],      # Use from enhanced_args
                use_timestamp=getattr(args, 'timestamp', False),
                custom_prefix=getattr(args, 'name_prefix', None),
                conflict_strategy=enhanced_args['conflict_strategy']  # ADD THIS LINE
            )

            if output_files:
                console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
                return True
        
        return False
        
    except Exception as e:
        console.print(f"[red]Extraction failed: {e}[/red]")
        return False


if __name__ == "__main__":
    main()

# End of file #
