"""
Ghostscript integration for PDF manipulation.
Add this as pdf_manipulator/core/ghostscript.py
"""

import io
import sys
import shutil
import hashlib
import tempfile
import subprocess

from typing import Optional, Tuple, List
from pathlib import Path
from contextlib import redirect_stderr
from rich.console import Console

from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings


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
    """Fix with content-only hash comparison."""
    console.print(f"[blue]Fixing malformed PDF with Ghostscript...[/blue]")
    console.print(f"[dim]Quality: {quality}[/dim]")
    
    # Create in temp directory first
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / f"{input_path.stem}_gs_fixed.pdf"
        
        args = [
            "-sDEVICE=pdfwrite",
            f"-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            # Try to make output more deterministic (may not work completely)
            "-dCreationDate=(D:20240101000000Z)",
            "-dModDate=(D:20240101000000Z)", 
            "-dProducer=(pdf-manipulator)",
            f"-sOutputFile={temp_path}",
            str(input_path)
        ]
        
        try:
            result = run_ghostscript_command(args)
            
            if not temp_path.exists():
                raise GhostscriptError("Output file was not created")
            
            # Get properties of the temp file
            temp_size_bytes = temp_path.stat().st_size
            temp_size_mb = temp_size_bytes / (1024 * 1024)
            temp_content_hash = _get_content_hash(temp_path)
            
            # console.print(f"[dim]DEBUG: New temp file - Size: {temp_size_bytes}, Content Hash: {temp_content_hash[:10]}...[/dim]")
            
            # Check canonical fixed filename for identical content
            canonical_fixed_path = input_path.parent / f"{input_path.stem}_gs_fixed.pdf"
            
            if canonical_fixed_path.exists():
                existing_size = canonical_fixed_path.stat().st_size
                existing_content_hash = _get_content_hash(canonical_fixed_path)
                
                # console.print(f"[dim]DEBUG: Existing file - Size: {existing_size}, Content Hash: {existing_content_hash[:10]}...[/dim]")
                # console.print(f"[dim]DEBUG: Size match: {existing_size == temp_size_bytes}[/dim]")
                # console.print(f"[dim]DEBUG: Content hash match: {existing_content_hash == temp_content_hash}[/dim]")
                
                if existing_content_hash == temp_content_hash:
                    # Content match - reuse existing file
                    console.print(f"[green]✓ Using existing repair (identical content): {canonical_fixed_path.name}[/green]")
                    console.print(f"[dim]Content hash matched (ignoring metadata differences)[/dim]")
                    return canonical_fixed_path, canonical_fixed_path.stat().st_size / (1024 * 1024)
                # else:
                #     if existing_size == temp_size_bytes:
                #         console.print(f"[yellow]DEBUG: Same size but different content - this is unexpected[/yellow]")
                #     else:
                #         size_diff = abs(existing_size - temp_size_bytes)
                #         console.print(f"[yellow]DEBUG: Different content and size - diff: {size_diff} bytes[/yellow]")
            
            # Determine output location
            if canonical_fixed_path.exists():
                # Canonical name exists but content differs - use unique name  
                final_output_path = _get_unique_output_path(input_path)
                console.print(f"[yellow]Note: Canonical fix exists but differs, creating: {final_output_path.name}[/yellow]")
            else:
                # Canonical name available - use it
                final_output_path = canonical_fixed_path
            
            # Move temp file to final location
            shutil.move(str(temp_path), str(final_output_path))
            
            # Success reporting
            original_size = input_path.stat().st_size / (1024 * 1024)
            
            console.print(f"[green]✓ Fixed PDF: {final_output_path.name}[/green]")
            console.print(f"[green]  Original: {original_size:.2f} MB[/green]")
            console.print(f"[green]  Fixed:    {temp_size_mb:.2f} MB[/green]")
            
            if original_size > 0:
                savings = ((original_size - temp_size_mb) / original_size) * 100
                if savings > 0:
                    console.print(f"[green]  Savings:  {savings:.1f}%[/green]")
                else:
                    console.print(f"[yellow]  Size change: {abs(savings):.1f}% larger[/yellow]")
            
            return final_output_path, temp_size_mb
            
        except GhostscriptError:
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
    console.print(f"[blue]Compressing PDF with Ghostscript...[/blue]")
    console.print(f"[dim]Quality: {quality}[/dim]")
    
    # Create in temp directory first
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / f"{input_path.stem}_gs_compressed.pdf"
        
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
            f"-sOutputFile={temp_path}",
            str(input_path)
        ]
        
        result = run_ghostscript_command(args)
        
        if not temp_path.exists():
            raise GhostscriptError("Output file was not created")
        
        # Get properties of the temp file
        temp_size_bytes = temp_path.stat().st_size
        temp_size_mb = temp_size_bytes / (1024 * 1024)
        temp_hash = _get_file_hash(temp_path)
        
        # For compression, use a different pattern to avoid conflicts with fix operations
        pattern = f"{input_path.stem}_gs_compressed*.pdf"
        existing_match = None
        
        try:
            for existing_file in input_path.parent.glob(pattern):
                if (existing_file.exists() and 
                    existing_file.stat().st_size == temp_size_bytes and
                    _get_file_hash(existing_file) == temp_hash):
                    existing_match = existing_file
                    break
        except Exception:
            pass
        
        if existing_match:
            console.print(f"[green]✓ Using existing identical compression: {existing_match.name}[/green]")
            console.print(f"[dim]Avoided creating duplicate compressed file[/dim]")
            return existing_match, existing_match.stat().st_size / (1024 * 1024)
        
        # No duplicate found, move temp file to target location
        base_output_path = input_path.parent / f"{input_path.stem}_gs_compressed.pdf"
        final_output_path = base_output_path
        
        # Handle existing files
        counter = 1
        while final_output_path.exists():
            final_output_path = input_path.parent / f"{input_path.stem}_gs_compressed_{counter:02d}.pdf"
            counter += 1
        
        shutil.move(str(temp_path), str(final_output_path))
        
        # Success reporting
        original_size = input_path.stat().st_size / (1024 * 1024)
        
        console.print(f"[green]✓ Compressed PDF: {final_output_path.name}[/green]")
        console.print(f"[green]  Original: {original_size:.2f} MB[/green]")
        console.print(f"[green]  Compressed: {temp_size_mb:.2f} MB[/green]")
        
        if original_size > 0:
            savings = ((original_size - temp_size_mb) / original_size) * 100
            console.print(f"[green]  Savings: {savings:.1f}%[/green]")
        
        return final_output_path, temp_size_mb


def detect_pdf_structural_issues(pdf_path: Path) -> tuple[bool, str]:
    """
    Detect PDF structural issues by capturing PyPDF warnings.
    
    Returns:
        Tuple of (has_issues, description)
    """
    try:
        from pypdf import PdfReader
        from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
        
        # Use our warning suppression system to capture structured warning data
        with suppress_pdf_warnings() as warning_filter:
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
        
        # Check what warnings were captured using structured data
        if warning_filter and warning_filter.suppressed_count > 0:
            # Check for "wrong pointing object" specifically
            wrong_objects = warning_filter.suppressed_types.get("wrong pointing object", 0)
            if wrong_objects > 0:
                return True, f"Structural corruption: {wrong_objects} invalid object references"
            
            # Check for other structural issues patterns
            ignoring_count = warning_filter.suppressed_types.get("Ignoring wrong pointing object", 0)
            if ignoring_count > 0:
                return True, f"Structural corruption: {ignoring_count} invalid object references"
            
            # Check for multiple warnings indicating structural problems
            if warning_filter.suppressed_count > 5:
                return True, f"Multiple PDF structure warnings detected ({warning_filter.suppressed_count} warnings)"
        
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


def _get_unique_output_path(input_path: Path) -> Path:
    """Get unique output path for cases where canonical name conflicts."""
    counter = 1
    while True:
        numbered_path = input_path.parent / f"{input_path.stem}_gs_fixed_{counter:02d}.pdf"
        if not numbered_path.exists():
            return numbered_path
        counter += 1


def _get_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Get SHA256 hash of file with error handling."""
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except (OSError, PermissionError):
        return ""


def _get_content_hash(file_path: Path) -> str:
    """Get hash of PDF content without metadata."""
    from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
    
    try:
        from pypdf import PdfReader
        
        with suppress_pdf_warnings():
            reader = PdfReader(file_path)
            content_parts = []
            
            # Hash just the page content streams (not metadata)
            for i, page in enumerate(reader.pages):
                try:
                    # Get page content
                    if hasattr(page, 'get_contents'):
                        content = page.get_contents()
                        if content:
                            content_parts.append(content.get_data())
                    
                    # Also include page dimensions for structural comparison
                    if hasattr(page, 'mediabox'):
                        media_box = str(page.mediabox).encode('utf-8')
                        content_parts.append(media_box)
                        
                except Exception:
                    # If we can't extract content from a page, use page number as fallback
                    content_parts.append(f"page_{i}".encode('utf-8'))
            
            # Combine all page contents and hash
            combined_content = b''.join(content_parts)
            return hashlib.sha256(combined_content).hexdigest()
        
    except Exception as e:
        console.print(f"[dim]Content hash failed ({e}), using file hash[/dim]")
        # Fallback to file hash if content extraction fails
        return _get_file_hash(file_path)

