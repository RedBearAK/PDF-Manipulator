#!/usr/bin/env python3

__version__ = "20250701"

"""
PDF Manipulator - A CLI tool to assess PDFs and optionally strip pages
Uses pikepdf for robust PDF manipulation and optimization
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import pikepdf
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, IntPrompt

console = Console()


def get_pdf_info(pdf_path: Path) -> Tuple[int, float]:
    """Get page count and file size for a PDF."""
    try:
        with pikepdf.open(pdf_path) as pdf:
            page_count = len(pdf.pages)

        file_size = pdf_path.stat().st_size / (1024 * 1024)  # Convert to MB
        return page_count, file_size
    except Exception as e:
        console.print(f"[red]Error reading {pdf_path.name}: {e}[/red]")
        return 0, 0


def scan_folder(folder_path: Path) -> List[Tuple[Path, int, float]]:
    """Scan folder for PDF files and return their info."""
    pdf_files = []

    for pdf_path in folder_path.glob("*.pdf"):
        page_count, file_size = get_pdf_info(pdf_path)
        if page_count > 0:
            pdf_files.append((pdf_path, page_count, file_size))

    return sorted(pdf_files, key=lambda x: x[0].name)


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


def strip_to_first_page(pdf_path: Path, optimize: bool = True) -> Path:
    """Strip PDF to first page only and optionally optimize."""
    output_path = pdf_path.parent / f"{pdf_path.stem}_page1.pdf"

    try:
        with pikepdf.open(pdf_path) as pdf:
            # Create new PDF with only first page
            new_pdf = pikepdf.Pdf.new()
            new_pdf.pages.append(pdf.pages[0])

            # Copy metadata
            if pdf.docinfo:
                new_pdf.docinfo.update(pdf.docinfo)

            # Save with optimization
            save_options = {
                'compress_streams': True,
                'object_stream_mode': pikepdf.ObjectStreamMode.generate
            }

            if optimize:
                save_options.update({
                    'linearize': True,  # Fast web view
                    'qdf': False,
                    'preserve_pdfa': True,
                    'min_version': pdf.pdf_version
                })

            new_pdf.save(output_path, **save_options)

        # Get new file size
        new_size = output_path.stat().st_size / (1024 * 1024)
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
        return None, 0


def optimize_pdf(pdf_path: Path, aggressive: bool = False) -> Tuple[Path, float]:
    """Optimize PDF file size without changing content."""
    output_path = pdf_path.parent / f"{pdf_path.stem}_optimized.pdf"

    try:
        with pikepdf.open(pdf_path) as pdf:
            # Remove unreferenced resources
            pdf.remove_unreferenced_resources()

            save_options = {
                'compress_streams': True,
                'object_stream_mode': pikepdf.ObjectStreamMode.generate,
                'linearize': True,
                'qdf': False,
                'preserve_pdfa': True,
            }

            if aggressive:
                # More aggressive optimization
                save_options['recompress_flate'] = True

                # Optionally downsample images (requires Pillow)
                try:
                    for page in pdf.pages:
                        for image_key in page.images:
                            image = page.images[image_key]
                            # You could add image optimization here
                            # using pikepdf's image handling capabilities
                except:
                    pass

            pdf.save(output_path, **save_options)

        new_size = output_path.stat().st_size / (1024 * 1024)
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error optimizing {pdf_path.name}: {e}[/red]")
        return None, 0


def process_multipage_pdfs(pdf_files: List[Tuple[Path, int, float]], 
                            replace_original: bool = False,
                            optimize: bool = True):
    """Process multi-page PDFs interactively."""
    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]

    if not multi_page_pdfs:
        console.print("[green]No multi-page PDFs found![/green]")
        return

    console.print(f"\n[yellow]Found {len(multi_page_pdfs)} multi-page PDFs[/yellow]")

    for pdf_path, page_count, file_size in multi_page_pdfs:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        if Confirm.ask("Strip to first page only?", default=False):
            output_path, new_size = strip_to_first_page(pdf_path, optimize)
            # Type hint to light up the ".name" method below.
            output_path: Path   # Better way? Not allowed in multi-var assignment line.

            if output_path:
                console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                console.print(f"[dim]Size reduction: {((file_size - new_size) / file_size * 100):.1f}%[/dim]")

                if replace_original and Confirm.ask("Replace original file?", default=False):
                    pdf_path.unlink()
                    output_path.rename(pdf_path)
                    console.print("[green]✓ Original file replaced[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="PDF Manipulator - Assess and manipulate PDF pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s .                    # Scan current directory
    %(prog)s /path/to/pdfs        # Scan specific directory
    %(prog)s . --replace          # Replace originals after confirmation
    %(prog)s . --optimize-only    # Only optimize file sizes
    %(prog)s . --auto             # Auto-process without prompts
        """
    )

    parser.add_argument('folder', type=Path, default=Path('.'), nargs='?',
                        help='Folder containing PDF files (default: current directory)')
    parser.add_argument('-r', '--replace', action='store_true',
                        help='Replace original files (with confirmation)')
    parser.add_argument('-o', '--optimize-only', action='store_true',
                        help='Only optimize file sizes, keep all pages')
    parser.add_argument('-a', '--auto', action='store_true',
                        help='Automatically process all multi-page PDFs')
    parser.add_argument('--no-optimize', action='store_true',
                        help='Skip optimization step')

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

    # Process based on mode
    if args.optimize_only:
        console.print("\n[blue]Optimization mode[/blue]")
        for pdf_path, _, file_size in pdf_files:
            if Confirm.ask(f"Optimize {pdf_path.name}?", default=True):
                output_path, new_size = optimize_pdf(pdf_path, aggressive=True)
                if output_path:
                    console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                                f"({file_size:.2f} MB → {new_size:.2f} MB)")
    else:
        # Process multi-page PDFs
        if args.auto:
            # Auto-process all multi-page PDFs
            for pdf_path, page_count, file_size in pdf_files:
                if page_count > 1:
                    console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
                    output_path, new_size = strip_to_first_page(
                        pdf_path, optimize=not args.no_optimize
                    )
                    if output_path:
                        console.print(f"[green]✓ Created:[/green] {output_path.name}")
                        if args.replace:
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
        else:
            # Interactive mode
            process_multipage_pdfs(
                pdf_files, 
                replace_original=args.replace,
                optimize=not args.no_optimize
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)

