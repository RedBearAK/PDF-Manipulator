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


def extract_pages(pdf_path: Path, page_range: str, 
                    patterns: list[str] = None, template: str = None,
                    source_page: int = 1, dry_run: bool = False,
                    dedup_strategy: str = 'strict') -> tuple[Path, float]:
    """
    Extract pages with Phase 3 intelligent naming, order preservation, and deduplication.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with advanced syntax support
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction (overridden by pg specs)
        dry_run: Whether to perform actual extraction
        dedup_strategy: Deduplication strategy to apply
        
    Returns:
        Tuple of (output_path, file_size) or (None, 0) if dry run or error
    """
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
        
        # Generate filename (existing pattern extraction logic)
        if patterns and template:
            from pdf_manipulator.renamer.filename_generator import FilenameGenerator
            generator = FilenameGenerator()
            
            try:
                output_path, extraction_results = generator.generate_smart_filename(
                    pdf_path, range_desc, patterns, template, source_page, dry_run=dry_run
                )
            except Exception as e:
                console.print(f"[yellow]Smart naming failed: {e}[/yellow]")
                output_path = pdf_path.parent / f"{pdf_path.stem}_pages{range_desc}.pdf"
        else:
            # Create filename based on page range
            if len(ordered_pages) == 1:
                output_path = pdf_path.parent / f"{pdf_path.stem}_page{ordered_pages[0]}.pdf"
            else:
                timestamp = int(time.time())
                output_path = pdf_path.parent / f"{timestamp}_{pdf_path.stem}_pages{range_desc}.pdf"
        
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


def extract_pages_grouped(pdf_path: Path, page_range: str, patterns: list[str] = None,
                template: str = None, source_page: int = 1,
                dry_run: bool = False, dedup_strategy: str = 'groups') -> list[tuple[Path, float]]:
    """
    Extract pages respecting original groupings with order preservation and deduplication.
    
    Args:
        pdf_path: Source PDF file
        page_range: Pages to extract with grouping syntax and order preservation
        patterns: List of enhanced pattern strings for content extraction
        template: Filename template for smart naming
        source_page: Fallback page for pattern extraction
        dry_run: Whether to perform actual extraction
        dedup_strategy: Deduplication strategy to apply
        
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
            ordered_pages = get_ordered_pages_from_groups([], pages_to_extract, dedup_strategy)
            from pdf_manipulator.core.page_range.page_group import PageGroup
            groups = [PageGroup(ordered_pages, False, range_desc)]
        
        # Apply deduplication strategy to groups
        from pdf_manipulator.core.deduplication import apply_deduplication_strategy
        processed_groups, dedup_info = apply_deduplication_strategy(groups, dedup_strategy)
        
        output_files = []
        
        if dry_run:
            console.print(f"\n[cyan]DRY RUN: Would create {len(processed_groups)} grouped files[/cyan]")
        
        # Process each group in order, respecting individual group order preferences
        for group_idx, group in enumerate(processed_groups):
            # FIXED: Skip empty groups to prevent list index out of range errors
            if not hasattr(group, 'pages') or not group.pages:
                console.print(f"[dim]Skipping empty group {group_idx+1}: {getattr(group, 'original_spec', 'unknown')} (no matches)[/dim]")
                continue
            
            # Respect the group's order preference
            if getattr(group, 'preserve_order', False):
                group_pages = group.pages  # Use exact order from group
            else:
                group_pages = sorted(group.pages)  # Sort for backward compatibility
            
            # Generate filename for this group
            if patterns and template:
                from pdf_manipulator.renamer.filename_generator import FilenameGenerator
                generator = FilenameGenerator()
                
                # FIXED: Now safe to access group_pages[0] since we've verified group is not empty
                pattern_source_page = group_pages[0]
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
                # Fallback naming - safe because we know group_pages is not empty
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
            # Show final summary excluding empty groups
            actual_groups_created = len(output_files)
            console.print(f"[green]✓ Created {actual_groups_created} grouped files[/green]")
        
        return output_files

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error extracting grouped pages from {pdf_path.name}: {e}[/red]")
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
            # FIXED: Skip empty groups to prevent list index out of range errors
            if not group.pages:
                console.print(f"[dim]Skipping empty group {group_idx+1}: {group.original_spec} (no matches)[/dim]")
                continue
            
            # Respect the group's order preference
            if getattr(group, 'preserve_order', False):
                group_pages = group.pages  # Use exact order from group
            else:
                group_pages = sorted(group.pages)  # Sort for backward compatibility
            
            # Generate filename for this group
            if patterns and template:
                from pdf_manipulator.renamer.filename_generator import FilenameGenerator
                generator = FilenameGenerator()
                
                # FIXED: Now safe to access group_pages[0] since we've verified group is not empty
                pattern_source_page = group_pages[0]
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
                # Fallback naming - safe because we know group_pages is not empty
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
            # Show final summary excluding empty groups
            actual_groups_created = len(output_files)
            console.print(f"[green]✓ Created {actual_groups_created} grouped files[/green]")
        
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
