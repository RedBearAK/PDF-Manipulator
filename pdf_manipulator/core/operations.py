"""Core PDF manipulation operations."""

import argparse
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from rich.console import Console
from pdf_manipulator.core.parser import parse_page_range

console = Console()


def process_folder_operations(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Delegate to folder operations module."""
    from .folder_operations import handle_folder_operations
    handle_folder_operations(args, pdf_files)


def extract_pages(pdf_path: Path, page_range: str) -> tuple[Path, float]:
    """Extract specified pages from PDF as a single document."""
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse the page range
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages)

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


def extract_pages_separate(pdf_path: Path, page_range: str) -> list[tuple[Path, float]]:
    """Extract specified pages from PDF as separate documents."""
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse the page range
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages)

        # Sort pages for output
        sorted_pages = sorted(pages_to_extract)
        output_files = []

        # Determine zero padding for filenames
        padding = len(str(max(sorted_pages)))

        for page_num in sorted_pages:
            # Create filename for this page
            page_str = str(page_num).zfill(padding)
            output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"

            # Create writer and add single page
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # Write the output
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            # Get file size
            file_size = output_path.stat().st_size / (1024 * 1024)
            output_files.append((output_path, file_size))

        console.print(f"[green]✓ Extracted {len(sorted_pages)} pages as separate files: {', '.join(map(str, sorted_pages))}[/green]")

        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        return []


def extract_pages_grouped(pdf_path: Path, page_range: str) -> list[tuple[Path, float]]:
    """Extract pages respecting original groupings - ranges become multi-page files, individuals become single files."""
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse with grouping information
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages)
        output_files = []

        # Determine padding for filenames
        max_pages = max(len(group.pages) for group in groups) if groups else 1
        all_pages = [page for group in groups for page in group.pages]
        padding = len(str(max(all_pages))) if all_pages else 1

        for group in groups:
            if group.is_range and len(group.pages) > 1:
                # Multi-page file for ranges
                sorted_pages = sorted(group.pages)
                start_page = sorted_pages[0]
                end_page = sorted_pages[-1]
                
                if len(sorted_pages) == (end_page - start_page + 1):
                    # Consecutive range
                    output_path = pdf_path.parent / f"{pdf_path.stem}_pages{start_page}-{end_page}.pdf"
                else:
                    # Non-consecutive (like step results)
                    page_list = ",".join(map(str, sorted_pages))
                    output_path = pdf_path.parent / f"{pdf_path.stem}_pages{page_list}.pdf"
                
                writer = PdfWriter()
                for page_num in sorted_pages:
                    writer.add_page(reader.pages[page_num - 1])
                    
            else:
                # Single page file
                page_num = group.pages[0]
                page_str = str(page_num).zfill(padding)
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"
                
                writer = PdfWriter()
                writer.add_page(reader.pages[page_num - 1])

            # Copy metadata and write file
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            file_size = output_path.stat().st_size / (1024 * 1024)
            output_files.append((output_path, file_size))

        console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        return []


def split_to_pages(pdf_path: Path) -> list[tuple[Path, float]]:
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


def optimize_pdf(pdf_path: Path) -> tuple[Path, float]:
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
