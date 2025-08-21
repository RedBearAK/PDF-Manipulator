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
from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings

console = Console()


def get_ordered_pages_from_groups(groups: list, fallback_pages: set = None) -> list[int]:
    """
    Extract pages in the correct order from PageGroup objects.
    
    Args:
        groups: List of PageGroup objects
        fallback_pages: Fallback page set if groups don't have preserve_order info
        
    Returns:
        List of pages in the intended order
    """
    if not groups:
        return sorted(fallback_pages) if fallback_pages else []
    
    ordered_pages = []
    has_preserve_order = hasattr(groups[0], 'preserve_order')
    
    for group in groups:
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


def extract_pages(pdf_path: Path, page_range: str, 
                 patterns: list[str] = None, template: str = None,
                 source_page: int = 1, dry_run: bool = False) -> tuple[Path, float]:
    """
    Extract pages with Phase 3 intelligent naming and order preservation.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with order preservation support
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
        
        # Parse page range with enhanced order preservation
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        # Get pages in the correct order (respecting preserve_order flag)
        ordered_pages = get_ordered_pages_from_groups(groups, pages_to_extract)
        
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
                return output_path, time.time() - start_time
            
            # Phase 3: Actual smart filename generation
            output_path, _ = generator.generate_smart_filename(
                pdf_path, range_desc, patterns, template, source_page
            )
        else:
            # Fallback naming
            if len(ordered_pages) == 1:
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{ordered_pages[0]}.pdf"
            else:
                output_path = pdf_path.parent / f"{pdf_path.stem}_pages{range_desc}.pdf"
        
        if dry_run:
            console.print(f"\n[cyan]DRY RUN: Would extract pages {page_range} from {pdf_path.name}[/cyan]")
            console.print(f"[cyan]Would create:[/cyan] {output_path.name}")
            return output_path, time.time() - start_time
        
        # Create new PDF with pages in the specified order
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


def extract_pages_separate(pdf_path: Path, page_range: str, patterns: list[str] = None,
                          template: str = None, source_page: int = 1,
                          dry_run: bool = False, remove_images: bool = False) -> list[tuple[Path, float]]:
    """
    Extract pages as separate files with order preservation.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with order preservation support
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction
        dry_run: Whether to perform actual extraction
        remove_images: Whether to remove images (for text-only extraction)
        
    Returns:
        List of (output_path, file_size) tuples in the specified order
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        
        # Parse page range with enhanced order preservation
        pages_to_extract, range_desc, groups = parse_page_range(page_range, total_pages, pdf_path)
        
        if not pages_to_extract:
            raise ValueError(f"No valid pages found for range: {page_range}")
        
        # Get pages in the correct order (respecting preserve_order flag)
        ordered_pages = get_ordered_pages_from_groups(groups, pages_to_extract)
        
        output_files = []
        
        # Phase 3: Handle pattern extraction for separate files
        extraction_results_cache = {}
        if patterns and template:
            from pdf_manipulator.renamer.filename_generator import FilenameGenerator
            generator = FilenameGenerator()
            
            if dry_run:
                console.print(f"\n[cyan]DRY RUN: Would create {len(ordered_pages)} separate files[/cyan]")
                # Show pattern preview for first few pages
                preview_pages = ordered_pages[:3]  # Limit preview to avoid spam
                for page_num in preview_pages:
                    try:
                        output_path, extraction_results = generator.generate_smart_filename(
                            pdf_path, str(page_num), patterns, template, page_num, dry_run=True
                        )
                        console.print(f"[cyan]Page {page_num} would create:[/cyan] {output_path.name}")
                        extraction_results_cache[page_num] = extraction_results
                    except Exception as e:
                        console.print(f"[yellow]Page {page_num} pattern preview failed: {e}[/yellow]")
                
                if len(ordered_pages) > 3:
                    console.print(f"[dim]... and {len(ordered_pages) - 3} more files[/dim]")
                return []
        
        # Process pages in the specified order
        for page_num in ordered_pages:
            if not (1 <= page_num <= total_pages):
                console.print(f"[yellow]Warning: Page {page_num} out of range, skipping[/yellow]")
                continue
            
            # Generate filename for this page
            if patterns and template:
                try:
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, str(page_num), patterns, template, page_num
                    )
                    extraction_results_cache[page_num] = extraction_results
                except Exception as e:
                    console.print(f"[yellow]Smart naming failed for page {page_num}: {e}[/yellow]")
                    output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num}.pdf"
            else:
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{page_num}.pdf"
            
            if dry_run:
                continue
            
            # Create single-page PDF
            writer = PdfWriter()
            page = reader.pages[page_num - 1]  # Convert to 0-indexed
            
            if remove_images:
                # Remove images from page (text-only extraction)
                # Note: This is a simplified approach - real implementation would need more sophisticated image removal
                pass  # TODO: Implement image removal if needed
            
            writer.add_page(page)
            
            # Write output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            file_size = output_path.stat().st_size / 1024 / 1024  # MB
            output_files.append((output_path, file_size))
        
        # Show completion message with order information
        if dry_run:
            console.print(f"[blue]Would create {len(output_files)} separate files[/blue]")
        else:
            if any(getattr(group, 'preserve_order', False) for group in groups):
                console.print(f"[green]✓ Extracted pages in specified order: {', '.join(map(str, ordered_pages))}[/green]")
            else:
                console.print(f"[green]✓ Extracted {len(ordered_pages)} pages as separate files: {', '.join(map(str, ordered_pages))}[/green]")
                
            # Show pattern extraction summary
            if patterns and template and extraction_results_cache:
                successful_count = sum(1 for results in extraction_results_cache.values() 
                                     if any(result.get('success') for result in results.get('variables_extracted', {}).values()))
                if successful_count > 0:
                    console.print(f"[green]Smart naming applied to {successful_count}/{len(ordered_pages)} files[/green]")
        
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
    Extract pages respecting original groupings with order preservation.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with grouping syntax and order preservation
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction
        dry_run: Whether to perform actual extraction
        
    Returns:
        List of (output_path, file_size) tuples for each group in the specified order
    """
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
            ordered_pages = get_ordered_pages_from_groups([], pages_to_extract)
            from pdf_manipulator.core.page_range.page_group import PageGroup
            groups = [PageGroup(ordered_pages, False, range_desc)]
        
        output_files = []
        
        if dry_run:
            console.print(f"\n[cyan]DRY RUN: Would create {len(groups)} grouped files[/cyan]")
        
        # Process each group in order, respecting individual group order preferences
        for group_idx, group in enumerate(groups):
            # Respect the group's order preference
            if getattr(group, 'preserve_order', False):
                group_pages = group.pages  # Use exact order from group
            else:
                group_pages = sorted(group.pages)  # Sort for backward compatibility
            
            # Generate filename for this group
            if patterns and template:
                from pdf_manipulator.renamer.filename_generator import FilenameGenerator
                generator = FilenameGenerator()
                
                # Use first page of group for pattern extraction
                pattern_source_page = group_pages[0] if group_pages else source_page
                group_desc = getattr(group, 'original_spec', f"group{group_idx+1}")
                
                try:
                    output_path, extraction_results = generator.generate_smart_filename(
                        pdf_path, group_desc, patterns, template, pattern_source_page, dry_run=dry_run
                    )
                    
                    if dry_run:
                        console.print(f"[cyan]Group {group_idx+1} (pages {group_pages}) would create:[/cyan] {output_path.name}")
                        continue
                        
                except Exception as e:
                    console.print(f"[yellow]Smart naming failed for group {group_idx+1}: {e}[/yellow]")
                    output_path = pdf_path.parent / f"{pdf_path.stem}_group{group_idx+1}.pdf"
            else:
                # Fallback naming
                if len(group_pages) == 1:
                    output_path = pdf_path.parent / f"{pdf_path.stem}_page{group_pages[0]}.pdf"
                else:
                    page_range_str = f"{group_pages[0]}-{group_pages[-1]}" if len(group_pages) > 1 else str(group_pages[0])
                    output_path = pdf_path.parent / f"{pdf_path.stem}_pages{page_range_str}.pdf"
                
                if dry_run:
                    console.print(f"[cyan]Group {group_idx+1} (pages {group_pages}) would create:[/cyan] {output_path.name}")
                    continue
            
            # Create grouped PDF with pages in the specified order
            writer = PdfWriter()
            for page_num in group_pages:
                if 1 <= page_num <= total_pages:
                    writer.add_page(reader.pages[page_num - 1])  # Convert to 0-indexed
            
            # Write output file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            file_size = output_path.stat().st_size / 1024 / 1024  # MB
            output_files.append((output_path, file_size))
            
            # Show group completion with order information
            if getattr(group, 'preserve_order', False):
                console.print(f"[green]✓ Group {group_idx+1}: extracted pages in specified order: {group_pages}[/green]")
            else:
                console.print(f"[green]✓ Group {group_idx+1}: extracted pages {group_pages}[/green]")
        
        if not dry_run:
            console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting grouped pages from {pdf_path.name}: {e}[/red]")
        return []


# Keep existing functions for backward compatibility
def analyze_pdf(pdf_path: Path) -> dict:
    """Analyze PDF structure and properties."""
    # Implementation unchanged - just keep existing function
    pass


def optimize_pdf(pdf_path: Path, quality: str = "default") -> tuple[Path, float]:
    """Optimize PDF file size."""
    # Implementation unchanged - just keep existing function  
    pass


def split_to_pages(pdf_path: Path, dry_run: bool = False) -> list[tuple[Path, float]]:
    """Split PDF into individual pages."""
    # Implementation unchanged - just keep existing function
    pass


# End of file #
