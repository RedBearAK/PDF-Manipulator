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
from pdf_manipulator.core.malformation_utils import check_and_fix_malformation_with_args
from pdf_manipulator.core.warning_suppression import suppress_all_pdf_warnings


console = Console()


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
    else:
        operation = "split"
        console.print("\n[blue]Split pages mode[/blue]")

    # Extra warning for batch mode with replace
    if args.batch and args.replace:
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
            process_batch_extract(args, pdf_files)
        else:
            process_batch_split(args, pdf_files)
    else:
        if operation == "extract":
            process_interactive_extract(args, pdf_files)
        else:
            # Split mode - only multi-page PDFs
            process_multipage_pdfs(pdf_files, "split", args.replace)


def process_batch_extract(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle batch extraction processing."""

    with suppress_all_pdf_warnings():
        # For extract, process all PDFs (not just multi-page)
        for pdf_path, page_count, file_size in pdf_files:
            console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
            try:
                # Check if extraction is valid for this PDF
                # pages_to_extract, _, groups = parse_page_range(args.extract_pages, page_count)
                pages_to_extract, _, groups = parse_page_range(args.extract_pages, page_count, pdf_path)
                
                if args.respect_groups:
                    # Extract with groupings respected
                    output_files = extract_pages_grouped(pdf_path, args.extract_pages)
                    if output_files:
                        console.print(f"[green]✓ Created {len(output_files)} grouped files[/green]")
                        if args.replace:
                            pdf_path.unlink()
                            console.print("[yellow]✓ Deleted original[/yellow]")
                elif args.separate_files:
                    # Extract as separate files
                    output_files = extract_pages_separate(pdf_path, args.extract_pages)
                    if output_files:
                        console.print(f"[green]✓ Created {len(output_files)} separate files[/green]")
                        if args.replace:
                            pdf_path.unlink()
                            console.print("[yellow]✓ Deleted original[/yellow]")
                else:
                    # Extract as single document
                    output_path, new_size = extract_pages(pdf_path, args.extract_pages)
                    if output_path:
                        console.print(f"[green]✓ Created:[/green] {output_path.name}")
                        if args.replace:
                            pdf_path.unlink()
                            output_path.rename(pdf_path)
                            console.print("[yellow]✓ Replaced original[/yellow]")

            except ValueError as e:
                console.print(f"[yellow]Skipping {pdf_path.name}: {e}[/yellow]")

def process_batch_split(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle batch split processing."""

    with suppress_all_pdf_warnings():
        # Split mode - only multi-page PDFs
        multi_page_pdfs = [(p, c, s) for p, c, s in pdf_files if c > 1]
        for pdf_path, page_count, file_size in multi_page_pdfs:
            console.print(f"\n[cyan]Processing {pdf_path.name}[/cyan]...")
            output_files = split_to_pages(pdf_path)
            if output_files:
                console.print(f"[green]✓ Split into {len(output_files)} files[/green]")
                if args.replace:
                    pdf_path.unlink()
                    console.print("[yellow]✓ Deleted original[/yellow]")


def process_interactive_extract(args: argparse.Namespace, pdf_files: list[tuple[Path, int, float]]):
    """Handle interactive extraction processing."""

    # For extract, ask about each PDF
    for pdf_path, page_count, file_size in pdf_files:
        console.print(f"\n[cyan]{pdf_path.name}[/cyan] - {page_count} pages, {file_size:.2f} MB")

        # NEW: Check for malformation on individual file
        pdf_files_single = [(pdf_path, page_count, file_size)]
        fixed_files = check_and_fix_malformation_with_args(pdf_files_single, args)
        
        if not fixed_files:
            console.print("[yellow]Skipping this PDF as requested[/yellow]")
            continue  # Skip to next PDF in the loop
        
        # Use the potentially fixed file info
        pdf_path, page_count, file_size = fixed_files[0]
        
        try:
            # Validate extraction for this PDF
            # pages_to_extract, _, groups = parse_page_range(args.extract_pages, page_count)
            pages_to_extract, _, groups = parse_page_range(args.extract_pages, page_count, pdf_path)
            
            # Determine extraction mode
            if args.respect_groups:
                extraction_mode = 'grouped'
            elif args.separate_files:
                extraction_mode = 'separate'
            else:
                extraction_mode = decide_extraction_mode(pages_to_extract, groups, True)
            
            if Confirm.ask(f"Extract pages {args.extract_pages}?", default=True):
                if extraction_mode == 'separate':
                    # Extract as separate files
                    output_files = extract_pages_separate(pdf_path, args.extract_pages)
                    if output_files:
                        total_size = sum(size for _, size in output_files)
                        console.print(f"[green]✓ Created {len(output_files)} files:[/green]")
                        for out_path, out_size in output_files:
                            console.print(f"  - {out_path.name} ({out_size:.2f} MB)")
                        if args.replace and Confirm.ask("Delete original file?", default=False):
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
                        if args.replace and Confirm.ask("Delete original file?", default=False):
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
            console.print(f"[yellow]Cannot extract from this PDF: {e}[/yellow]")
