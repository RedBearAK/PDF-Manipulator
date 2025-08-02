"""
Create: pdf_manipulator/core/malformation_checker.py

This module handles the CLI workflow for detecting and fixing malformed PDFs.
It uses ghostscript.py for the core detection/fixing logic.
"""

import sys

from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, Prompt

from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings


console = Console()


def check_and_fix_malformation_early(pdf_files: list[tuple[Path, int, float]], args) -> list[tuple[Path, int, float]]:
    """Check for malformed PDFs and offer fixes before showing analysis."""
    pdf_path, page_count, file_size = pdf_files[0]
    
    # Early return if we don't need to check
    if not any([args.extract_pages, args.split_pages, args.analyze]):
        return pdf_files
    
    # Try to detect malformation, return original files if we can't
    try:
        from pdf_manipulator.core.ghostscript import detect_malformed_pdf, check_ghostscript_availability, fix_malformed_pdf
    except ImportError:
        return pdf_files
    
    try:
        is_malformed, description = detect_malformed_pdf(pdf_path)
    except Exception:
        return pdf_files
    
    # Early return if not malformed
    if not is_malformed:
        return pdf_files
    
    # Show malformation warning
    _show_malformation_warning(description, args)
    
    # Early return if Ghostscript not available
    if not check_ghostscript_availability():
        console.print("[yellow]Ghostscript not available for fixing[/yellow]")
        console.print("[dim]Install with: brew install ghostscript[/dim]")
        return pdf_files
    
    # Early return for batch mode
    if args.batch:
        console.print("[yellow]Batch mode: continuing with original PDF[/yellow]")
        return pdf_files
    
    # Ask user if they want to fix
    if not Confirm.ask("Fix with Ghostscript before proceeding? (Recommended)", default=True):
        console.print("[yellow]Continuing with original PDF (pages may be larger than necessary)[/yellow]")
        return pdf_files
    
    # Try to fix the PDF
    fixed_files = _attempt_pdf_fix(pdf_path, pdf_files)
    return fixed_files


def check_and_fix_malformation_batch(pdf_files: list[tuple[Path, int, float]], args) -> list[tuple[Path, int, float]]:
    """Check for malformed PDFs in batch mode - just warn briefly."""
    
    # Early return if we don't need to check
    if not any([args.extract_pages, args.split_pages, args.analyze]):
        return pdf_files
    
    try:
        from pdf_manipulator.core.ghostscript import detect_malformed_pdf
    except ImportError:
        return pdf_files
    
    # Find malformed files
    malformed_count = 0
    for pdf_path, page_count, file_size in pdf_files:
        try:
            is_malformed, description = detect_malformed_pdf(pdf_path)
            if is_malformed:
                malformed_count += 1
        except Exception:
            continue
    
    if malformed_count > 0:
        console.print(f"\n[yellow]⚠️  Found {malformed_count} malformed PDFs[/yellow]")
        console.print("[dim]Individual files will be checked during processing[/dim]")
    
    return pdf_files


# def check_and_fix_malformation_for_extraction(pdf_files: list[tuple[Path, int, float]], args) -> list[tuple[Path, int, float]]:
#     """Check for malformation during extraction and offer to fix individual files."""
    
#     # Only check the first file (for individual processing)
#     pdf_path, page_count, file_size = pdf_files[0]
    
#     # Early return if we don't need to check
#     if not any([args.extract_pages, args.split_pages]):
#         return pdf_files
    
#     # Try to detect malformation
#     try:
#         from pdf_manipulator.core.ghostscript import detect_malformed_pdf, check_ghostscript_availability
#     except ImportError:
#         return pdf_files
    
#     try:
#         is_malformed, description = detect_malformed_pdf(pdf_path)
#     except Exception:
#         return pdf_files
    
#     # Early return if not malformed
#     if not is_malformed:
#         return pdf_files
    
#     # Show malformation warning for this specific file
#     console.print(f"\n[yellow]⚠️  {pdf_path.name} has issues:[/yellow]")
#     console.print(f"[yellow]{description}[/yellow]")
    
#     if "Structural corruption" in description:
#         console.print("[yellow]This may cause processing errors or unexpected results[/yellow]")
#     elif "Resource duplication" in description:
#         console.print("[yellow]Extracted pages will be unnecessarily large[/yellow]")
    
#     # Early return if Ghostscript not available
#     if not check_ghostscript_availability():
#         console.print("[yellow]Ghostscript not available for fixing[/yellow]")
#         console.print("[dim]Install with: brew install ghostscript (macOS) or apt install ghostscript (Ubuntu)[/dim]")
        
#         if not Confirm.ask("Continue with malformed PDF anyway?", default=True):
#             console.print("[blue]Skipping this file[/blue]")
#             return []  # Return empty list to skip this file
#         return pdf_files
    
#     # Early return for batch mode
#     if args.batch:
#         console.print("[yellow]Batch mode: continuing with malformed PDF[/yellow]")
#         return pdf_files
    
#     # Ask user if they want to fix
#     if not Confirm.ask("Fix with Ghostscript before processing?", default=True):
#         console.print("[yellow]Continuing with malformed PDF (results may be suboptimal)[/yellow]")
#         return pdf_files
    
#     # Try to fix the PDF
#     return _attempt_individual_pdf_fix(pdf_path, pdf_files, batch_mode=args.batch)


def _show_malformation_warning(description: str, args):
    """Show malformation warning messages."""
    console.print(f"\n[yellow]⚠️  Malformed PDF detected:[/yellow]")
    console.print(f"[yellow]{description}[/yellow]")
    
    if "Structural corruption" in description:
        console.print("[yellow]This PDF has internal structure problems that may cause errors[/yellow]")
        console.print("[dim]Ghostscript can repair these structural issues[/dim]")
    
    if args.extract_pages or args.split_pages:
        console.print("[yellow]Processing this PDF may produce unexpected results[/yellow]")
        console.print("[dim]Recommendation: Fix with --gs-fix first for best results[/dim]")


def _attempt_pdf_fix(pdf_path: Path, original_files: list[tuple[Path, int, float]]) -> list[tuple[Path, int, float]]:
    """Attempt to fix PDF and get user choice on how to proceed."""
    from pdf_manipulator.core.ghostscript import fix_malformed_pdf
    
    console.print("\n[blue]Fixing PDF structure with Ghostscript...[/blue]")
    
    try:
        with suppress_pdf_warnings():
            output_path, new_size = fix_malformed_pdf(pdf_path, quality="default")
    except Exception as e:
        console.print(f"[red]Error fixing PDF: {e}[/red]")
        console.print("[yellow]Continuing with original PDF[/yellow]")
        return original_files
    
    if not output_path or not output_path.exists():
        console.print("[red]Failed to create fixed PDF, continuing with original[/red]")
        return original_files
    
    console.print(f"[green]✓ Fixed PDF created: {output_path.name}[/green]")
    return _get_user_choice_on_fixed_pdf(output_path, original_files)


def _attempt_individual_pdf_fix(pdf_path: Path, original_files: list[tuple[Path, int, float]], 
                                    batch_mode: bool = False) -> list[tuple[Path, int, float]]:
    """Fix individual PDF during processing."""
    from pdf_manipulator.core.ghostscript import fix_malformed_pdf
    from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
    from rich.prompt import Confirm
    
    console.print(f"\n[blue]Fixing {pdf_path.name} with Ghostscript...[/blue]")
    
    try:
        with suppress_pdf_warnings():
            output_path, new_size = fix_malformed_pdf(pdf_path, quality="default")
    except Exception as e:
        console.print(f"[red]Error fixing PDF: {e}[/red]")
        
        # In interactive mode, ask user what to do
        # In batch mode, just continue with original
        if batch_mode:
            console.print("[yellow]Batch mode: continuing with original PDF[/yellow]")
            return original_files
        else:
            if Confirm.ask("Continue with original malformed PDF anyway?", default=True):
                console.print("[yellow]Continuing with original PDF (results may be suboptimal)[/yellow]")
                return original_files
            else:
                console.print("[blue]Skipping this file[/blue]")
                return []  # Return empty list to skip this file
    
    # Verify the output file actually exists
    if not output_path or not output_path.exists():
        console.print("[red]Fixed PDF was not created successfully[/red]")
        
        # Same interactive vs batch handling
        if batch_mode:
            console.print("[yellow]Batch mode: continuing with original PDF[/yellow]")
            return original_files
        else:
            if Confirm.ask("Continue with original malformed PDF anyway?", default=True):
                console.print("[yellow]Continuing with original PDF (results may be suboptimal)[/yellow]")
                return original_files
            else:
                console.print("[blue]Skipping this file[/blue]")
                return []
    
    console.print(f"[green]✓ Fixed PDF created: {output_path.name}[/green]")
    
    # Update file info to use the fixed PDF
    from pdf_manipulator.core.scanner import get_pdf_info
    new_page_count, new_file_size = get_pdf_info(output_path)
    console.print("[green]✓ Using fixed PDF for processing[/green]")
    
    return [(output_path, new_page_count, new_file_size)]


def _get_user_choice_on_fixed_pdf(fixed_path: Path, original_files: list[tuple[Path, int, float]]) -> list[tuple[Path, int, float]]:
    """Get user choice on whether to use fixed or original PDF."""
    console.print("\nChoose how to proceed:")
    console.print("  [bold]f[/bold] - Use fixed PDF (recommended)")
    console.print("  [bold]o[/bold] - Use original PDF anyway")  
    console.print("  [bold]c[/bold] - Cancel operation")
    
    choice = Prompt.ask("Your choice", choices=["f", "o", "c"], default="f")
    
    if choice == "f":
        return _use_fixed_pdf(fixed_path)
    elif choice == "o":
        console.print("[yellow]Continuing with original PDF (pages may be larger than necessary)[/yellow]")
        return original_files
    else:  # choice == "c"
        console.print("[blue]Operation cancelled[/blue]")
        sys.exit(0)


def _use_fixed_pdf(fixed_path: Path) -> list[tuple[Path, int, float]]:
    """Update file list to use the fixed PDF."""
    from pdf_manipulator.core.scanner import get_pdf_info
    
    new_page_count, new_file_size = get_pdf_info(fixed_path)
    console.print("[green]✓ Using fixed PDF for processing[/green]")
    return [(fixed_path, new_page_count, new_file_size)]
