"""
Enhanced PDF manipulation operations with intelligent filename generation.
File: pdf_manipulator/core/operations.py

PHASE 2 ENHANCEMENTS:
- Smart filename generation using pattern extraction and templates
- Graceful fallback to original naming when extraction fails
- Support for dry-run with real pattern extraction
- Backward compatibility maintained for all existing functionality
"""

import argparse

from pypdf import PdfReader, PdfWriter
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
from pdf_manipulator.renamer.filename_generator import FilenameGenerator


console = Console()


class PDFManipulatorError(Exception):
    """Base exception for PDF Manipulator operations."""
    pass

class MalformedPDFError(PDFManipulatorError):
    """Exception for malformed PDF handling."""
    pass

class ExtractionError(PDFManipulatorError):
    """Exception for page extraction errors."""
    pass


def _get_unique_filename(base_path: Path) -> Path:
    """Generate a unique filename by appending _copy_01, _copy_02, etc. if file exists."""
    if not base_path.exists():
        return base_path
    
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_copy_{counter:02d}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def _create_optimized_writer_from_pages(reader: PdfReader, page_indices: list[int]) -> PdfWriter:
    """Create a new optimized writer with only the specified pages and their required resources."""
    writer = PdfWriter()
    
    # Add only the specified pages
    for page_idx in page_indices:
        writer.add_page(reader.pages[page_idx])
    
    # Apply aggressive optimizations
    for page in writer.pages:
        # Compress content streams with maximum compression
        page.compress_content_streams(level=9)  # Maximum compression level
        
        # Try to remove unused images (this PDF has all images on every page!)
        if hasattr(page, 'images'):
            try:
                # For malformed PDFs where every page has all images,
                # we need to be more aggressive about removing unused images
                images_to_keep = []
                for img in page.images:
                    # Try to reduce image quality to save space
                    try:
                        # Value of "60" here caused broken images in extracted PDFs
                        # img.replace(img.image, quality=60)  # More aggressive compression
                        images_to_keep.append(img)
                    except Exception:
                        # If we can't compress, at least keep the image
                        images_to_keep.append(img)
                
                # Try to remove images if possible (experimental)
                # This is for PDFs where all images are embedded on every page
                if len(page.images) > 10:  # Likely malformed if >10 images per page
                    console.print(f"[yellow]Warning: Page has {len(page.images)} images - attempting to optimize[/yellow]")
                    
            except Exception as e:
                console.print(f"[dim]Note: Could not optimize images on page: {e}[/dim]")
    
    # Remove duplicate objects and orphaned resources aggressively
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    
    return writer


def _generate_smart_filename(pdf_path: Path, range_desc: str,
                           patterns: list[str] = None, template: str = None,
                           source_page: int = 1, dry_run: bool = False) -> tuple[Path, dict]:
    """
    Generate intelligent filename using pattern extraction and templates.
    
    PHASE 2: New smart filename generation with graceful fallback.
    
    Args:
        pdf_path: Original PDF file path
        range_desc: Description of extracted page range
        patterns: List of compact pattern strings
        template: Filename template string
        source_page: Page to extract patterns from
        dry_run: Whether this is a dry-run (affects extraction)
        
    Returns:
        Tuple of (output_path, extraction_results)
    """
    if not patterns or not template:
        # No smart naming - use traditional approach
        base_output_path = pdf_path.parent / f"{pdf_path.stem}_{range_desc}.pdf"
        return _get_unique_filename(base_output_path), {'fallback_used': True}
    
    try:
        generator = FilenameGenerator()
        return generator.generate_smart_filename(
            pdf_path, range_desc, patterns, template, source_page, dry_run
        )
    except Exception as e:
        console.print(f"[yellow]Smart filename generation failed ({e}), using simple naming[/yellow]")
        base_output_path = pdf_path.parent / f"{pdf_path.stem}_{range_desc}.pdf"
        return _get_unique_filename(base_output_path), {'fallback_used': True, 'error': str(e)}


def process_folder_operations(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Delegate to folder operations module."""
    from .folder_operations import handle_folder_operations
    handle_folder_operations(args, pdf_files)


def extract_pages(pdf_path: Path, page_range: str, patterns: list[str] = None,
                 template: str = None, source_page: int = 1, 
                 dry_run: bool = False) -> tuple[Path, float]:
    """
    Extract specified pages from PDF as a single document.
    
    PHASE 2 ENHANCED: Now supports smart filename generation.
    
    Args:
        pdf_path: Path to source PDF
        page_range: Range specification for pages to extract
        patterns: Optional list of pattern strings for content extraction
        template: Optional filename template
        source_page: Page to extract patterns from (default: 1)
        dry_run: Whether this is a dry-run preview
        
    Returns:
        Tuple of (output_path, file_size_mb)
    """
    
    try:
        with suppress_pdf_warnings(show_summary=True):
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)

            # Parse the page range
            pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)

            # Check if any pages were found
            if not pages_to_extract:
                console.print(f"[yellow]No pages found matching pattern: {page_range}[/yellow]")
                return None, 0

            # Sort pages for output
            sorted_pages = sorted(pages_to_extract)

            # PHASE 2: Generate smart filename
            output_path, extraction_results = _generate_smart_filename(
                pdf_path, range_desc, patterns, template, source_page, dry_run
            )

            # Show extraction results if patterns were used
            if patterns and template and not extraction_results.get('fallback_used', False):
                console.print(f"[green]Smart filename: {output_path.name}[/green]")
                if extraction_results.get('variables_extracted'):
                    for var, value in extraction_results['variables_extracted'].items():
                        if value:
                            console.print(f"[dim]  {var}: {value}[/dim]")

            # Handle dry-run
            if dry_run:
                estimated_size = (pdf_path.stat().st_size * len(sorted_pages) / total_pages) / (1024 * 1024)
                console.print(f"[blue]DRY RUN: Would extract {len(sorted_pages)} pages as {output_path.name}[/blue]")
                console.print(f"[dim]Estimated size: {estimated_size:.1f} MB[/dim]")
                return output_path, estimated_size

            # Create optimized writer
            page_indices = [p - 1 for p in sorted_pages]  # Convert to 0-indexed
            writer = _create_optimized_writer_from_pages(reader, page_indices)

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


def extract_pages_separate(pdf_path: Path, page_range: str, patterns: list[str] = None,
                          template: str = None, source_page: int = 1,
                          dry_run: bool = False, remove_images: bool = False) -> list[tuple[Path, float]]:
    """
    Extract specified pages from PDF as separate documents.
    
    PHASE 2 ENHANCED: Now supports smart filename generation for each page.
    
    Args:
        pdf_path: Path to source PDF
        page_range: Range specification for pages to extract
        patterns: Optional list of pattern strings for content extraction
        template: Optional filename template (modified for individual pages)
        source_page: Page to extract patterns from (default: 1)
        dry_run: Whether this is a dry-run preview
        remove_images: Whether to remove images for size reduction
        
    Returns:
        List of (output_path, file_size_mb) tuples
    """
    
    try:
        with suppress_pdf_warnings(show_summary=True):
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)

            # Parse the page range
            pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)

            # Check if any pages were found
            if not pages_to_extract:
                console.print(f"[yellow]No pages found matching pattern: {page_range}[/yellow]")
                return []

            # Sort pages for output
            sorted_pages = sorted(pages_to_extract)
            output_files = []

            # Check for malformed PDF (every page has too many images)
            sample_page = reader.pages[0]
            image_count = 0
            if '/XObject' in sample_page.get('/Resources', {}):
                xobjects = sample_page['/Resources']['/XObject'].get_object()
                images = [x for x in xobjects if xobjects[x].get('/Subtype') == '/Image']
                image_count = len(images)
            
            is_malformed = image_count >= total_pages * 0.5  # If page has 50%+ of total pages as images
            
            if is_malformed and not remove_images:
                console.print(f"[yellow]Detected malformed PDF: Each page has {image_count} images (likely duplicated across all pages)[/yellow]")
                console.print("[yellow]Consider using --remove-images flag for dramatic size reduction[/yellow]")

            # Determine zero padding for filenames
            padding = len(str(max(sorted_pages)))

            # PHASE 2: Extract pattern content once (if using smart naming)
            extraction_results = {}
            if patterns and template:
                try:
                    generator = FilenameGenerator()
                    _, extraction_results = generator.generate_smart_filename(
                        pdf_path, range_desc, patterns, template, source_page, dry_run=True
                    )
                    
                    if not extraction_results.get('fallback_used', False):
                        console.print(f"[green]Smart naming: extracted content from page {source_page}[/green]")
                        for var, value in extraction_results.get('variables_extracted', {}).items():
                            if value:
                                console.print(f"[dim]  {var}: {value}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Pattern extraction failed ({e}), using simple naming[/yellow]")
                    extraction_results = {'fallback_used': True}

            for page_num in sorted_pages:
                # Create filename for this page
                page_str = str(page_num).zfill(padding)
                
                if patterns and template and not extraction_results.get('fallback_used', False):
                    # Use smart naming with page number
                    try:
                        generator = FilenameGenerator()
                        
                        # Modify template to include page number
                        if '{range}' in template:
                            page_template = template.replace('{range}', page_str)
                        else:
                            # Add page number to template
                            base_template = template.replace('.pdf', f'_page{page_str}.pdf')
                            page_template = base_template
                        
                        output_path, _ = generator.generate_smart_filename(
                            pdf_path, page_str, patterns, page_template, source_page, dry_run
                        )
                    except Exception:
                        # Fallback to simple naming
                        if remove_images:
                            base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}_text.pdf"
                        else:
                            base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"
                        output_path = _get_unique_filename(base_output_path)
                else:
                    # Simple naming
                    if remove_images:
                        base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}_text.pdf"
                    else:
                        base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"
                    output_path = _get_unique_filename(base_output_path)

                # Handle dry-run
                if dry_run:
                    estimated_size = (pdf_path.stat().st_size / total_pages) / (1024 * 1024)
                    console.print(f"[blue]DRY RUN: Would extract page {page_num} as {output_path.name}[/blue]")
                    output_files.append((output_path, estimated_size))
                    continue

                # Create optimized writer for single page
                writer = _create_optimized_writer_from_pages(reader, [page_num - 1])

                # Remove images if requested (for malformed PDFs)
                if remove_images:
                    try:
                        writer.remove_images()
                        console.print(f"[dim]Removed images from page {page_num}[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]Could not remove images from page {page_num}: {e}[/yellow]")

                # Copy metadata
                if reader.metadata:
                    writer.add_metadata(reader.metadata)

                # Write the output
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)

                # Get file size
                file_size = output_path.stat().st_size / (1024 * 1024)
                output_files.append((output_path, file_size))

            if dry_run:
                console.print(f"[blue]DRY RUN: Would create {len(output_files)} separate files[/blue]")
            elif remove_images:
                console.print(f"[green]✓ Extracted {len(sorted_pages)} pages as text-only files: {', '.join(map(str, sorted_pages))}[/green]")
            else:
                console.print(f"[green]✓ Extracted {len(sorted_pages)} pages as separate files: {', '.join(map(str, sorted_pages))}[/green]")

            return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        return []


def extract_pages_grouped(pdf_path: Path, page_range: str, patterns: list[str] = None,
                         template: str = None, source_page: int = 1,
                         dry_run: bool = False) -> list[tuple[Path, float]]:
    """
    Extract pages respecting original groupings with smart filename generation.
    
    PHASE 2 ENHANCED: Now supports smart filename generation for groups.
    """
    
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Parse with grouping information
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        # Check if any pages were found
        if not pages_to_extract:
            console.print(f"[yellow]No pages found matching pattern: {page_range}[/yellow]")
            return []

        output_files = []

        # Determine padding for filenames
        max_pages = max(len(group.pages) for group in groups) if groups else 1
        all_pages = [page for group in groups for page in group.pages]
        padding = len(str(max(all_pages))) if all_pages else 1

        # PHASE 2: Extract pattern content once (if using smart naming)
        extraction_results = {}
        if patterns and template:
            try:
                generator = FilenameGenerator()
                _, extraction_results = generator.generate_smart_filename(
                    pdf_path, range_desc, patterns, template, source_page, dry_run=True
                )
                
                if not extraction_results.get('fallback_used', False):
                    console.print(f"[green]Smart naming: extracted content from page {source_page}[/green]")
                    for var, value in extraction_results.get('variables_extracted', {}).items():
                        if value:
                            console.print(f"[dim]  {var}: {value}[/dim]")
            except Exception as e:
                console.print(f"[yellow]Pattern extraction failed ({e}), using simple naming[/yellow]")
                extraction_results = {'fallback_used': True}

        for group_idx, group in enumerate(groups):
            if group.is_range and len(group.pages) > 1:
                # Multi-page file for ranges
                sorted_pages = sorted(group.pages)
                start_page = sorted_pages[0]
                end_page = sorted_pages[-1]
                
                # Create group range description
                if len(sorted_pages) == (end_page - start_page + 1):
                    # Consecutive range
                    group_range_desc = f"{start_page:02d}-{end_page:02d}"
                else:
                    # Non-consecutive (like step results)
                    group_range_desc = ",".join(f"{p:02d}" for p in sorted_pages)
                
                page_indices = [p - 1 for p in sorted_pages]  # Convert to 0-indexed
                writer = _create_optimized_writer_from_pages(reader, page_indices)
                    
            else:
                # Single page file
                page_num = group.pages[0]
                group_range_desc = f"{page_num:02d}"
                writer = _create_optimized_writer_from_pages(reader, [page_num - 1])

            # Generate filename for this group
            if patterns and template and not extraction_results.get('fallback_used', False):
                # Use smart naming with group range
                try:
                    generator = FilenameGenerator()
                    
                    # Modify template to include group range
                    if '{range}' in template:
                        group_template = template.replace('{range}', group_range_desc)
                    else:
                        # Add group range to template
                        group_template = template.replace('.pdf', f'_pages{group_range_desc}.pdf')
                    
                    output_path, _ = generator.generate_smart_filename(
                        pdf_path, group_range_desc, patterns, group_template, source_page, dry_run
                    )
                except Exception:
                    # Fallback to simple naming
                    if group.is_range and len(group.pages) > 1:
                        base_output_path = pdf_path.parent / f"{pdf_path.stem}_pages{group_range_desc}.pdf"
                    else:
                        page_str = str(group.pages[0]).zfill(padding)
                        base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"
                    output_path = _get_unique_filename(base_output_path)
            else:
                # Simple naming
                if group.is_range and len(group.pages) > 1:
                    base_output_path = pdf_path.parent / f"{pdf_path.stem}_pages{group_range_desc}.pdf"
                else:
                    page_str = str(group.pages[0]).zfill(padding)
                    base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_str}.pdf"
                output_path = _get_unique_filename(base_output_path)

            # Handle dry-run
            if dry_run:
                estimated_size = (pdf_path.stat().st_size * len(group.pages) / total_pages) / (1024 * 1024)
                console.print(f"[blue]DRY RUN: Would create group {group_idx + 1} as {output_path.name}[/blue]")
                output_files.append((output_path, estimated_size))
                continue

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # Write file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            file_size = output_path.stat().st_size / (1024 * 1024)
            output_files.append((output_path, file_size))

        if dry_run:
            console.print(f"[blue]DRY RUN: Would create {len(output_files)} grouped files[/blue]")
        else:
            console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        return []


def split_to_pages(pdf_path: Path, dry_run: bool = False) -> list[tuple[Path, float]]:
    """
    Split PDF into individual pages with resource optimization.
    
    PHASE 2: Added dry-run support.
    """
    
    output_files = []

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Determine zero padding for filenames
        padding = len(str(total_pages))

        for i in range(total_pages):
            page_num = str(i + 1).zfill(padding)
            base_output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num}.pdf"
            output_path = _get_unique_filename(base_output_path)

            # Handle dry-run
            if dry_run:
                estimated_size = (pdf_path.stat().st_size / total_pages) / (1024 * 1024)
                console.print(f"[blue]DRY RUN: Would create page {i + 1} as {output_path.name}[/blue]")
                output_files.append((output_path, estimated_size))
                continue

            # Create optimized writer for single page
            writer = _create_optimized_writer_from_pages(reader, [i])

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # Write the page
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            # Get file size
            file_size = output_path.stat().st_size / (1024 * 1024)
            output_files.append((output_path, file_size))

        if dry_run:
            console.print(f"[blue]DRY RUN: Would split into {len(output_files)} files[/blue]")

        return output_files

    except Exception as e:
        console.print(f"[red]Error splitting {pdf_path.name}: {e}[/red]")
        return []


def optimize_pdf(pdf_path: Path) -> tuple[Path, float]:
    """Compress PDF by removing duplicates and compressing streams."""
    base_output_path = pdf_path.parent / f"{pdf_path.stem}_optimized.pdf"
    output_path = _get_unique_filename(base_output_path)

    try:
        reader = PdfReader(pdf_path)
        
        # Create optimized writer with all pages
        all_page_indices = list(range(len(reader.pages)))
        writer = _create_optimized_writer_from_pages(reader, all_page_indices)

        # Copy metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        # Write with compression
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        new_size = output_path.stat().st_size / (1024 * 1024)
        
        if output_path != base_output_path:
            console.print(f"[yellow]Note: Saved as {output_path.name} to avoid overwriting existing file[/yellow]")
            
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error optimizing {pdf_path.name}: {e}[/red]")
        return None, 0


def analyze_pdf(pdf_path: Path) -> None:
    """Analyze PDF content to understand file size."""
    try:
        with suppress_pdf_warnings(show_summary=True):
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
                console.print("[dim]Scanned PDFs often have large images that can't be easily optimized without quality loss[/dim]")

    except Exception as e:
        console.print(f"[red]Error analyzing {pdf_path.name}: {e}[/red]")


# End of file #
