"""
Ghostscript integration for PDF manipulation.
Add this as pdf_manipulator/core/ghostscript.py
"""

import io
import sys
import shutil
import subprocess

from typing import Optional, Tuple, List
from pathlib import Path
from contextlib import redirect_stderr
from rich.console import Console

console = Console()


class GhostscriptError(Exception):
    """Custom exception for Ghostscript-related errors."""
    pass


def find_ghostscript_executable() -> Optional[str]:
    """
    Find Ghostscript executable on the system.
    
    Returns:
        Path to ghostscript executable or None if not found
    """
    # Common executable names across platforms
    if sys.platform == "win32":
        candidates = ["gswin64c.exe", "gswin32c.exe", "gs.exe"]
    else:
        candidates = ["gs"]
    
    for candidate in candidates:
        gs_path = shutil.which(candidate)
        if gs_path:
            return gs_path
    
    return None


def check_ghostscript_availability() -> bool:
    """
    Check if Ghostscript is available on the system.
    
    Returns:
        True if Ghostscript is available, False otherwise
    """
    gs_path = find_ghostscript_executable()
    if not gs_path:
        return False
    
    try:
        # Test with version command
        result = subprocess.run(
            [gs_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def get_ghostscript_version() -> Optional[str]:
    """
    Get Ghostscript version string.
    
    Returns:
        Version string or None if not available
    """
    gs_path = find_ghostscript_executable()
    if not gs_path:
        return None
    
    try:
        result = subprocess.run(
            [gs_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    
    return None


def run_ghostscript_command(args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """
    Run a Ghostscript command with the given arguments.
    
    Args:
        args: List of command-line arguments (without 'gs')
        timeout: Timeout in seconds
        
    Returns:
        CompletedProcess result
        
    Raises:
        GhostscriptError: If Ghostscript is not available or command fails
    """
    gs_path = find_ghostscript_executable()
    if not gs_path:
        raise GhostscriptError(
            "Ghostscript not found. Please install Ghostscript:\n"
            "  macOS: brew install ghostscript\n"
            "  Ubuntu: sudo apt-get install ghostscript\n"
            "  Windows: Download from https://www.ghostscript.com/download/"
        )
    
    cmd = [gs_path] + args
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = f"Ghostscript command failed (exit code {result.returncode})"
            if result.stderr:
                error_msg += f"\nError: {result.stderr}"
            if result.stdout:
                error_msg += f"\nOutput: {result.stdout}"
            raise GhostscriptError(error_msg)
        
        return result
        
    except subprocess.TimeoutExpired:
        raise GhostscriptError(f"Ghostscript command timed out after {timeout} seconds")
    except subprocess.SubprocessError as e:
        raise GhostscriptError(f"Subprocess error: {e}")


def fix_malformed_pdf(input_path: Path, quality: str = "default") -> Tuple[Path, float]:
    """
    Fix malformed PDF using Ghostscript to deduplicate resources.
    
    Args:
        input_path: Path to input PDF
        quality: Quality setting ('screen', 'ebook', 'printer', 'prepress', 'default')
        
    Returns:
        Tuple of (output_path, new_size_mb)
        
    Raises:
        GhostscriptError: If processing fails
    """
    output_path = input_path.parent / f"{input_path.stem}_gs_fixed.pdf"
    
    # Ensure unique filename
    counter = 1
    while output_path.exists():
        output_path = input_path.parent / f"{input_path.stem}_gs_fixed_{counter:02d}.pdf"
        counter += 1
    
    args = [
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        str(input_path)
    ]
    
    console.print(f"[blue]Fixing malformed PDF with Ghostscript...[/blue]")
    console.print(f"[dim]Quality: {quality}[/dim]")
    
    try:
        result = run_ghostscript_command(args)
        
        if output_path.exists():
            new_size = output_path.stat().st_size / (1024 * 1024)
            original_size = input_path.stat().st_size / (1024 * 1024)
            
            console.print(f"[green]✓ Fixed PDF: {output_path.name}[/green]")
            console.print(f"[green]  Original: {original_size:.2f} MB[/green]")
            console.print(f"[green]  Fixed:    {new_size:.2f} MB[/green]")
            
            if original_size > 0:
                savings = ((original_size - new_size) / original_size) * 100
                if savings > 0:
                    console.print(f"[green]  Savings:  {savings:.1f}%[/green]")
                else:
                    console.print(f"[yellow]  Size change: {abs(savings):.1f}% larger[/yellow]")
            
            return output_path, new_size
        else:
            raise GhostscriptError("Output file was not created")
            
    except GhostscriptError:
        # Clean up partial file if it exists
        if output_path.exists():
            output_path.unlink()
        raise


def compress_pdf(input_path: Path, quality: str = "ebook") -> Tuple[Path, float]:
    """
    Compress PDF using Ghostscript.
    
    Args:
        input_path: Path to input PDF
        quality: Compression quality ('screen', 'ebook', 'printer', 'prepress', 'default')
        
    Returns:
        Tuple of (output_path, new_size_mb)
    """
    output_path = input_path.parent / f"{input_path.stem}_gs_compressed.pdf"
    
    # Ensure unique filename
    counter = 1
    while output_path.exists():
        output_path = input_path.parent / f"{input_path.stem}_gs_compressed_{counter:02d}.pdf"
        counter += 1
    
    args = [
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dCompressPages=true",
        "-dEmbedAllFonts=true",
        f"-sOutputFile={output_path}",
        str(input_path)
    ]
    
    console.print(f"[blue]Compressing PDF with Ghostscript...[/blue]")
    console.print(f"[dim]Quality: {quality}[/dim]")
    
    result = run_ghostscript_command(args)
    
    if output_path.exists():
        new_size = output_path.stat().st_size / (1024 * 1024)
        original_size = input_path.stat().st_size / (1024 * 1024)
        
        console.print(f"[green]✓ Compressed PDF: {output_path.name}[/green]")
        console.print(f"[green]  Original: {original_size:.2f} MB[/green]")
        console.print(f"[green]  Compressed: {new_size:.2f} MB[/green]")
        
        if original_size > 0:
            savings = ((original_size - new_size) / original_size) * 100
            console.print(f"[green]  Savings: {savings:.1f}%[/green]")
        
        return output_path, new_size
    else:
        raise GhostscriptError("Output file was not created")


def detect_pdf_structural_issues(pdf_path: Path) -> tuple[bool, str]:
    """
    Detect PDF structural issues by capturing PyPDF warnings.
    
    Returns:
        Tuple of (has_issues, description)
    """
    try:
        from pypdf import PdfReader
        
        # Capture stderr to catch PyPDF warnings
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            reader = PdfReader(pdf_path)
            # Try to access pages to trigger warnings
            total_pages = len(reader.pages)
            
            # Sample a few pages to trigger more warnings
            for i in range(min(3, total_pages)):
                try:
                    page = reader.pages[i]
                    # Try to access page resources to trigger warnings
                    if hasattr(page, 'get_contents'):
                        page.get_contents()
                except Exception:
                    pass  # Ignore extraction errors, we just want to trigger warnings
        
        # Check what warnings were captured
        warnings_output = stderr_capture.getvalue()
        
        if "wrong pointing object" in warnings_output:
            wrong_objects = warnings_output.count("wrong pointing object")
            return True, f"Structural corruption: {wrong_objects} invalid object references"
        
        if "Ignoring" in warnings_output and len(warnings_output) > 100:
            return True, "Multiple PDF structure warnings detected"
        
        return False, "No structural issues detected"
        
    except Exception as e:
        return False, f"Could not analyze PDF structure: {e}"


def detect_malformed_pdf(pdf_path: Path) -> tuple[bool, str]:
    """
    Detect if a PDF has issues that Ghostscript can fix.
    
    Returns:
        Tuple of (is_malformed, description)
    """
    issues = []
    
    # Check for structural corruption first
    has_structural_issues, structural_desc = detect_pdf_structural_issues(pdf_path)
    if has_structural_issues:
        issues.append(structural_desc)
    
    # Check for resource malformation (existing logic)
    try:
        from pypdf import PdfReader
        
        # Suppress warnings for this analysis since we already checked them above
        with redirect_stderr(io.StringIO()):
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            
            # Sample first few pages to check for malformation
            pages_to_check = min(3, total_pages)
            
            for i in range(pages_to_check):
                page = reader.pages[i]
                if '/XObject' in page.get('/Resources', {}):
                    xobjects = page['/Resources']['/XObject'].get_object()
                    images = [x for x in xobjects if xobjects[x].get('/Subtype') == '/Image']
                    image_count = len(images)
                    
                    # If page has 50%+ of total pages as image references, it's likely malformed
                    if image_count >= total_pages * 0.5:
                        issues.append(f"Resource duplication: {image_count} images per page")
                        break
        
    except Exception as e:
        if not issues:  # Only report this if we haven't found other issues
            issues.append(f"Could not analyze PDF: {e}")
    
    if issues:
        return True, "; ".join(issues)
    else:
        return False, "No issues detected"


# def check_and_fix_malformation_for_extraction(pdf_files: list[tuple[Path, int, float]], args) -> list[tuple[Path, int, float]]:
#     """Check for malformation during extraction and offer to fix individual files."""
    
#     # Only check the first file (for individual processing)
#     pdf_path, page_count, file_size = pdf_files[0]
    
#     # Early return if we don't need to check
#     if not any([args.extract_pages, args.split_pages]):
#         return pdf_files
    
#     # Try to detect malformation
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
        
#         from rich.prompt import Confirm
#         if not Confirm.ask("Continue with malformed PDF anyway?", default=True):
#             console.print("[blue]Skipping this file[/blue]")
#             return []  # Return empty list to skip this file
#         return pdf_files
    
#     # Early return for batch mode
#     if args.batch:
#         console.print("[yellow]Batch mode: continuing with malformed PDF[/yellow]")
#         return pdf_files
    
#     # Ask user if they want to fix
#     from rich.prompt import Confirm
#     if not Confirm.ask("Fix with Ghostscript before processing?", default=True):
#         console.print("[yellow]Continuing with malformed PDF (results may be suboptimal)[/yellow]")
#         return pdf_files
    
#     # Try to fix the PDF
#     return _attempt_individual_pdf_fix(pdf_path, pdf_files)


# def _attempt_individual_pdf_fix(pdf_path: Path, original_files: list[tuple[Path, int, float]]) -> list[tuple[Path, int, float]]:
#     """Fix individual PDF during processing."""
    
#     console.print(f"\n[blue]Fixing {pdf_path.name} with Ghostscript...[/blue]")
    
#     try:
#         output_path, new_size = fix_malformed_pdf(pdf_path, quality="default")
#     except Exception as e:
#         console.print(f"[red]Error fixing PDF: {e}[/red]")
#         console.print("[yellow]Continuing with original PDF[/yellow]")
#         return original_files
    
#     if not output_path or not output_path.exists():
#         console.print("[red]Failed to create fixed PDF, continuing with original[/red]")
#         return original_files
    
#     console.print(f"[green]✓ Fixed PDF created: {output_path.name}[/green]")
    
#     # Update file info to use the fixed PDF
#     from pdf_manipulator.core.scanner import get_pdf_info
#     new_page_count, new_file_size = get_pdf_info(output_path)
#     console.print("[green]✓ Using fixed PDF for processing[/green]")
    
#     return [(output_path, new_page_count, new_file_size)]


def safe_batch_fix_pdfs(folder_path: Path, recursive: bool = False, 
                        dry_run: bool = False, preserve_originals: bool = True) -> list[tuple[Path, str]]:
    """
    Safely fix malformed PDFs in batch with safety checks.
    
    Args:
        folder_path: Directory to process
        recursive: Process subdirectories
        dry_run: Only report what would be done
        preserve_originals: Keep original files
        
    Returns:
        List of (file_path, result_message) tuples
    """
    if not check_ghostscript_availability():
        raise GhostscriptError("Ghostscript not available for batch processing")
    
    # Find PDF files
    if recursive:
        pdf_files = list(folder_path.rglob("*.pdf"))
    else:
        pdf_files = list(folder_path.glob("*.pdf"))
    
    # Filter hidden files
    pdf_files = [f for f in pdf_files if not f.name.startswith('.')]
    
    console.print(f"[blue]Found {len(pdf_files)} PDF files[/blue]")
    
    results = []
    malformed_files = []
    
    # First pass: detect malformed files
    console.print("[blue]Scanning for malformed PDFs...[/blue]")
    for pdf_file in pdf_files:
        is_malformed, description = detect_malformed_pdf(pdf_file)
        if is_malformed:
            malformed_files.append((pdf_file, description))
            console.print(f"[yellow]📄 {pdf_file.name}: {description}[/yellow]")
    
    if not malformed_files:
        console.print("[green]✓ No malformed PDFs detected![/green]")
        return []
    
    console.print(f"\n[yellow]Found {len(malformed_files)} malformed PDFs[/yellow]")
    
    if dry_run:
        console.print("[blue]DRY RUN - would fix these files:[/blue]")
        for pdf_file, desc in malformed_files:
            console.print(f"  • {pdf_file.name}")
        return [(f, "Would fix: " + desc) for f, desc in malformed_files]
    
    # Safety warnings
    console.print("\n[yellow]⚠️  SAFETY NOTES:[/yellow]")
    console.print("• This operation rebuilds PDFs (generally safe but not 100% lossless)")
    console.print("• Digital signatures will be invalidated")
    console.print("• Annotations and form fields might be altered")
    console.print("• Interactive elements (JavaScript) might be removed")
    if preserve_originals:
        console.print("• Original files will be preserved")
    else:
        console.print("[red]• Original files will be REPLACED[/red]")
    
    # Get user confirmation for batch operation
    from rich.prompt import Confirm
    if not Confirm.ask(f"\nProceed to fix {len(malformed_files)} malformed PDFs?", default=True):
        console.print("[yellow]Operation cancelled[/yellow]")
        return []
    
    # Process malformed files
    for pdf_file, description in malformed_files:
        try:
            console.print(f"\n[cyan]Processing {pdf_file.name}[/cyan]...")
            
            output_path, new_size = fix_malformed_pdf(pdf_file, quality="default")
            
            if output_path and output_path.exists():
                original_size = pdf_file.stat().st_size / (1024 * 1024)
                
                # Safety check: warn if file size changed dramatically
                size_change = abs(new_size - original_size) / original_size * 100
                if size_change > 20:  # More than 20% change
                    console.print(f"[yellow]⚠️  Size changed by {size_change:.1f}% - please verify result[/yellow]")
                
                if not preserve_originals:
                    # Replace original with fixed version
                    backup_path = pdf_file.with_suffix('.pdf.backup')
                    pdf_file.rename(backup_path)  # Backup original
                    output_path.rename(pdf_file)  # Move fixed to original location
                    console.print(f"[green]✓ Replaced original (backup: {backup_path.name})[/green]")
                    results.append((pdf_file, f"Fixed and replaced (was {description})"))
                else:
                    console.print(f"[green]✓ Fixed: {output_path.name}[/green]")
                    results.append((pdf_file, f"Fixed as {output_path.name} ({description})"))
            else:
                results.append((pdf_file, f"Failed to fix: {description}"))
                
        except GhostscriptError as e:
            console.print(f"[red]Failed to fix {pdf_file.name}: {e}[/red]")
            results.append((pdf_file, f"Error: {e}"))
        except Exception as e:
            console.print(f"[red]Unexpected error with {pdf_file.name}: {e}[/red]")
            results.append((pdf_file, f"Unexpected error: {e}"))
    
    return results


# Quality settings explanation
QUALITY_SETTINGS = {
    "screen": "Low quality, small file size (72 DPI images)",
    "ebook": "Medium quality for ebooks (150 DPI images)",
    "printer": "Good quality for printing (300 DPI images)",  
    "prepress": "High quality for professional printing (300 DPI images)",
    "default": "Balanced quality and size"
}


def repair_pdf(input_path: Path) -> Tuple[Path, float]:
    """
    Repair corrupted PDF using Ghostscript.
    
    Args:
        input_path: Path to input PDF
        
    Returns:
        Tuple of (output_path, new_size_mb)
    """
    return fix_malformed_pdf(input_path, quality="default")


# CLI integration suggestions:
"""
Add these to cli.py:

# Ghostscript operations
operations.add_argument('--gs-fix', action='store_true',
    help='Fix malformed PDFs using Ghostscript (deduplicates resources)')
operations.add_argument('--gs-batch-fix', action='store_true',
    help='Fix all malformed PDFs in folder using Ghostscript')
operations.add_argument('--gs-quality', choices=['screen', 'ebook', 'printer', 'prepress', 'default'],
    default='default', help='Ghostscript quality setting')
operations.add_argument('--recursive', action='store_true',
    help='Process subdirectories recursively')
operations.add_argument('--dry-run', action='store_true',
    help='Show what would be done without actually doing it')
operations.add_argument('--replace-originals', action='store_true',
    help='Replace original files with fixed versions (CAREFUL!)')
"""
