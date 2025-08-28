"""
Enhanced page extraction operations with order preservation support.
File: pdf_manipulator/core/operations.py

Key changes:
- Respect PageGroup.preserve_order flag 
- Use ordered page lists from groups instead of always sorting
- Maintain backward compatibility for existing functionality
"""

import time
from pathlib import Path
from rich.console import Console

from pypdf import PdfReader, PdfWriter

from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.file_conflicts import resolve_file_conflicts
from pdf_manipulator.core.smart_filenames import (
    generate_extraction_filename,
    generate_smart_description
)
from pdf_manipulator.core.operation_context import OpCtx, get_cached_parsing_results, get_parsed_pages
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings

console = Console()


def get_ordered_pages_from_groups(groups: list, fallback_pages: set = None, 
                                    dedup_strategy: str = 'strict') -> list[int]:
    """
    Extract pages in the correct order from PageGroup objects with optional deduplication.
    
    This is the canonical implementation used throughout the PDF manipulator tool.
    
    Args:
        groups: List of PageGroup objects
        fallback_pages: Fallback page set if groups don't have preserve_order info
        dedup_strategy: Deduplication strategy ('none', 'strict', 'groups', 'warn', 'fail')
        
    Returns:
        List of pages in the intended order
        
    Raises:
        ValueError: If dedup_strategy is 'fail' and duplicates are detected
    """
    if not groups:
        return sorted(fallback_pages) if fallback_pages else []
    
    # Apply deduplication strategy if specified and not 'none'
    if dedup_strategy != 'none':
        try:
            from pdf_manipulator.core.deduplication import apply_deduplication_strategy
            processed_groups, dedup_info = apply_deduplication_strategy(groups, dedup_strategy)
        except (ImportError, ValueError) as e:
            # If deduplication module not available or fails, fall back to original groups
            if dedup_strategy == 'fail':
                raise e  # Re-raise if user explicitly wants to fail
            else:
                console.print(f"[yellow]Warning: Deduplication failed, proceeding without: {e}[/yellow]")
                processed_groups = groups
    else:
        processed_groups = groups
    
    ordered_pages = []
    has_preserve_order = processed_groups and hasattr(processed_groups[0], 'preserve_order')
    
    for group in processed_groups:
        # Skip empty groups (this was the critical Alaska cities fix)
        if not hasattr(group, 'pages') or not group.pages:
            continue
            
        # For ranges, always preserve the order as specified in the pages list
        # For comma-separated preserve_order groups, also preserve order
        # For other groups, sort for backward compatibility
        if (hasattr(group, 'is_range') and group.is_range) or \
            (has_preserve_order and getattr(group, 'preserve_order', False)):
            # Preserve the exact order from this group (ranges or preserve_order=True)
            ordered_pages.extend(group.pages)
        else:
            # Use sorted order for this group (backward compatibility)
            ordered_pages.extend(sorted(group.pages))
    
    return ordered_pages


# def extract_pages(pdf_path: Path, page_range: str, patterns: list[str] = None,
#                     template: str = None, source_page: int = 1,
#                     dry_run: bool = False, dedup_strategy: str = 'strict',
#                     use_timestamp: bool = False, custom_prefix: str = None,
#                     conflict_strategy: str = 'ask', interactive: bool = None) -> tuple[Path, float]:
def extract_pages(*args, **kwargs) -> tuple[Path, float]:
    """
    Extract specified pages with order preservation and enhanced deduplication.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with advanced syntax support
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction (overridden by pg specs)
        dry_run: Whether to perform actual extraction
        dedup_strategy: Deduplication strategy to apply
        use_timestamp: Whether to include timestamp in filenames
        custom_prefix: Custom prefix for output filenames
        conflict_strategy: How to handle existing files ('ask', 'overwrite', 'skip', 'rename', 'fail')
        interactive: Whether to allow interactive prompts (inferred from conflict_strategy if None)
        
    Returns:
        Tuple of (output_path, file_size) or (None, 0) if dry run or error
    """
    # Discard incoming parameters - use OpCtx instead
    args = None
    kwargs = None
    
    # Get all parameters from OpCtx
    pdf_path = OpCtx.current_pdf_path
    page_range = OpCtx.get_page_range_arg()
    patterns = OpCtx.patterns
    template = OpCtx.template
    source_page = OpCtx.source_page
    dry_run = OpCtx.dry_run
    dedup_strategy = OpCtx.dedup_strategy
    use_timestamp = OpCtx.use_timestamp
    custom_prefix = OpCtx.custom_prefix
    conflict_strategy = OpCtx.conflict_strategy
    interactive = OpCtx.interactive
    
    # If interactive not explicitly set, infer it from conflict_strategy
    if interactive is None:
        interactive = conflict_strategy == 'ask'
    
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range with grouping and order preservation
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        # Get ordered pages with deduplication applied
        ordered_pages = get_ordered_pages_from_groups(groups, pages_to_extract, dedup_strategy)
        
        if not ordered_pages:
            raise ValueError("No pages remaining after deduplication")
        
        # Use existing simple filename generation (no renamer complexity)
        output_path = generate_extraction_filename(pdf_path, range_desc, use_timestamp, custom_prefix)
        
        # Handle conflict resolution
        if not dry_run:
            # FIXED: Use interactive parameter instead of hardcoded True
            resolved_paths, skipped_paths = resolve_file_conflicts([output_path], conflict_strategy, interactive)
            
            if not resolved_paths:
                # User chose to skip or no conflict resolution
                console.print(f"[yellow]Skipping extraction: {output_path.name}[/yellow]")
                return None, 0
            
            output_path = resolved_paths[0]
        
        if dry_run:
            console.print(f"[cyan]Would create:[/cyan] {output_path.name}")
            return None, 0
        
        # Create output PDF
        writer = PdfWriter()
        for page_num in ordered_pages:
            if 1 <= page_num <= total_pages:
                writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed
        
        # Write output file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        file_size = output_path.stat().st_size / 1024 / 1024  # MB
        
        # Show page order information if order was preserved
        if any(getattr(group, 'preserve_order', False) for group in groups):
            console.print(f"[green]✓ Extracted pages in specified order: {', '.join(map(str, ordered_pages))}[/green]")
        else:
            console.print(f"[green]✓ Extracted {len(ordered_pages)} pages: {', '.join(map(str, ordered_pages))}[/green]")
        
        return output_path, file_size

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Error extracting pages from {pdf_path.name}: {e}[/red]")
        raise


# def extract_pages_grouped(pdf_path: Path, page_range: str, patterns: list[str] = None,
#                 template: str = None, source_page: int = 1,
#                 dry_run: bool = False, dedup_strategy: str = 'groups',
#                 use_timestamp: bool = False, custom_prefix: str = None,
#                 conflict_strategy: str = 'ask', interactive: bool = None) -> list[tuple[Path, float]]:
def extract_pages_grouped(*args, **kwargs) -> list[tuple[Path, float]]:
    """
    Extract pages respecting original groupings with order preservation and deduplication.
    FIXED: Handle list/PageGroup object inconsistencies properly.
    """
    
    # Discard incoming parameters - use OpCtx instead
    args = None
    kwargs = None
    
    # Get all parameters from OpCtx
    pdf_path = OpCtx.current_pdf_path
    page_range = OpCtx.get_page_range_arg()
    patterns = OpCtx.patterns
    template = OpCtx.template
    source_page = OpCtx.source_page
    dry_run = OpCtx.dry_run
    dedup_strategy = OpCtx.dedup_strategy
    use_timestamp = OpCtx.use_timestamp
    custom_prefix = OpCtx.custom_prefix
    conflict_strategy = OpCtx.conflict_strategy
    interactive = OpCtx.interactive
    
    # If interactive not explicitly set, infer it from conflict_strategy
    if interactive is None:
        interactive = conflict_strategy == 'ask'
    
    def handle_group_conflicts_and_dryrun(output_path: Path, group_idx: int, group_pages: list) -> Path | None:
        """Handle conflict resolution and dry run logic for a group."""
        if not dry_run:
            resolved_paths, skipped_paths = resolve_file_conflicts([output_path], conflict_strategy, interactive)
            
            if not resolved_paths:
                console.print(f"[yellow]Skipping group {group_idx+1}: {output_path.name}[/yellow]")
                return None
            
            return resolved_paths[0]
        else:
            console.print(f"[cyan]Group {group_idx+1} (pages {group_pages}) would create:[/cyan] {output_path.name}")
            return None
    
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range with grouping and order preservation
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        if not groups:
            # Fallback to single group
            ordered_pages = get_ordered_pages_from_groups([], pages_to_extract, dedup_strategy)
            from pdf_manipulator.core.page_range.page_group import PageGroup
            groups = [PageGroup(ordered_pages, False, range_desc)]
        
        # FIXED: Apply deduplication with robust error handling
        try:
            from pdf_manipulator.core.deduplication import apply_deduplication_strategy
            processed_groups, dedup_info = apply_deduplication_strategy(groups, dedup_strategy)
        except Exception as e:
            console.print(f"[yellow]Warning: Deduplication failed ({e}), using original groups[/yellow]")
            processed_groups = groups
        
        if not processed_groups:
            raise ValueError("No groups remaining after deduplication")
        
        output_files = []
        
        for group_idx, group in enumerate(processed_groups):
            # FIXED: Handle both PageGroup objects and raw lists robustly
            if hasattr(group, 'pages'):
                # It's a proper PageGroup object
                group_pages = group.pages
                if not group_pages:
                    continue  # Skip empty groups
            elif isinstance(group, list):
                # It's a raw list of page numbers (fallback from deduplication failure)
                group_pages = group
                if not group_pages:
                    continue
            else:
                # Unknown type - try to handle gracefully
                console.print(f"[yellow]Warning: Unknown group type {type(group)} at index {group_idx}[/yellow]")
                continue
            
            # Generate filename for this group using consistent naming
            if len(processed_groups) > 1:
                group_desc = f"group{group_idx+1:02d}"
            else:
                # Single group - use range description
                safe_range = range_desc.replace('-', '_').replace(',', '_')
                group_desc = f"pages_{safe_range}"
            
            # Use consistent filename generation
            output_path = generate_extraction_filename(pdf_path, group_desc, 'grouped', use_timestamp, custom_prefix)
            
            # Handle conflicts and dry run for this group
            resolved_output_path = handle_group_conflicts_and_dryrun(output_path, group_idx, group_pages)
            
            if resolved_output_path is None:
                continue  # Skip this group (dry run or user chose skip)
            
            # Create grouped PDF
            writer = PdfWriter()
            for page_num in group_pages:
                if 1 <= page_num <= total_pages:
                    writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed
            
            # Write group output file
            with open(resolved_output_path, 'wb') as output_file:
                writer.write(output_file)
            
            file_size = resolved_output_path.stat().st_size / 1024 / 1024  # MB
            output_files.append((resolved_output_path, file_size))
            
            # Show group extraction info
            preserve_order = hasattr(group, 'preserve_order') and getattr(group, 'preserve_order', False)
            if preserve_order:
                console.print(f"[green]✓ Group {group_idx+1} (pages in order): {', '.join(map(str, group_pages))}[/green]")
            else:
                console.print(f"[green]✓ Group {group_idx+1}: {len(group_pages)} pages[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting grouped pages from {pdf_path.name}: {e}[/red]")
        return []


# def extract_pages_separate(pdf_path: Path, page_range: str, patterns: list[str] = None,
#                     template: str = None, source_page: int = 1,
#                     dry_run: bool = False, dedup_strategy: str = 'strict',
#                     use_timestamp: bool = False, custom_prefix: str = None,
#                     conflict_strategy: str = 'ask', interactive: bool = None) -> list[tuple[Path, float]]:
def extract_pages_separate(*args, **kwargs) -> list[tuple[Path, float]]:
    """
    Extract each page as a separate file with order preservation and deduplication.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with advanced syntax support
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction (overridden by pg specs)
        dry_run: Whether to perform actual extraction
        dedup_strategy: Deduplication strategy to apply
        use_timestamp: Whether to include timestamp in filenames
        custom_prefix: Custom prefix for output filenames
        conflict_strategy: How to handle existing files ('ask', 'overwrite', 'skip', 'rename', 'fail')
        interactive: Whether to allow interactive prompts (inferred from conflict_strategy if None)
        
    Returns:
        List of (output_path, file_size) tuples for each created page file
    """
    # Discard incoming parameters - use OpCtx instead
    args = None
    kwargs = None
    
    # Get all parameters from OpCtx
    pdf_path = OpCtx.current_pdf_path
    page_range = OpCtx.get_page_range_arg()
    patterns = OpCtx.patterns
    template = OpCtx.template
    source_page = OpCtx.source_page
    dry_run = OpCtx.dry_run
    dedup_strategy = OpCtx.dedup_strategy
    use_timestamp = OpCtx.use_timestamp
    custom_prefix = OpCtx.custom_prefix
    conflict_strategy = OpCtx.conflict_strategy
    interactive = OpCtx.interactive
    
    # If interactive not explicitly set, infer it from conflict_strategy
    if interactive is None:
        interactive = conflict_strategy == 'ask'
    
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range with grouping and order preservation
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        # Get ordered pages with deduplication applied
        ordered_pages = get_ordered_pages_from_groups(groups, pages_to_extract, dedup_strategy)
        
        if not ordered_pages:
            raise ValueError("No pages remaining after deduplication")
        
        output_files = []
        
        for page_num in ordered_pages:
            # Generate filename for this page using existing simple logic
            page_desc = f"page{page_num:02d}"
            output_path = generate_extraction_filename(pdf_path, page_desc, use_timestamp, custom_prefix)
            
            # Handle conflict resolution for this page
            if not dry_run:
                # FIXED: Use interactive parameter instead of hardcoded True
                resolved_paths, skipped_paths = resolve_file_conflicts([output_path], conflict_strategy, interactive)
                
                if not resolved_paths:
                    # User chose to skip this page
                    console.print(f"[yellow]Skipping page {page_num}: {output_path.name}[/yellow]")
                    continue  # Skip this page, continue with next
                
                output_path = resolved_paths[0]  # Use the resolved path for this page

            if dry_run:
                console.print(f"[cyan]Page {page_num} would create:[/cyan] {output_path.name}")
                continue
            
            # Create single-page PDF
            writer = PdfWriter()
            if 1 <= page_num <= total_pages:
                writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed
            
            # Write output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            file_size = output_path.stat().st_size / 1024 / 1024  # MB
            output_files.append((output_path, file_size))
            
            console.print(f"[green]✓ Extracted page {page_num}:[/green] {output_path.name} ({file_size:.2f} MB)")
        
        if not dry_run and output_files:
            console.print(f"[green]✓ Created {len(output_files)} separate files[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting separate pages from {pdf_path.name}: {e}[/red]")
        return []


def analyze_pdf(pdf_path: Path) -> dict:
    """
    Analyze PDF structure and properties.
    
    Called by folder_operations.py for --analyze mode on files > 1MB or > 0.5MB per page.
    
    Returns:
        Dictionary with analysis results including page_count, file_size_mb, content info
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            
        # Basic analysis
        page_count = len(reader.pages)
        file_size = pdf_path.stat().st_size / 1024 / 1024  # MB
        size_per_page = file_size / page_count if page_count > 0 else 0
        
        analysis = {
            'file_path': pdf_path,
            'page_count': page_count,
            'file_size_mb': file_size,
            'size_per_page_mb': size_per_page,
            'has_images': False,
            'has_text': False,
            'is_malformed': False
        }
        
        # Sample a few pages to check content type
        pages_to_check = min(3, page_count)
        for i in range(pages_to_check):
            try:
                page = reader.pages[i]
                
                # Check for text content
                text_content = page.extract_text().strip()
                if text_content:
                    analysis['has_text'] = True
                
                # Check for images (basic detection via XObject resources)
                if '/Resources' in page and '/XObject' in page['/Resources']:
                    x_objects = page['/Resources']['/XObject']
                    for obj in x_objects.values():
                        if obj.get('/Subtype') == '/Image':
                            analysis['has_images'] = True
                            break
                            
            except Exception:
                # If we can't read a page, mark as potentially malformed
                analysis['is_malformed'] = True
        
        # Display analysis results
        console.print(f"\n[cyan]📊 Analysis: {pdf_path.name}[/cyan]")
        console.print(f"  📄 Pages: {page_count}")
        console.print(f"  📏 Size: {file_size:.2f} MB ({size_per_page:.2f} MB/page)")
        
        content_types = []
        if analysis['has_text']:
            content_types.append("Text")
        if analysis['has_images']: 
            content_types.append("Images")
        content_str = ", ".join(content_types) if content_types else "Unknown content"
        console.print(f"  📝 Content: {content_str}")
        
        if analysis['is_malformed']:
            console.print(f"  [yellow]⚠️  Potential issues detected[/yellow]")
        
        return analysis
        
    except Exception as e:
        console.print(f"[red]Error analyzing {pdf_path.name}: {e}[/red]")
        return {
            'file_path': pdf_path,
            'error': str(e),
            'page_count': 0,
            'file_size_mb': 0,
            'has_images': False,
            'has_text': False,
            'is_malformed': True
        }


def optimize_pdf(pdf_path: Path, quality: str = "default") -> tuple[Path, float]:
    """
    Optimize PDF file size using PyPDF compression.
    
    Called by folder_operations.py for --optimize mode.
    
    Args:
        pdf_path: PDF file to optimize
        quality: Optimization level ("default" or "aggressive")
        
    Returns:
        Tuple of (output_path, optimized_size_mb)
    """
    try:
        # Create optimized version filename
        output_path = pdf_path.parent / f"{pdf_path.stem}_optimized.pdf"
        
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # Add all pages to writer
            for page in reader.pages:
                writer.add_page(page)
            
            # Apply optimization based on quality setting
            if quality == "aggressive":
                # More aggressive compression - remove duplicates and compress streams
                writer.compress_identical_objects(remove_duplicates=True)
                for page in writer.pages:
                    page.compress_content_streams()
            else:
                # Default optimization - just compress identical objects
                writer.compress_identical_objects()
        
        # Write optimized file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        # Calculate new size
        new_size = output_path.stat().st_size / 1024 / 1024  # MB
        
        return output_path, new_size
        
    except Exception as e:
        console.print(f"[red]Error optimizing {pdf_path.name}: {e}[/red]")
        # Return original path and size if optimization fails
        original_size = pdf_path.stat().st_size / 1024 / 1024
        return pdf_path, original_size


def split_to_pages(pdf_path: Path, dry_run: bool = False) -> list[tuple[Path, float]]:
    """
    Split PDF into individual page files.
    
    Called by processor.py for --split-pages mode on single files.
    
    Args:
        pdf_path: PDF file to split
        dry_run: If True, show what would be done without creating files
        
    Returns:
        List of (output_path, file_size_mb) tuples for each created page file
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        if total_pages <= 1:
            console.print("[yellow]PDF has only one page - nothing to split[/yellow]")
            return []
        
        output_files = []
        
        if dry_run:
            console.print(f"[cyan]DRY RUN: Would split {pdf_path.name} into {total_pages} files[/cyan]")
            for page_num in range(1, total_pages + 1):
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num:02d}.pdf"
                console.print(f"[cyan]  Would create:[/cyan] {output_path.name}")
            return []
        
        # Actually split the pages
        console.print(f"[blue]Splitting {pdf_path.name} into {total_pages} pages...[/blue]")
        
        for page_num in range(1, total_pages + 1):
            # Create output path for this page
            output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num:02d}.pdf"
            
            # Create single-page PDF
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed
            
            # Write output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            file_size = output_path.stat().st_size / 1024 / 1024  # MB
            output_files.append((output_path, file_size))
            
            # Show progress for each page
            console.print(f"[green]  ✓ Created page {page_num}:[/green] {output_path.name} ({file_size:.2f} MB)")
        
        console.print(f"[green]✓ Split complete: {len(output_files)} files created[/green]")
        return output_files
        
    except Exception as e:
        console.print(f"[red]Error splitting {pdf_path.name}: {e}[/red]")
        return []


# End of file #
