"""
Enhanced folder operations with batch pattern extraction and smart naming support.
File: pdf_manipulator/core/folder_operations.py

PHASE 2 ENHANCEMENTS:
- Batch processing with pattern extraction and smart naming
- Dry-run support for folder operations
- Consistent pattern argument handling across all modes
- Enhanced error handling and user feedback
"""

import argparse

from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

from pdf_manipulator.ui import decide_extraction_mode, show_folder_help
from pdf_manipulator.core.parser import parse_page_range
from pdf_manipulator.core.processor import process_multipage_pdfs
from pdf_manipulator.core.operations import (
    analyze_pdf,
    optimize_pdf,
    extract_pages,
    extract_pages_grouped,
    extract_pages_separate,
    split_to_pages,
)
from pdf_manipulator.core.operation_context import OpCtx
from pdf_manipulator.core.malformation_utils import check_and_fix_malformation_with_args
from pdf_manipulator.core.warning_suppression import suppress_all_pdf_warnings
from pdf_manipulator.ui_enhanced import format_page_ranges, show_page_selection_preview

console = Console()


def _extract_pattern_and_template_args(args: argparse.Namespace) -> tuple[list[str], str, int]:
    """
    Extract pattern and template arguments from args object.
    
    PHASE 2: Centralized pattern argument extraction.
    """
    patterns = getattr(args, 'scrape_pattern', None)
    template = getattr(args, 'filename_template', None)
    source_page = getattr(args, 'pattern_source_page', 1)
    
    # Handle patterns from file
    if getattr(args, 'scrape_patterns_file', None):
        try:
            with open(args.scrape_patterns_file, 'r') as f:
                file_patterns = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        file_patterns.append(line)
                patterns = file_patterns
        except Exception as e:
            console.print(f"[red]Error reading patterns file: {e}[/red]")
            patterns = None
    
    return patterns, template, source_page


def _show_batch_pattern_preview(pdf_files: list[tuple[Path, int, float]], 
                               patterns: list[str], template: str, source_page: int):
    """
    Show pattern extraction preview for batch operations.
    
    PHASE 2: Preview pattern extraction for first few files in batch.
    """
    if not patterns or not template:
        return
    
    console.print(f"\n[cyan]Batch Pattern Preview (first 3 files):[/cyan]")
    
    try:
        from pdf_manipulator.renamer.filename_generator import FilenameGenerator
        
        generator = FilenameGenerator()
        
        for i, (pdf_path, page_count, file_size) in enumerate(pdf_files[:3]):
            console.print(f"\n[dim]{pdf_path.name}:[/dim]")
            
            try:
                preview = generator.preview_filename_generation(
                    pdf_path, "preview", patterns, template, source_page
                )
                
                for var_name, details in preview.get('extraction_preview', {}).items():
                    console.print(f"  {var_name}: {details['simulated_value']}")
                
                console.print(f"  → {preview['filename_preview']}")
                
            except Exception as e:
                console.print(f"  [yellow]Preview failed: {e}[/yellow]")
        
        if len(pdf_files) > 3:
            console.print(f"[dim]... and {len(pdf_files) - 3} more files[/dim]")
            
    except Exception as e:
        console.print(f"[yellow]Batch pattern preview failed: {e}[/yellow]")


def handle_folder_operations(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Main dispatcher for folder operations."""

    if args.analyze:
        process_analyze_mode(args, pdf_files)
    elif args.optimize:
        process_optimize_mode(args, pdf_files)
    elif args.extract_pages or args.split_pages:
        process_extract_split_mode(args, pdf_files)
    else:
        show_folder_help(pdf_files)


def process_analyze_mode(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle analyze mode for folder operations."""

    console.print("\n[blue]Analysis mode[/blue]")
    
    # Analyze large PDFs (> 1MB or > 0.5MB per page)
    for pdf_path, page_count, file_size in pdf_files:
        size_per_page = file_size / page_count if page_count > 0 else 0
        if file_size > 1.0 or size_per_page > 0.5:
            analyze_pdf(pdf_path)


def process_optimize_mode(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle optimize mode for folder operations."""
    
    console.print("\n[blue]Optimization mode[/blue]")
    
    for pdf_path, _, file_size in pdf_files:
        if args.batch or Confirm.ask(f"Optimize {pdf_path.name}?", default=True):
            output_path, new_size = optimize_pdf(pdf_path)
            if output_path:
                console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                            f"({file_size:.2f} MB → {new_size:.2f} MB)")


def process_extract_split_mode(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle extract/split mode for folder operations."""

    # PHASE 2: Extract pattern and template arguments
    patterns, template, source_page = _extract_pattern_and_template_args(args)
    dry_run = getattr(args, 'dry_run', False)

    # Determine operation
    if args.extract_pages:
        operation = "extract"
        console.print(f"\n[blue]Extract pages mode: {args.extract_pages}[/blue]")

        if args.respect_groups:
            console.print("[dim]Mode: Respect groupings (ranges→multi-page, "
                            "individuals→single)[/dim]")
        elif args.separate_files:
            console.print("[dim]Mode: Extract as separate files[/dim]")
        else:
            console.print("[dim]Mode: Extract as single document[/dim]")
            
        # PHASE 2: Show pattern preview for batch operations
        if patterns and template and not args.batch:
            _show_batch_pattern_preview(pdf_files, patterns, template, source_page)
    else:
        operation = "split"
        console.print("\n[blue]Split pages mode[/blue]")

    # Show dry-run indicator
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be created[/yellow]")

    # Extra warning for batch mode with replace
    if args.batch and args.replace and not dry_run:
        if operation == "extract":
            console.print(f"[red]WARNING: This will extract pages {args.extract_pages} "
                            "from ALL PDFs and replace originals![/red]")
        else:
            console.print("[red]WARNING: This will split ALL multi-page PDFs and "
                            "replace originals![/red]")
        if not Confirm.ask("Are you absolutely sure?", default=False):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

    # Process based on mode
    if args.batch:
        if operation == "extract":
            process_batch_extract(args, pdf_files, patterns, template, source_page, dry_run)
        else:
            process_batch_split(args, pdf_files, dry_run)
    else:
        if operation == "extract":
            process_interactive_extract(args, pdf_files, patterns, template, source_page, dry_run)
        else:
            # Split mode - only multi-page PDFs
            process_multipage_pdfs(pdf_files, "split", args.replace)


def process_batch_extract(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]],
                            patterns: list[str], template: str, source_page: int, dry_run: bool):
    """Handle batch extraction processing with pattern support."""

    # Extract enhanced arguments including conflict strategy
    from pdf_manipulator.cli import extract_enhanced_args
    enhanced_args = extract_enhanced_args(args)

    suppress_context = suppress_all_pdf_warnings() if not dry_run else None
    
    with suppress_context if suppress_context else _null_context():
        # For extract, process all PDFs (not just multi-page)
        for pdf_path, page_count, file_size in pdf_files:
            console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")

            # CRITICAL: Set PDF context BEFORE any parsing operations
            OpCtx.set_current_pdf(pdf_path, page_count)

            try:
                # Validate extraction for this PDF (early error detection)
                from pdf_manipulator.core.parser import parse_page_range_from_args
                pages_to_extract, desc, groups = parse_page_range_from_args(args, page_count, pdf_path)
                
                # Variables above are intentionally unused - this is validation only
                # Operations functions do their own parsing internally
                
                if args.respect_groups:
                    # Extract with groupings respected
                    output_files = extract_pages_grouped(
                        pdf_path=pdf_path,
                        page_range=args.extract_pages,
                        patterns=patterns,
                        template=template,
                        source_page=source_page,
                        dry_run=dry_run,
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_files and not dry_run:
                        console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
                        if args.replace:
                            pdf_path.unlink()
                            console.print("[yellow]✓ Deleted original[/yellow]")
                            
                elif args.separate_files:
                    # Extract as separate files
                    output_files = extract_pages_separate(
                        pdf_path=pdf_path,
                        page_range=args.extract_pages,
                        patterns=patterns,
                        template=template,
                        source_page=source_page,
                        dry_run=dry_run,
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_files and not dry_run:
                        console.print(f"[green]✓ Created {len(output_files)} separate files[/green]")
                        if args.replace:
                            pdf_path.unlink()
                            console.print("[yellow]✓ Deleted original[/yellow]")
                else:
                    # Extract as single document
                    output_path, new_size = extract_pages(
                        pdf_path=pdf_path,
                        page_range=args.extract_pages,
                        patterns=patterns,
                        template=template,
                        source_page=source_page,
                        dry_run=dry_run,
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter  
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_path and not dry_run:
                        console.print(f"[green]✓ Created:[/green] {output_path.name}")
                        if args.replace:
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
                            console.print("[yellow]✓ Replaced original[/yellow]")

            except ValueError as e:
                console.print(f"[yellow]Skipping {pdf_path.name}: {e}[/yellow]")


def process_batch_split(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]], dry_run: bool):
    """Handle batch split processing."""

    suppress_context = suppress_all_pdf_warnings() if not dry_run else None
    
    with suppress_context if suppress_context else _null_context():
        # Split mode - only multi-page PDFs
        multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]
        for pdf_path, page_count, file_size in multi_page_pdfs:
            console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")

            # CRITICAL: Set PDF context for consistency (though split doesn't use parsing)
            OpCtx.set_current_pdf(pdf_path, page_count)

            output_files = split_to_pages(pdf_path, dry_run)
            if output_files and not dry_run:
                console.print(f"[green]✓ Split into {len(output_files)} files[/green]")
                if args.replace:
                    pdf_path.unlink()
                    console.print("[yellow]✓ Deleted original[/yellow]")



def process_interactive_extract(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]],
                                patterns: list[str], template: str, source_page: int, dry_run: bool):
    """Handle interactive extraction processing with pattern support."""
    
    # Extract enhanced arguments including conflict strategy
    from pdf_manipulator.cli import extract_enhanced_args
    enhanced_args = extract_enhanced_args(args)
    
    suppress_context = suppress_all_pdf_warnings() if not dry_run else None
    
    with suppress_context if suppress_context else _null_context():
        for pdf_path, page_count, file_size in pdf_files:
            try:
                # CRITICAL: Set PDF context BEFORE any parsing operations
                OpCtx.set_current_pdf(pdf_path, page_count)
                
                # Validate extraction for this PDF (early error detection)
                from pdf_manipulator.core.parser import parse_page_range_from_args
                pages_to_extract, desc, groups = parse_page_range_from_args(args, page_count, pdf_path)
                
                # # Show extraction preview
                # page_list = format_page_ranges(pages_to_extract)
                # console.print(f"[blue]Would extract pages: {page_list}[/blue]")

                # Show unmatched pages info
                show_page_selection_preview(pages_to_extract, page_count)
                
                # Ask user for confirmation
                from rich.prompt import Confirm
                proceed = Confirm.ask(f"Extract from {pdf_path.name}?", default=True)
                
                if not proceed:
                    console.print(f"[dim]Skipped {pdf_path.name}[/dim]")
                    continue
                
                # Determine extraction mode
                extraction_mode = 'single'  # Default
                if args.respect_groups:
                    extraction_mode = 'grouped'
                elif args.separate_files:
                    extraction_mode = 'separate'
                elif len(groups) > 1:
                    from pdf_manipulator.ui import decide_extraction_mode
                    extraction_mode = decide_extraction_mode(pages_to_extract, groups, True)
                
                if extraction_mode == 'separate':
                    # Extract as separate files
                    output_files = extract_pages_separate(
                        pdf_path=pdf_path, 
                        page_range=args.extract_pages, 
                        patterns=patterns, 
                        template=template, 
                        source_page=source_page, 
                        dry_run=dry_run, 
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_files and not dry_run:
                        total_size = sum(size for _, size in output_files)
                        console.print(f"[green]✓ Created {len(output_files)} files:[/green]")
                        for out_path, out_size in output_files:
                            console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                        if args.replace and Confirm.ask("Delete original file?", default=False):
                            pdf_path.unlink()
                            console.print("[green]✓ Original file deleted[/green]")
                            
                elif extraction_mode == 'grouped':
                    # Extract with groupings respected
                    output_files = extract_pages_grouped(
                        pdf_path=pdf_path, 
                        page_range=args.extract_pages, 
                        patterns=patterns, 
                        template=template, 
                        source_page=source_page, 
                        dry_run=dry_run, 
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_files and not dry_run:
                        total_size = sum(size for _, size in output_files)
                        console.print(f"[green]✓ Created {len(output_files)} grouped files:[/green]")
                        for out_path, out_size in output_files:
                            console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                        if args.replace and Confirm.ask("Delete original file?", default=False):
                            pdf_path.unlink()
                            console.print("[green]✓ Original file deleted[/green]")
                else:
                    # Extract as single document
                    output_path, new_size = extract_pages(
                        pdf_path=pdf_path, 
                        page_range=args.extract_pages, 
                        patterns=patterns, 
                        template=template, 
                        source_page=source_page, 
                        dry_run=dry_run, 
                        dedup_strategy=enhanced_args['dedup_strategy'],
                        use_timestamp=getattr(args, 'timestamp', False),
                        custom_prefix=getattr(args, 'name_prefix', None),
                        conflict_strategy=enhanced_args['conflict_strategy'],  # FIXED: Added this parameter
                        interactive=enhanced_args['interactive']  # FIXED: Added this parameter
                    )
                    if output_path and not dry_run:
                        console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                        if file_size > 0:
                            console.print(f"[dim]Size: {((new_size / file_size) * 100):.1f}% of original[/dim]")
                        if args.replace and Confirm.ask("Replace original file?", default=False):
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
                            console.print("[green]✓ Original file replaced[/green]")

            except ValueError as e:
                console.print(f"[yellow]Cannot extract from this PDF: {e}[/yellow]")


def _null_context():
    """Return a null context manager for conditional context usage."""
    from contextlib import nullcontext
    return nullcontext()


# End of file #
