#!/usr/bin/env python3

__version__ = "20250701"

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
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt

console = Console()


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


def display_pdf_table(pdf_files: List[Tuple[Path, int, float]]):
    """Display PDF files in a formatted table."""
    table = Table(title="PDF Files Assessment")
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
    """Process multi-page PDFs based on the chosen operation."""
    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]

    if not multi_page_pdfs:
        console.print("[green]No multi-page PDFs found![/green]")
        return

    console.print(f"\n[yellow]Found {len(multi_page_pdfs)} multi-page PDFs[/yellow]")

    for pdf_path, page_count, file_size in multi_page_pdfs:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        # Ask what to do with this specific PDF
        if operation == "ask":
            action = Prompt.ask(
                "What would you like to do?",
                choices=["strip", "split", "skip"],
                default="skip"
            )
        else:
            action = operation
            if action == "strip":
                if not Confirm.ask("Strip to first page only?", default=False):
                    action = "skip"
            elif action == "split":
                if not Confirm.ask(f"Split into {page_count} separate files?", default=False):
                    action = "skip"

        if action == "strip":
            output_path, new_size = strip_to_first_page(pdf_path)
            if output_path:
                console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                console.print(f"[dim]Size reduction: {((file_size - new_size) / file_size * 100):.1f}%[/dim]")

                if replace_original and Confirm.ask("Replace original file?", default=False):
                    pdf_path.unlink()
                    output_path.rename(pdf_path)
                    console.print("[green]✓ Original file replaced[/green]")
                    
        elif action == "split":
            output_files = split_to_pages(pdf_path)
            if output_files:
                console.print(f"[green]✓ Split into {len(output_files)} files:[/green]")
                for out_path, out_size in output_files:
                    console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                
                if replace_original and Confirm.ask("Delete original file?", default=False):
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
    --strip-first     Strip multi-page PDFs to first page only
    --split-pages     Split multi-page PDFs into individual pages
    --optimize        Optimize PDF file sizes
    --analyze         Analyze PDFs to understand file sizes

Modes:
    --interactive     Process each PDF interactively (ask for each file)
    --batch           Process all matching PDFs without prompting

Examples:
    %(prog)s                           # Just scan and assess
    %(prog)s --analyze                 # Analyze large PDFs
    %(prog)s --optimize                # Optimize all PDFs
    %(prog)s --strip-first             # Interactive: ask which PDFs to strip
    %(prog)s --split-pages             # Interactive: ask which PDFs to split
    %(prog)s --strip-first --batch     # Strip ALL multi-page PDFs (careful!)
    %(prog)s --split-pages --batch     # Split ALL multi-page PDFs (careful!)

Safety options:
    --replace         Replace/delete originals after processing (still asks!)
    --strip-first --batch --replace    # Most dangerous: strips all and replaces

Note: No short arguments are provided to ensure clarity and prevent accidents.
        """
    )

    parser.add_argument('folder', type=Path, default=Path('.'), nargs='?',
                        help='Folder containing PDF files (default: current directory)')
    
    # Operations
    operations = parser.add_argument_group('operations')
    operations.add_argument('--strip-first', action='store_true',
                           help='Strip multi-page PDFs to first page only')
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

    # Validate arguments
    if args.batch and args.interactive:
        console.print("[red]Error: Cannot use both --batch and --interactive[/red]")
        sys.exit(1)
        
    operations_count = sum([args.strip_first, args.split_pages, args.optimize, args.analyze])
    if operations_count > 1:
        console.print("[red]Error: Please specify only one operation at a time[/red]")
        sys.exit(1)

    if not args.folder.exists() or not args.folder.is_dir():
        console.print(f"[red]Error: {args.folder} is not a valid directory[/red]")
        sys.exit(1)

    # Scan folder
    console.print(f"[blue]Scanning {args.folder.absolute()}...[/blue]\n")
    pdf_files = scan_folder(args.folder)

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
                    
    elif args.strip_first or args.split_pages:
        # Determine operation
        if args.strip_first:
            operation = "strip"
            console.print("\n[blue]Strip to first page mode[/blue]")
        else:
            operation = "split"
            console.print("\n[blue]Split pages mode[/blue]")
        
        # Extra warning for batch mode with replace
        if args.batch and args.replace:
            console.print(f"[red]WARNING: This will {operation} ALL multi-page PDFs and replace originals![/red]")
            if not Confirm.ask("Are you absolutely sure?", default=False):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        # Process based on mode
        if args.batch:
            multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]
            for pdf_path, page_count, file_size in multi_page_pdfs:
                console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
                
                if operation == "strip":
                    output_path, new_size = strip_to_first_page(pdf_path)
                    if output_path:
                        console.print(f"[green]✓ Created:[/green] {output_path.name}")
                        if args.replace:
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
                            console.print("[yellow]✓ Replaced original[/yellow]")
                            
                elif operation == "split":
                    output_files = split_to_pages(pdf_path)
                    if output_files:
                        console.print(f"[green]✓ Split into {len(output_files)} files[/green]")
                        if args.replace:
                            pdf_path.unlink()
                            console.print("[yellow]✓ Deleted original[/yellow]")
        else:
            # Interactive mode (default)
            process_multipage_pdfs(pdf_files, operation, args.replace)
            
    else:
        # No operation specified - just show assessment
        multi_page_count = sum(1 for _, pages, _ in pdf_files if pages > 1)
        if multi_page_count > 0:
            console.print(f"\n[yellow]Found {multi_page_count} multi-page PDF(s).[/yellow]")
            console.print("\nAvailable operations:")
            console.print("  --strip-first  Strip to first page only")
            console.print("  --split-pages  Split into individual pages")
            console.print("  --optimize     Optimize file sizes")
            console.print("  --analyze      Analyze PDF contents")
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
