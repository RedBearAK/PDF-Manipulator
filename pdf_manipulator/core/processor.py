"""High-level processing coordination."""

import argparse

from pathlib import Path
from rich.prompt import Confirm
from rich.console import Console

from pdf_manipulator.ui import *
from pdf_manipulator.core.scanner import *
from pdf_manipulator.core.operations import *
from pdf_manipulator.core.detailed_analysis import handle_detailed_analysis
from pdf_manipulator.core.malformation_utils import ensure_pdf_ready_for_optimization


console = Console()


def process_single_file_operations(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Process operations on a single PDF file."""
    if any([
        args.extract_pages,
        args.split_pages,
        args.optimize,
        args.analyze,
        args.analyze_detailed
        ]):
        pdf_path, page_count, file_size = pdf_files[0]
        process_single_pdf(pdf_path, page_count, file_size, args)
    else:
        # No operation specified - just show info
        from ..ui import show_single_file_help
        show_single_file_help(pdf_files[0][1])  # Pass page count


def process_single_file_mode(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle all single file processing logic."""
    pdf_path, page_count, file_size = pdf_files[0]
    
    if any([
        args.extract_pages,
        args.split_pages,
        args.optimize,
        args.analyze,
        args.analyze_detailed
        ]):
        process_single_pdf(pdf_path, page_count, file_size, args)
    else:
        # Show available operations
        if page_count > 1:
            # Move the console.print statements here
            pass


def process_single_pdf(pdf_path: Path, page_count: int, file_size: float,
                        args: argparse.Namespace):
    """Process a single PDF file based on the specified operation."""
    if args.analyze:
        analyze_pdf(pdf_path)

    elif args.analyze_detailed:
        # Pass the no_auto_fix flag from args
        handle_detailed_analysis(pdf_path, getattr(args, 'no_auto_fix', False))

    elif args.optimize:
        # NEW: Check and fix malformation before optimizing
        ready_pdf_path = ensure_pdf_ready_for_optimization(
            pdf_path, 
            batch_mode=getattr(args, 'batch', False),
            no_auto_fix=getattr(args, 'no_auto_fix', False)
        )
        
        if ready_pdf_path is None:
            return  # User cancelled
        
        # Use the potentially fixed PDF for optimization
        if args.batch or Confirm.ask(f"Optimize {ready_pdf_path.name}?", default=True):
            output_path, new_size = optimize_pdf(ready_pdf_path)
            if output_path:
                console.print(f"[green]✓ Optimized:[/green] {output_path.name} "
                            f"({file_size:.2f} MB → {new_size:.2f} MB)")
                
                # Show if malformation fixing contributed to size reduction
                if ready_pdf_path != pdf_path:
                    console.print("[dim]Size reduction includes malformation repair[/dim]")
                    
                if args.replace and Confirm.ask("Replace original file?", default=False):
                    pdf_path.unlink()
                    output_path.rename(pdf_path)
                    console.print("[green]✓ Original file replaced[/green]")

    elif args.extract_pages:
        # The existing extraction logic can stay mostly the same
        # The malformation checking happens in the malformation_checker.py
        # which should be updated to use the legacy wrapper
        
        # Validate that extraction makes sense for this PDF
        try:

            from pdf_manipulator.core.parser import parse_page_range_from_args
            pages_to_extract, desc, groups = parse_page_range_from_args(args, page_count, pdf_path)

            # pages_to_extract, _, groups = parse_page_range(args.extract_pages, page_count, pdf_path)

            if len(pages_to_extract) == page_count:
                console.print("[yellow]Extracting all pages - consider using --optimize instead[/yellow]")

            # Determine extraction mode
            if args.respect_groups:
                extraction_mode = 'grouped'
            elif args.separate_files:
                extraction_mode = 'separate'
            elif not args.batch:
                extraction_mode = decide_extraction_mode(pages_to_extract, groups, True)
            else:
                extraction_mode = 'single'

            if args.batch or Confirm.ask(f"Extract pages {args.extract_pages} from {pdf_path.name}?", default=True):
                if extraction_mode == 'separate':
                    # Extract as separate files
                    output_files = extract_pages_separate(pdf_path, args.extract_pages)
                    if output_files:
                        total_size = sum(size for _, size in output_files)
                        console.print(f"[green]✓ Created {len(output_files)} files:[/green]")
                        for out_path, out_size in output_files:
                            console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                        if file_size > 0:
                            console.print(f"[dim]Total size: {((total_size / file_size) * 100):.1f}% of original[/dim]")
                        if args.replace and Confirm.ask("Replace original file?", default=False):
                            pdf_path.unlink()
                            console.print("[green]✓ Original file deleted[/green]")
                elif extraction_mode == 'grouped':
                    # Extract with groupings respected
                    output_files = extract_pages_grouped(pdf_path, args.extract_pages)
                    if output_files:
                        total_size = sum(size for _, size in output_files)
                        console.print(f"[green]✓ Created {len(output_files)} grouped files:[/green]")
                        for out_path, out_size in output_files:
                            console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                        if file_size > 0:
                            console.print(f"[dim]Total size: {((total_size / file_size) * 100):.1f}% of original[/dim]")
                        if args.replace and Confirm.ask("Replace original file?", default=False):
                            pdf_path.unlink()
                            console.print("[green]✓ Original file deleted[/green]")
                else:
                    # Extract as single document
                    output_path, new_size = extract_pages(pdf_path, args.extract_pages)
                    if output_path:
                        console.print(f"[green]✓ Created:[/green] {output_path.name} ({new_size:.2f} MB)")
                        if file_size > 0:
                            console.print(f"[dim]Size: {((new_size / file_size) * 100):.1f}% of original[/dim]")
                        if args.replace and Confirm.ask("Replace original file?", default=False):
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
                            console.print("[green]✓ Original file replaced[/green]")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")

    elif args.split_pages:
        if page_count == 1:
            console.print("[yellow]PDF already has only one page[/yellow]")
        else:
            if args.batch or Confirm.ask(f"Split into {page_count} separate files?", default=False):
                output_files = split_to_pages(pdf_path)
                if output_files:
                    console.print(f"[green]✓ Split into {len(output_files)} files:[/green]")
                    for out_path, out_size in output_files:
                        console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                    if args.replace and Confirm.ask("Delete original file?", default=False):
                        pdf_path.unlink()
                        console.print("[green]✓ Original file deleted[/green]")


def process_multipage_pdfs(pdf_files: list[tuple[Path, int, float]], 
                            operation: str,
                            replace_original: bool = False):
    """Process multi-page PDFs based on the chosen operation (split only now)."""
    multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]

    if not multi_page_pdfs:
        console.print("[green]No multi-page PDFs found![/green]")
        return

    console.print(f"\n[yellow]Found {len(multi_page_pdfs)} multi-page PDFs[/yellow]")

    for pdf_path, page_count, file_size in multi_page_pdfs:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        if not Confirm.ask(f"Split into {page_count} separate files?", default=False):
            continue

        output_files = split_to_pages(pdf_path)
        if output_files:
            console.print(f"[green]✓ Split into {len(output_files)} files:[/green]")
            for out_path, out_size in output_files:
                console.print(f"  - {out_path.name} ({out_size:.2f} MB)")

            if replace_original and Confirm.ask("Delete original file?", default=False):
                pdf_path.unlink()
                console.print("[green]✓ Original file deleted[/green]")


