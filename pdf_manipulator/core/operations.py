"""
Enhanced PDF manipulation operations with Phase 3 multi-page/multi-match pattern integration.
File: pdf_manipulator/core/operations.py

PHASE 3 ENHANCEMENTS:
- Full integration of multi-page and multi-match pattern extraction
- Real dry-run functionality with actual pattern preview
- Enhanced error handling and user feedback
- Backward compatibility with existing operations
- Intelligent fallback naming when pattern extraction fails
"""

import time
import argparse

from pathlib import Path
from rich.console import Console
from pypdf import PdfReader, PdfWriter

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings


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
    
    return writer


def _get_pdf_page_count(pdf_path: Path) -> int:
    """Get total page count for a PDF file."""
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            return len(reader.pages)
    except Exception:
        return 1  # Conservative fallback


def extract_pages(pdf_path: Path, page_range: str, 
                 patterns: list[str] = None, template: str = None,
                 source_page: int = 1, dry_run: bool = False) -> tuple[Path, float]:
    """
    Extract pages with Phase 3 intelligent naming via enhanced pattern extraction.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract (existing logic)
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction (when no pg spec)
        dry_run: Whether to perform actual extraction
        
    Returns:
        Tuple of (output_path, execution_time_or_file_size)
    """
    start_time = time.time()
    
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range (existing logic)
        pages_to_extract, range_desc, _ = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        sorted_pages = sorted(pages_to_extract)
        
        # Determine output filename with Phase 3 enhanced pattern extraction
        if patterns and template:
            from pdf_manipulator.renamer.filename_generator import FilenameGenerator
            generator = FilenameGenerator()
            
            if dry_run:
                # Phase 3: Real extraction preview for dry-run
                output_path, extraction_results = generator.generate_smart_filename(
                    pdf_path, range_desc, patterns, template, source_page, dry_run=True
                )
                console.print(f"\n[cyan]DRY RUN: Would extract pages {page_range} from {pdf_path.name}[/cyan]")
                generator.show_extraction_preview(extraction_results)
                console.print(f"[cyan]Would create:[/cyan] {output_path.name}")
                
                # Estimate file size
                estimated_size = (pdf_path.stat().st_size * len(sorted_pages) / total_pages) / (1024 * 1024)
                console.print(f"[dim]Estimated size: {estimated_size:.1f} MB[/dim]")
                
                return output_path, time.time() - start_time
            else:
                # Phase 3: Real extraction for actual file creation
                output_path, extraction_results = generator.generate_smart_filename(
                    pdf_path, range_desc, patterns, template, source_page
                )
                # Show warnings if any pattern extraction failed
                generator.show_extraction_warnings(extraction_results)
                
                # Show successful extractions
                successful_extractions = {
                    var: result for var, result in extraction_results.get('variables_extracted', {}).items()
                    if result.get('success') and result.get('selected_match') != "No_Match"
                }
                if successful_extractions:
                    console.print(f"[green]Smart filename: {output_path.name}[/green]")
                    for var, result in successful_extractions.items():
                        console.print(f"[dim]  {var}: \"{result['selected_match']}\"[/dim]")
        else:
            # Original simple naming
            output_path = pdf_path.parent / f"{pdf_path.stem}_pages{range_desc}.pdf"
            
            if dry_run:
                console.print(f"[cyan]DRY RUN: Would extract pages {page_range} as {output_path.name}[/cyan]")
                estimated_size = (pdf_path.stat().st_size * len(sorted_pages) / total_pages) / (1024 * 1024)
                console.print(f"[dim]Estimated size: {estimated_size:.1f} MB[/dim]")
                return output_path, time.time() - start_time
        
        # Ensure unique filename
        output_path = _get_unique_filename(output_path)
        
        # Proceed with actual extraction (existing logic)
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
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
    Extract specified pages from PDF as separate documents with Phase 3 smart naming.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction
        dry_run: Whether to perform actual extraction
        remove_images: Whether to remove images (for text-only extraction)
        
    Returns:
        List of (output_path, file_size) tuples
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range
        pages_to_extract, range_desc, _ = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        sorted_pages = sorted(pages_to_extract)
        output_files = []
        
        # Phase 3: Handle pattern extraction for separate files
        extraction_results_cache = {}
        if patterns and template:
            from pdf_manipulator.renamer.filename_generator import FilenameGenerator
            generator = FilenameGenerator()
            
            if dry_run:
                console.print(f"\n[cyan]DRY RUN: Would create {len(sorted_pages)} separate files[/cyan]")
                # Show pattern preview for first few pages
                preview_pages = sorted_pages[:3]  # Limit preview to avoid spam
                for page_num in preview_pages:
                    console.print(f"\n[cyan]Preview for page {page_num}:[/cyan]")
                    page_desc = f"p{page_num}"
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, page_desc, patterns, template, page_num, dry_run=True
                    )
                    generator.show_extraction_preview(extraction_results)
                    console.print(f"[cyan]Would create:[/cyan] {output_path.name}")
                
                if len(sorted_pages) > 3:
                    console.print(f"[dim]... and {len(sorted_pages) - 3} more files[/dim]")
                
                return [(pdf_path.parent / f"preview_page_{p}.pdf", 0) for p in sorted_pages]
        
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            
            for page_num in sorted_pages:
                # Generate filename for this page
                if patterns and template:
                    # Use page-specific pattern extraction
                    page_desc = f"p{page_num}"
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, page_desc, patterns, template, page_num
                    )
                    extraction_results_cache[page_num] = extraction_results
                else:
                    # Simple naming
                    output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num}.pdf"
                
                # Ensure unique filename
                output_path = _get_unique_filename(output_path)
                
                if dry_run:
                    output_files.append((output_path, 0))
                    continue
                
                # Create single-page PDF
                writer = PdfWriter()
                page_idx = page_num - 1  # Convert to 0-indexed
                writer.add_page(reader.pages[page_idx])
                
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
        
        # Show results summary
        if dry_run:
            console.print(f"[blue]DRY RUN: Would create {len(output_files)} separate files[/blue]")
        else:
            if remove_images:
                console.print(f"[green]✓ Extracted {len(sorted_pages)} pages as text-only files: {', '.join(map(str, sorted_pages))}[/green]")
            else:
                console.print(f"[green]✓ Extracted {len(sorted_pages)} pages as separate files: {', '.join(map(str, sorted_pages))}[/green]")
                
            # Show pattern extraction summary
            if patterns and template and extraction_results_cache:
                successful_count = sum(1 for results in extraction_results_cache.values() 
                                     if any(result.get('success') for result in results.get('variables_extracted', {}).values()))
                if successful_count > 0:
                    console.print(f"[green]Smart naming applied to {successful_count}/{len(sorted_pages)} files[/green]")
        
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
    Extract pages respecting original groupings with Phase 3 smart filename generation.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with grouping syntax
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction
        dry_run: Whether to perform actual extraction
        
    Returns:
        List of (output_path, file_size) tuples for each group
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range with grouping
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        if not groups:
            # Fallback to single group
            groups = [type('PageGroup', (), {'pages': sorted(pages_to_extract), 'desc': range_desc})()]
        
        output_files = []
        
        if dry_run:
            console.print(f"\n[cyan]DRY RUN: Would create {len(groups)} grouped files[/cyan]")
        
        # Phase 3: Handle pattern extraction for grouped files
        for group_idx, group in enumerate(groups):
            sorted_group_pages = sorted(group.pages)
            
            # Generate filename for this group
            if patterns and template:
                from pdf_manipulator.renamer.filename_generator import FilenameGenerator
                generator = FilenameGenerator()
                
                # Use first page of group for pattern extraction
                group_source_page = sorted_group_pages[0] if sorted_group_pages else source_page
                group_desc = getattr(group, 'desc', f"group{group_idx + 1}")
                
                if dry_run:
                    console.print(f"\n[cyan]Preview for group {group_idx + 1} (pages {', '.join(map(str, sorted_group_pages))}):[/cyan]")
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, group_desc, patterns, template, group_source_page, dry_run=True
                    )
                    generator.show_extraction_preview(extraction_results)
                    console.print(f"[cyan]Would create:[/cyan] {output_path.name}")
                    output_files.append((output_path, 0))
                    continue
                else:
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, group_desc, patterns, template, group_source_page
                    )
                    generator.show_extraction_warnings(extraction_results)
            else:
                # Simple naming
                if len(groups) == 1:
                    output_path = pdf_path.parent / f"{pdf_path.stem}_pages{range_desc}.pdf"
                else:
                    group_desc = getattr(group, 'desc', f"group{group_idx + 1}")
                    output_path = pdf_path.parent / f"{pdf_path.stem}_{group_desc}.pdf"
                
                if dry_run:
                    console.print(f"[cyan]Group {group_idx + 1}: Would create {output_path.name}[/cyan]")
                    output_files.append((output_path, 0))
                    continue
            
            # Ensure unique filename
            output_path = _get_unique_filename(output_path)
            
            # Create grouped PDF
            with suppress_pdf_warnings():
                reader = PdfReader(pdf_path)
                page_indices = [p - 1 for p in sorted_group_pages]  # Convert to 0-indexed
                writer = _create_optimized_writer_from_pages(reader, page_indices)
                
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
            console.print(f"[blue]DRY RUN: Would create {len(groups)} grouped files[/blue]")
        else:
            console.print(f"[green]✓ Created {len(groups)} grouped files[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting grouped pages from {pdf_path.name}: {e}[/red]")
        return []


def split_to_pages(pdf_path: Path, dry_run: bool = False) -> list[tuple[Path, float]]:
    """
    Split a multi-page PDF into individual page files.
    
    Args:
        pdf_path: Source PDF file
        dry_run: Whether to perform actual splitting
        
    Returns:
        List of (output_path, file_size) tuples
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        if total_pages <= 1:
            console.print(f"[yellow]{pdf_path.name} has only {total_pages} page(s), skipping split[/yellow]")
            return []
        
        output_files = []
        
        if dry_run:
            console.print(f"[cyan]DRY RUN: Would split {pdf_path.name} into {total_pages} individual pages[/cyan]")
            for page_num in range(1, total_pages + 1):
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num:02d}.pdf"
                output_files.append((output_path, 0))
            return output_files
        
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            
            for page_num in range(total_pages):
                # Create output filename
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num + 1:02d}.pdf"
                output_path = _get_unique_filename(output_path)
                
                # Create single-page PDF
                writer = PdfWriter()
                writer.add_page(reader.pages[page_num])
                
                # Copy metadata
                if reader.metadata:
                    writer.add_metadata(reader.metadata)
                
                # Write the output
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                # Get file size
                file_size = output_path.stat().st_size / (1024 * 1024)
                output_files.append((output_path, file_size))
        
        console.print(f"[green]✓ Split into {len(output_files)} individual pages[/green]")
        return output_files

    except Exception as e:
        console.print(f"[red]Error splitting {pdf_path.name}: {e}[/red]")
        return []


def optimize_pdf(pdf_path: Path) -> tuple[Path, float]:
    """
    Optimize a PDF file to reduce its size.
    
    Args:
        pdf_path: Source PDF file
        
    Returns:
        Tuple of (output_path, new_file_size_mb) or (None, 0) on error
    """
    try:
        output_path = pdf_path.parent / f"{pdf_path.stem}_optimized.pdf"
        output_path = _get_unique_filename(output_path)
        
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # Add all pages with optimization
            for page in reader.pages:
                writer.add_page(page)
            
            # Apply optimizations
            for page in writer.pages:
                page.compress_content_streams(level=9)
            
            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)
            
            # Write optimized file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        # Get new file size
        new_size = output_path.stat().st_size / (1024 * 1024)
        
        return output_path, new_size

    except Exception as e:
        console.print(f"[red]Error optimizing {pdf_path.name}: {e}[/red]")
        return None, 0


def analyze_pdf(pdf_path: Path) -> dict:
    """
    Analyze a PDF file and return basic information.
    
    Args:
        pdf_path: PDF file to analyze
        
    Returns:
        Dictionary with analysis results
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            
            analysis = {
                'path': pdf_path,
                'page_count': len(reader.pages),
                'file_size_mb': pdf_path.stat().st_size / (1024 * 1024),
                'has_metadata': bool(reader.metadata),
                'metadata': dict(reader.metadata) if reader.metadata else {},
                'is_encrypted': reader.is_encrypted
            }
            
            # Try to extract some text from first page
            try:
                first_page_text = reader.pages[0].extract_text()
                analysis['has_text'] = bool(first_page_text.strip())
                analysis['text_sample'] = first_page_text[:200] + "..." if len(first_page_text) > 200 else first_page_text
            except:
                analysis['has_text'] = False
                analysis['text_sample'] = ""
            
            return analysis

    except Exception as e:
        return {
            'path': pdf_path,
            'error': str(e),
            'page_count': 0,
            'file_size_mb': 0
        }


# End of file #
