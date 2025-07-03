#!/usr/bin/env python3

__version__ = "20250703"

"""
PDF Manipulator - A CLI tool to assess PDFs and manipulate pages
Uses pypdf for PDF manipulation

Design philosophy:
- No short arguments: All options use descriptive long names for clarity
- Explicit is better than implicit: No ambiguous single-letter flags
- Safety first: Destructive operations require explicit flags and confirmations
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Tuple, Union, Set
from pypdf import PdfReader, PdfWriter
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt

console = Console()


def parse_page_range(range_str: str, total_pages: int) -> Tuple[Set[int], str]:
    """
    Parse page range string and return set of page numbers (1-indexed) and a description.

    Supports:
    - Single page: "5"
    - Range: "3-7" or "3:7" or "3..7"
    - Open-ended: "3-" (page 3 to end) or "-7" (start to page 7)
    - First N: "first 3" or "first-3"
    - Last N: "last 2" or "last-2"
    - Multiple: "1-3,7,9-11"
    - Slicing: "::2" (odd pages), "2::2" (even pages), "5:10:2" (every 2nd from 5 to 10)

    Returns: (set of page numbers, description for filename)
    """
    pages = set()
    descriptions = []

    # Remove quotes and extra spaces
    range_str = range_str.strip().strip('"\'')

    # Handle comma-separated ranges
    parts = [p.strip() for p in range_str.split(',')]

    for part in parts:
        try:
            # Check for slicing syntax (contains :: or single : with 3 parts)
            if '::' in part or (part.count(':') == 2):
                # Parse slicing: start:stop:step
                slice_parts = part.split(':')
                start = int(slice_parts[0]) if slice_parts[0] else 1
                stop = int(slice_parts[1]) if slice_parts[1] else total_pages
                step = int(slice_parts[2]) if len(slice_parts) > 2 and slice_parts[2] else 1

                # Make stop inclusive for user-friendliness
                for p in range(start, stop + 1, step):
                    if 1 <= p <= total_pages:
                        pages.add(p)

                if not slice_parts[0] and not slice_parts[1]:
                    if step == 2:
                        descriptions.append("odd" if start == 1 else "even")
                    else:
                        descriptions.append(f"every-{step}")
                else:
                    descriptions.append(f"{start}-{stop}-step{step}")

            # Check for "first N" syntax
            elif part.lower().startswith('first'):
                match = re.match(r'first[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(1, min(n + 1, total_pages + 1)):
                        pages.add(p)
                    descriptions.append(f"first{n}")

            # Check for "last N" syntax
            elif part.lower().startswith('last'):
                match = re.match(r'last[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(max(1, total_pages - n + 1), total_pages + 1):
                        pages.add(p)
                    descriptions.append(f"last{n}")

            # Check for range syntax
            elif any(sep in part for sep in ['-', ':', '..']):
                # Find the separator
                sep = next(s for s in ['-', ':', '..'] if s in part)
                if sep == '..':
                    start_str, end_str = part.split('..')
                else:
                    # Be careful with negative numbers
                    parts = part.split(sep, 1)
                    start_str = parts[0]
                    end_str = parts[1] if len(parts) > 1 else ''

                # Parse start and end
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else total_pages

                if start > end:
                    raise ValueError(f"Invalid range: {start} > {end}")

                for p in range(start, end + 1):
                    if 1 <= p <= total_pages:
                        pages.add(p)

                descriptions.append(f"{start}-{end}")

            # Single page number
            else:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    pages.add(page_num)
                    descriptions.append(str(page_num))
                else:
                    raise ValueError(f"Page {page_num} out of range (1-{total_pages})")

        except ValueError as e:
            raise ValueError(f"Invalid page range '{part}': {str(e)}")

    if not pages:
        raise ValueError("No valid pages in range")

    # Create description for filename
    if len(descriptions) == 1:
        desc = descriptions[0]
    else:
        # Simplify if multiple parts
        desc = ",".join(descriptions)
        if len(desc) > 20:  # Keep filename reasonable
            desc = f"{min(pages)}-{max(pages)}-selected"

    # Format description
    if ',' in desc:
        desc = f"pages{desc}"
    elif any(d in desc for d in ['odd', 'even', 'every', 'first', 'last']):
        desc = desc  # Keep as is
    elif '-' in desc and not desc.startswith('pages'):
        desc = f"pages{desc}"
    else:
        desc = f"page{desc}"

    return pages, desc


def extract_pages(pdf_path: Path, page_range: str) -> Tuple[Path, float]:
    """Extract specified pages from PDF."""
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse the page range
        pages_to_extract, range_desc = parse_page_range(page_range, total_pages)

        # Sort pages for output
        sorted_pages = sorted(pages_to_extract)

        # Create output filename
        output_path = pdf_path.parent / f"{pdf_path.stem}_{range_desc}.pdf"

        # Create writer and add pages
        writer = PdfWriter()
        for page_num in sorted_pages:
            writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed

        # Copy metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        # Write the output
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        # Get new file size
        new_size = output_path.stat().st_size / (1024 * 1024)

        console.print(f"[green]✓ Extracted {len(sorted_pages)} pages: {', '.join(map(str, sorted_pages))}[/green]")

        return output_path, new_size

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return None, 0
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        return None, 0


def get_pdf_info(pdf_path: Path) -> Tuple[int, float]:
    """Get page count and file size for a PDF."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            page_count = len(reader.pages)

        file_size = pdf_path.stat().st_size / (1024 * 1024)  # Convert to MB
        return page_count, file_size
    except Exception as e:
        console.print(f"[red]Error reading {pdf_path.name}: {e}[/red]")
        return 0, 0


def scan_folder(folder_path: Path) -> List[Tuple[Path, int, float]]:
    """Scan folder for PDF files and return their info."""
    pdf_files = []

    for pdf_path in folder_path.glob("*.pdf"):
        # Skip processing hidden files ".", including macOS metadata files "._"
        if pdf_path.name.startswith("."):
            continue
        page_count, file_size = get_pdf_info(pdf_path)
        if page_count > 0:
            pdf_files.append((pdf_path, page_count, file_size))

    return sorted(pdf_files, key=lambda x: x[0].name)


def scan_file(file_path: Path) -> List[Tuple[Path, int, float]]:
    """Get info for a single PDF file."""
    if not file_path.exists():
        console.print(f"[red]Error: File {file_path} does not exist[/red]")
        return []

    if not file_path.suffix.lower() == '.pdf':
        console.print(f"[red]Error: {file_path} is not a PDF file[/red]")
        return []

    page_count, file_size = get_pdf_info(file_path)
    if page_count > 0:
        return [(file_path, page_count, file_size)]
    return []


def analyze_pdf(pdf_path: Path) -> None:
    """Analyze PDF content to understand file size."""
    try:
        reader = PdfReader(pdf_path)
        total_images = 0

        console.print(f"\n[cyan]Analysis of {pdf_path.name}:[/cyan]")
        console.print(f"Pages: {len(reader.pages)}")
        console.print(f"File size: {pdf_path.stat().st_size / (1024 * 1024):.2f} MB")
        console.print(f"Average per page: {pdf_path.stat().st_size / (1024 * len(reader.pages)):.0f} KB")

        # Check for images in each page
        for i, page in enumerate(reader.pages):
            if '/XObject' in page.get('/Resources', {}):
                xobjects = page['/Resources']['/XObject'].get_object()
                images = [x for x in xobjects if xobjects[x].get('/Subtype') == '/Image']
                if images:
                    console.print(f"  Page {i+1}: {len(images)} image(s)")
                    total_images += len(images)

        if total_images > 0:
            console.print(f"[yellow]Total images found: {total_images}[/yellow]")
            console.print("[dim]Note: Large file sizes often indicate high-resolution scanned images[/dim]")

        # Check if it's likely a scanned PDF
        text_found = False
        for page in reader.pages[:1]:  # Just check first page
            text = page.extract_text().strip()
            if len(text) > 50:  # Arbitrary threshold
                text_found = True
                break

        if not text_found and total_images > 0:
            console.print("[yellow]This appears to be a scanned PDF (images, not text)[/yellow]")

    except Exception as e:
        console.print(f"[red]Error analyzing {pdf_path.name}: {e}[/red]")


def display_pdf_table(pdf_files: List[Tuple[Path, int, float]], title: str = "PDF Files Assessment"):
    """Display PDF files in a formatted table."""
    table = Table(title=title)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Pages", justify="right", style="magenta")
    table.add_column("Size (MB)", justify="right", style="green")
    table.add_column("Status", style="yellow")

    for pdf_path, page_count, file_size in pdf_files:
        status = "⚠️  Multi-page" if page_count > 1 else "✓ Single page"
        table.add_row(
            pdf_path.name,
            str(page_count),
            f"{file_size:.2f}",
            status
        )

    console.print(table)


def strip_to_first_page(pdf_path: Path) -> Tuple[Path, float]:
    """Strip PDF to first page only."""
    output_path = pdf_path.parent / f"{pdf_path.stem}_page1.pdf"

    try:
        # Read the source PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        # Add just the first page
        writer.add_page(reader.pages[0])

        # Copy metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        # Write the output
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        # Get new file size
        new_size = output_path.stat().st_size / (1024 * 1024)
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
        return None, 0


def split_to_pages(pdf_path: Path) -> List[Tuple[Path, float]]:
    """Split PDF into individual pages."""
    output_files = []

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Determine zero padding for filenames
        padding = len(str(total_pages))

        for i, page in enumerate(reader.pages):
            page_num = str(i + 1).zfill(padding)
            output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num}.pdf"

            writer = PdfWriter()
            writer.add_page(page)

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # Write the page
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            # Get file size
            file_size = output_path.stat().st_size / (1024 * 1024)
            output_files.append((output_path, file_size))

        return output_files

    except Exception as e:
        console.print(f"[red]Error splitting {pdf_path.name}: {e}[/red]")
        return []


def optimize_pdf(pdf_path: Path) -> Tuple[Path, float]:
    """Compress PDF by removing duplicates and compressing streams."""
    output_path = pdf_path.parent / f"{pdf_path.stem}_optimized.pdf"

    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)

        # Compress content streams after pages are added to writer
        for page in writer.pages:
            page.compress_content_streams()

        # Copy metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        # Enable compression
        writer.compress_identical_objects()

        # Write with compression
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        new_size = output_path.stat().st_size / (1024 * 1024)
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error optimizing {pdf_path.name}: {e}[/red]")
        return None, 0


def process_multipage_pdfs(pdf_files: List[Tuple[Path, int, float]], 
                            operation: str,
                            replace_original: bool = False):
    """Process multi-page PDFs based on the chosen operation (split only now)."""
    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]

    if not multi_page_pdfs:
        console.print("[green]No multi-page PDFs found![/green]")
        return

    console.print(f"\n[yellow]Found {len(multi_page_pdfs)} multi-page PDFs[/yellow]")

    for pdf_path, page_count, file_size in multi_page_pdfs:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        if not Confirm.ask(f"Split into {page_count} separate files?", default=False):
            continue

        output_files = split_to_pages(pdf_path)
        if output_files:
            console.print(f"[green]✓ Split into {len(output_files)} files:[/green]")
            for out_path, out_size in output_files:
                console.print(f"  - {out_path.name} ({out_size:.2f} MB)")

            if replace_original and Confirm.ask("Delete original file?", default=False):
                pdf_path.unlink()
                console.print("[green]✓ Original file deleted[/green]")


def process_single_pdf(pdf_path: Path, page_count: int, file_size: float,
                        args: argparse.Namespace):
    """Process a single PDF file based on the specified operation."""
    if args.analyze:
        analyze_pdf(pdf_path)

    elif args.optimize:
        if args.batch or Confirm.ask(f"Optimize {pdf_path.name}?", default=True):
            output_path, new_size = optimize_pdf(pdf_path)
            if output_path:
                console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                            f"({file_size:.2f} MB → {new_size:.2f} MB)")
                if args.replace and Confirm.ask("Replace original file?", default=False):
                    pdf_path.unlink()
                    output_path.rename(pdf_path)
                    console.print("[green]✓ Original file replaced[/green]")

    elif args.extract_pages:
        # Validate that extraction makes sense for this PDF
        try:
            pages_to_extract, _ = parse_page_range(args.extract_pages, page_count)
            if len(pages_to_extract) == page_count:
                console.print("[yellow]Extracting all pages - consider using --optimize instead[/yellow]")

            if args.batch or Confirm.ask(f"Extract pages {args.extract_pages} from {pdf_path.name}?", default=True):
                output_path, new_size = extract_pages(pdf_path, args.extract_pages)
                if output_path:
                    console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                    if file_size > 0:
                        console.print(f"[dim]Size: {((new_size / file_size) * 100):.1f}% of original[/dim]")
                    if args.replace and Confirm.ask("Replace original file?", default=False):
                        pdf_path.unlink()
                        output_path.rename(pdf_path)
                        console.print("[green]✓ Original file replaced[/green]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")

    elif args.split_pages:
        if page_count == 1:
            console.print("[yellow]PDF already has only one page[/yellow]")
        else:
            if args.batch or Confirm.ask(f"Split into {page_count} separate files?", default=False):
                output_files = split_to_pages(pdf_path)
                if output_files:
                    console.print(f"[green]✓ Split into {len(output_files)} files:[/green]")
                    for out_path, out_size in output_files:
                        console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                    if args.replace and Confirm.ask("Delete original file?", default=False):
                        pdf_path.unlink()
                        console.print("[green]✓ Original file deleted[/green]")


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
        epilog="""
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
    %(prog)s --extract-pages=3-7       # Extract pages 3 through 7
    %(prog)s --extract-pages="1-3,7"   # Extract pages 1-3 and page 7
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

    # Process based on input type
    if is_file:
        # Single file mode
        console.print(f"[blue]Processing file: {args.path.absolute()}[/blue]\n")
        pdf_files = scan_file(args.path)

        if not pdf_files:
            console.print("[red]Failed to read PDF file[/red]")
            sys.exit(1)

        # Display file info
        display_pdf_table(pdf_files, title="PDF File Assessment")

        # Process the single file if an operation was specified
        if any([args.extract_pages, args.split_pages, args.optimize, args.analyze]):
            pdf_path, page_count, file_size = pdf_files[0]
            process_single_pdf(pdf_path, page_count, file_size, args)
        else:
            # No operation specified - just show info
            if pdf_files[0][1] > 1:
                console.print(f"\n[yellow]This PDF has {pdf_files[0][1]} pages.[/yellow]")
                console.print("\nAvailable operations:")
                console.print("  --strip-first   Strip to first page only")
                console.print("  --extract-pages Extract specific pages (e.g., \"3-7\", \"last 2\")")
                console.print("  --split-pages   Split into individual pages")
                console.print("  --optimize      Optimize file size")
                console.print("  --analyze       Analyze PDF contents")
    else:
        # Folder mode (existing behavior)
        console.print(f"[blue]Scanning {args.path.absolute()}...[/blue]\n")
        pdf_files = scan_folder(args.path)

        if not pdf_files:
            console.print("[yellow]No PDF files found![/yellow]")
            sys.exit(0)

        # Display assessment
        display_pdf_table(pdf_files)

        # Handle operations
        if args.analyze:
            console.print("\n[blue]Analysis mode[/blue]")
            # Analyze large PDFs (> 1MB or > 0.5MB per page)
            for pdf_path, page_count, file_size in pdf_files:
                size_per_page = file_size / page_count if page_count > 0 else 0
                if file_size > 1.0 or size_per_page > 0.5:
                    analyze_pdf(pdf_path)

        elif args.optimize:
            console.print("\n[blue]Optimization mode[/blue]")
            for pdf_path, _, file_size in pdf_files:
                if args.batch or Confirm.ask(f"Optimize {pdf_path.name}?", default=True):
                    output_path, new_size = optimize_pdf(pdf_path)
                    if output_path:
                        console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                                    f"({file_size:.2f} MB → {new_size:.2f} MB)")

        elif args.extract_pages or args.split_pages:
            # Determine operation
            if args.extract_pages:
                operation = "extract"
                console.print(f"\n[blue]Extract pages mode: {args.extract_pages}[/blue]")
            else:
                operation = "split"
                console.print("\n[blue]Split pages mode[/blue]")

            # Extra warning for batch mode with replace
            if args.batch and args.replace:
                if operation == "extract":
                    console.print(f"[red]WARNING: This will extract pages {args.extract_pages} from ALL PDFs and replace originals![/red]")
                else:
                    console.print(f"[red]WARNING: This will split ALL multi-page PDFs and replace originals![/red]")
                if not Confirm.ask("Are you absolutely sure?", default=False):
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return

            # Process based on mode
            if args.batch:
                if operation == "extract":
                    # For extract, process all PDFs (not just multi-page)
                    for pdf_path, page_count, file_size in pdf_files:
                        console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
                        try:
                            # Check if extraction is valid for this PDF
                            pages_to_extract, _ = parse_page_range(args.extract_pages, page_count)
                            output_path, new_size = extract_pages(pdf_path, args.extract_pages)
                            if output_path:
                                console.print(f"[green]✓ Created:[/green] {output_path.name}")
                                if args.replace:
                                    pdf_path.unlink()
                                    output_path.rename(pdf_path)
                                    console.print("[yellow]✓ Replaced original[/yellow]")
                        except ValueError as e:
                            console.print(f"[yellow]Skipping {pdf_path.name}: {e}[/yellow]")
                else:
                    # Split mode - only multi-page PDFs
                    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]
                    for pdf_path, page_count, file_size in multi_page_pdfs:
                        console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
                        output_files = split_to_pages(pdf_path)
                        if output_files:
                            console.print(f"[green]✓ Split into {len(output_files)} files[/green]")
                            if args.replace:
                                pdf_path.unlink()
                                console.print("[yellow]✓ Deleted original[/yellow]")
            else:
                # Interactive mode
                if operation == "extract":
                    # For extract, ask about each PDF
                    for pdf_path, page_count, file_size in pdf_files:
                        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")
                        try:
                            # Validate extraction for this PDF
                            pages_to_extract, _ = parse_page_range(args.extract_pages, page_count)
                            if Confirm.ask(f"Extract pages {args.extract_pages}?", default=True):
                                output_path, new_size = extract_pages(pdf_path, args.extract_pages)
                                if output_path:
                                    console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                                    if args.replace and Confirm.ask("Replace original file?", default=False):
                                        pdf_path.unlink()
                                        output_path.rename(pdf_path)
                                        console.print("[green]✓ Original file replaced[/green]")
                        except ValueError as e:
                            console.print(f"[yellow]Cannot extract from this PDF: {e}[/yellow]")
                else:
                    # Split mode - only multi-page PDFs
                    process_multipage_pdfs(pdf_files, "split", args.replace)

        else:
            # No operation specified - just show assessment
            multi_page_count = sum(1 for _, pages, _ in pdf_files if pages > 1)
            if multi_page_count > 0:
                console.print(f"\n[yellow]Found {multi_page_count} multi-page PDF(s).[/yellow]")
                console.print("\nAvailable operations:")
                console.print("  --strip-first   Strip to first page only")
                console.print("  --extract-pages Extract specific pages (e.g., \"3-7\", \"last 2\")")
                console.print("  --split-pages   Split into individual pages")
                console.print("  --optimize      Optimize file sizes")
                console.print("  --analyze       Analyze PDF contents")
                console.print("\nAdd --batch to process all files without prompting")
                console.print("Add --replace to overwrite originals (use with extreme caution!)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)
