#!/usr/bin/env python3

__version__ = "20250701"

"""
PDF Manipulator - A CLI tool to assess PDFs and optionally strip pages
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
from rich.prompt import Confirm

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
                          replace_original: bool = False):
    """Process multi-page PDFs interactively."""
    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]

    if not multi_page_pdfs:
        console.print("[green]No multi-page PDFs found![/green]")
        return

    console.print(f"\n[yellow]Found {len(multi_page_pdfs)} multi-page PDFs[/yellow]")

    for pdf_path, page_count, file_size in multi_page_pdfs:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        if Confirm.ask("Strip to first page only?", default=False):
            output_path, new_size = strip_to_first_page(pdf_path)
            
            if output_path:
                console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                console.print(f"[dim]Size reduction: {((file_size - new_size) / file_size * 100):.1f}%[/dim]")

                if replace_original and Confirm.ask("Replace original file?", default=False):
                    pdf_path.unlink()
                    output_path.rename(pdf_path)
                    console.print("[green]✓ Original file replaced[/green]")


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
Examples:
    %(prog)s                      # Scan current directory
    %(prog)s /path/to/pdfs        # Scan specific directory
    %(prog)s --interactive        # Interactively process multi-page PDFs
    %(prog)s --auto               # Auto-process all multi-page PDFs
    %(prog)s --auto --replace     # Auto-process and replace originals (CAREFUL!)
    %(prog)s --optimize-only      # Only optimize file sizes
    %(prog)s --analyze            # Analyze PDF content and sizes

Note: No short arguments are provided to ensure clarity and prevent accidental misuse.
Always use the full argument names for safety and self-documentation.
        """
    )

    parser.add_argument('folder', type=Path, default=Path('.'), nargs='?',
                        help='Folder containing PDF files (default: current directory)')
    parser.add_argument('--replace', action='store_true',
                        help='Replace original files after processing (CAREFUL: still asks for confirmation)')
    parser.add_argument('--optimize-only', action='store_true',
                        help='Only optimize file sizes, keep all pages')
    parser.add_argument('--auto', action='store_true',
                        help='Automatically process all multi-page PDFs without prompting')
    parser.add_argument('--interactive', action='store_true',
                        help='Interactive mode - prompt for each multi-page PDF')
    parser.add_argument('--analyze', action='store_true',
                        help='Analyze PDFs to understand file sizes')

    args = parser.parse_args()

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

    # Only process if specific options are provided
    if args.analyze:
        console.print("\n[blue]Analysis mode[/blue]")
        # Analyze large PDFs (> 1MB or > 0.5MB per page)
        for pdf_path, page_count, file_size in pdf_files:
            size_per_page = file_size / page_count if page_count > 0 else 0
            if file_size > 1.0 or size_per_page > 0.5:
                analyze_pdf(pdf_path)
    elif args.optimize_only:
        console.print("\n[blue]Optimization mode[/blue]")
        for pdf_path, _, file_size in pdf_files:
            if Confirm.ask(f"Optimize {pdf_path.name}?", default=True):
                output_path, new_size = optimize_pdf(pdf_path)
                if output_path:
                    console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                                f"({file_size:.2f} MB → {new_size:.2f} MB)")
    elif args.auto:
        # Auto-process all multi-page PDFs
        console.print("\n[blue]Auto-processing multi-page PDFs[/blue]")
        
        # Extra warning if replace mode is active
        if args.replace:
            console.print("[red]WARNING: --replace is active! Original files will be overwritten![/red]")
            if not Confirm.ask("Are you sure you want to continue?", default=False):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        for pdf_path, page_count, file_size in pdf_files:
            if page_count > 1:
                console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
                output_path, new_size = strip_to_first_page(pdf_path)
                if output_path:
                    console.print(f"[green]✓ Created:[/green] {output_path.name}")
                    if args.replace:
                        pdf_path.unlink()
                        output_path.rename(pdf_path)
                        console.print(f"[yellow]✓ Replaced original file[/yellow]")
    elif args.interactive:
        # Interactive mode - only run when explicitly requested
        process_multipage_pdfs(
            pdf_files, 
            replace_original=args.replace
        )
    else:
        # Default: just show assessment
        multi_page_count = sum(1 for _, pages, _ in pdf_files if pages > 1)
        if multi_page_count > 0:
            console.print(f"\n[yellow]Found {multi_page_count} multi-page PDF(s).[/yellow]")
            console.print("Available options:")
            console.print("  --interactive   Interactively process each PDF")
            console.print("  --auto          Process all automatically (be careful!)")
            console.print("  --optimize-only Optimize file sizes without changing pages")
            console.print("  --analyze       Analyze PDFs to understand large file sizes")
            console.print("\nCombine with --replace to overwrite originals (use with caution!)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)
