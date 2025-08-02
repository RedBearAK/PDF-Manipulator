"""
Comprehensive PDF malformation detection and fixing utilities.
Create: pdf_manipulator/core/malformation_utils.py

This module provides reusable malformation handling for all operations
while preserving the carefully debugged idempotent file creation logic.
"""

import sys

from typing import Optional, Any
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

from pdf_manipulator.core.scanner import get_pdf_info


console = Console()


#################################################################################################
# Core Detection Functions

def check_pdf_malformation(pdf_path: Path) -> tuple[bool, str]:
    """
    Pure malformation detection with no side effects.
    
    Args:
        pdf_path: Path to PDF file to check
        
    Returns:
        Tuple of (is_malformed, description)
    """
    try:
        from pdf_manipulator.core.ghostscript import detect_malformed_pdf
        return detect_malformed_pdf(pdf_path)
    except ImportError:
        return False, "Ghostscript integration not available"
    except Exception as e:
        return False, f"Could not analyze PDF: {e}"


def check_ghostscript_available() -> bool:
    """Check if Ghostscript is available for fixing."""
    try:
        from pdf_manipulator.core.ghostscript import check_ghostscript_availability
        return check_ghostscript_availability()
    except ImportError:
        return False


#################################################################################################
# Core Fixing Functions (Preserving Existing Idempotent Logic)

def fix_pdf_idempotent(pdf_path: Path, quality: str = "default") -> tuple[Optional[Path], bool, str]:
    """
    Fix PDF with full idempotent logic preserved.
    
    This function preserves all the carefully debugged logic for:
    - Content-based hash checking (ignoring metadata)
    - Proper file creation order
    - Deduplication of identical repairs
    
    Args:
        pdf_path: Path to PDF to fix
        quality: Ghostscript quality setting
        
    Returns:
        Tuple of (output_path, was_created_new, status_message)
        - output_path: Path to fixed file (None if failed)
        - was_created_new: True if new file created, False if reused existing
        - status_message: Human-readable status
    """
    try:
        from pdf_manipulator.core.ghostscript import fix_malformed_pdf
        
        # Use existing idempotent logic - this preserves all the debugging work
        output_path, new_size = fix_malformed_pdf(pdf_path, quality=quality)
        
        if output_path and output_path.exists():
            # Check if this was a new creation or reused existing
            canonical_path = pdf_path.parent / f"{pdf_path.stem}_gs_fixed.pdf"
            was_created_new = output_path == canonical_path
            
            original_size = pdf_path.stat().st_size / (1024 * 1024)
            
            if was_created_new:
                status = f"Created fixed PDF: {output_path.name} ({original_size:.1f} MB → {new_size:.1f} MB)"
            else:
                status = f"Using existing identical repair: {output_path.name}"
            
            return output_path, was_created_new, status
        else:
            return None, False, "Failed to create fixed PDF"
            
    except Exception as e:
        return None, False, f"Error during repair: {e}"


#################################################################################################
# Context-Aware Interactive Functions

def offer_malformation_fix(pdf_path: Path, 
                          operation_context: str = "operation",
                          batch_mode: bool = False,
                          no_auto_fix: bool = False) -> Optional[Path]:
    """
    Offer to fix malformed PDF with proper batch mode handling.
    
    Args:
        pdf_path: Path to PDF file
        operation_context: Context for user messaging ("analysis", "optimization", "extraction", etc.)
        batch_mode: Whether running in batch mode
        no_auto_fix: Whether to disable auto-fixing in batch mode
        
    Returns:
        Path to use (original or fixed), or None if user cancelled
    """
    # Check for malformation
    is_malformed, description = check_pdf_malformation(pdf_path)
    
    if not is_malformed:
        return pdf_path  # No issues, use original
    
    # Show context-aware malformation warning
    _show_malformation_warning(description, operation_context)
    
    # Check if Ghostscript is available
    if not check_ghostscript_available():
        return _handle_no_ghostscript(pdf_path, operation_context, batch_mode, no_auto_fix)
    
    # Handle batch mode logic
    if batch_mode:
        if no_auto_fix:
            console.print("[yellow]Batch mode with --no-auto-fix: continuing with malformed PDF[/yellow]")
            return pdf_path
        else:
            console.print("[blue]Batch mode: automatically fixing malformed PDF[/blue]")
            return _attempt_fix_with_feedback(pdf_path, operation_context, auto_mode=True)
    
    # Interactive mode - ask user
    fix_prompt = _get_fix_prompt(operation_context)
    if not Confirm.ask(fix_prompt, default=True):
        console.print(f"[yellow]Continuing {operation_context} with malformed PDF (results may be suboptimal)[/yellow]")
        return pdf_path
    
    # Attempt to fix
    return _attempt_fix_with_feedback(pdf_path, operation_context, auto_mode=False)


def _show_malformation_warning(description: str, operation_context: str):
    """Show context-aware malformation warning."""
    console.print(f"\n[yellow]⚠️  Malformed PDF detected:[/yellow]")
    console.print(f"[yellow]{description}[/yellow]")
    
    # Context-specific impact messaging
    impact_messages = {
        "analysis": "This may affect analysis accuracy and page size calculations",
        "optimization": "This will reduce optimization effectiveness (repair often saves more space)",
        "extraction": "This may cause processing errors or unexpected results",
        "operation": "This may affect processing results"
    }
    
    impact = impact_messages.get(operation_context, impact_messages["operation"])
    console.print(f"[yellow]{impact}[/yellow]")


def _get_fix_prompt(operation_context: str) -> str:
    """Get context-appropriate fix prompt."""
    prompts = {
        "analysis": "Fix with Ghostscript before analysis? (Recommended)",
        "optimization": "Fix structural issues before optimization? (Often saves more space)",
        "extraction": "Fix with Ghostscript before extraction? (Prevents errors)",
        "operation": "Fix with Ghostscript before proceeding? (Recommended)"
    }
    
    return prompts.get(operation_context, prompts["operation"])


def _handle_no_ghostscript(pdf_path: Path, operation_context: str, batch_mode: bool, no_auto_fix: bool = False) -> Optional[Path]:
    """Handle case where Ghostscript is not available."""
    console.print("[yellow]Ghostscript not available for fixing[/yellow]")
    console.print("[dim]Install with: brew install ghostscript (macOS) or apt install ghostscript (Ubuntu)[/dim]")
    
    if batch_mode:
        console.print(f"[yellow]Batch mode: continuing {operation_context} with malformed PDF[/yellow]")
        return pdf_path
    
    if Confirm.ask(f"Continue {operation_context} with malformed PDF anyway?", default=True):
        return pdf_path
    else:
        console.print(f"[blue]{operation_context.title()} cancelled[/blue]")
        return None


def _attempt_fix_with_feedback(pdf_path: Path, operation_context: str, auto_mode: bool = False) -> Optional[Path]:
    """Attempt to fix PDF with appropriate user feedback."""
    if auto_mode:
        console.print(f"[blue]Auto-fixing {pdf_path.name} with Ghostscript...[/blue]")
    else:
        console.print(f"\n[blue]Fixing {pdf_path.name} with Ghostscript...[/blue]")
    
    output_path, was_created_new, status_message = fix_pdf_idempotent(pdf_path)
    
    if output_path:
        console.print(f"[green]✓ {status_message}[/green]")
        if auto_mode:
            console.print(f"[green]✓ Auto-fixed PDF will be used for {operation_context}[/green]")
        else:
            console.print(f"[green]✓ Using fixed PDF for {operation_context}[/green]")
        return output_path
    else:
        console.print(f"[red]{status_message}[/red]")
        
        if auto_mode:
            console.print(f"[yellow]Auto-fix failed, continuing {operation_context} with malformed PDF[/yellow]")
            return pdf_path
        
        if Confirm.ask(f"Continue {operation_context} with original malformed PDF?", default=True):
            console.print(f"[yellow]Continuing {operation_context} with malformed PDF (results may be suboptimal)[/yellow]")
            return pdf_path
        else:
            console.print(f"[blue]{operation_context.title()} cancelled[/blue]")
            return None


#################################################################################################
# Early check in CLI

def check_and_fix_malformation_early(pdf_files: list, args) -> list:
    """Early malformation check for CLI scanning phase."""
    if len(pdf_files) == 1:
        pdf_path, page_count, file_size = pdf_files[0]
        
        fixed_path = offer_malformation_fix(
            pdf_path, 
            "scanning",  # Context: just scanning, no specific operation yet
            getattr(args, 'batch', False),
            getattr(args, 'no_auto_fix', False)
        )
        
        if fixed_path is None:
            console.print("[blue]Scanning cancelled[/blue]")
            sys.exit(0)
        
        # Update file info if PDF was fixed
        if fixed_path != pdf_path:
            
            new_page_count, new_file_size = get_pdf_info(fixed_path)
            return [(fixed_path, new_page_count, new_file_size)]
    
    return pdf_files


#################################################################################################
# Batch Processing Functions

def check_and_fix_malformation_batch(pdf_files: list[tuple[Path, int, float]], 
                                    operation_context: str = "operation") -> list[tuple[Path, int, float]]:
    """
    Check for malformed PDFs in batch mode - just warn briefly.
    
    Args:
        pdf_files: List of (pdf_path, page_count, file_size) tuples
        operation_context: Context for messaging
        
    Returns:
        Original pdf_files list (unchanged in batch mode)
    """
    if not pdf_files:
        return pdf_files
    
    # Find malformed files
    malformed_count = 0
    for pdf_path, page_count, file_size in pdf_files:
        is_malformed, description = check_pdf_malformation(pdf_path)
        if is_malformed:
            malformed_count += 1
    
    if malformed_count > 0:
        context_messages = {
            "analysis": "Individual files will be checked during analysis",
            "optimization": "Consider fixing malformed files first for better optimization",
            "extraction": "Individual files will be checked during processing"
        }
        
        message = context_messages.get(operation_context, "Individual files will be checked during processing")
        
        console.print(f"\n[yellow]⚠️  Found {malformed_count} malformed PDFs[/yellow]")
        console.print(f"[dim]{message}[/dim]")
    
    return pdf_files


#################################################################################################
# Convenience Functions for Common Use Cases

def ensure_pdf_ready_for_analysis(pdf_path: Path, batch_mode: bool = False, no_auto_fix: bool = False) -> Optional[Path]:
    """Ensure PDF is ready for analysis (fix if needed)."""
    return offer_malformation_fix(pdf_path, "analysis", batch_mode, no_auto_fix)


def ensure_pdf_ready_for_optimization(pdf_path: Path, batch_mode: bool = False, no_auto_fix: bool = False) -> Optional[Path]:
    """Ensure PDF is ready for optimization (fix if needed)."""
    return offer_malformation_fix(pdf_path, "optimization", batch_mode, no_auto_fix)


def ensure_pdf_ready_for_extraction(pdf_path: Path, batch_mode: bool = False, no_auto_fix: bool = False) -> Optional[Path]:
    """Ensure PDF is ready for extraction (fix if needed)."""
    return offer_malformation_fix(pdf_path, "extraction", batch_mode, no_auto_fix)


#################################################################################################
# Backward Compatibility Wrapper

def check_and_fix_malformation_with_args(pdf_files: list[tuple[Path, int, float]], 
                                                    args: Any) -> list[tuple[Path, int, float]]:
    """
    Legacy wrapper for existing extraction code.
    
    This preserves the existing API while using the new utility functions.
    """
    if not pdf_files:
        return []
    
    # Extract relevant flags from args
    batch_mode = getattr(args, 'batch', False)
    no_auto_fix = getattr(args, 'no_auto_fix', False)
    
    # For single file processing
    if len(pdf_files) == 1:
        pdf_path, page_count, file_size = pdf_files[0]
        
        fixed_path = ensure_pdf_ready_for_extraction(pdf_path, batch_mode, no_auto_fix)
        
        if fixed_path is None:
            return []  # User cancelled
        
        # Update file info if PDF was fixed
        if fixed_path != pdf_path:
            from pdf_manipulator.core.scanner import get_pdf_info
            new_page_count, new_file_size = get_pdf_info(fixed_path)
            return [(fixed_path, new_page_count, new_file_size)]
        else:
            return pdf_files
    
    # For batch processing
    else:
        if batch_mode and not no_auto_fix:
            # Auto-fix each file in batch mode
            console.print("[blue]Batch mode: auto-fixing malformed PDFs[/blue]")
            fixed_files = []
            
            for pdf_path, page_count, file_size in pdf_files:
                fixed_path = ensure_pdf_ready_for_extraction(pdf_path, batch_mode=True, no_auto_fix=False)
                
                if fixed_path:
                    if fixed_path != pdf_path:
                        # Update file info for fixed PDF
                        from pdf_manipulator.core.scanner import get_pdf_info
                        new_page_count, new_file_size = get_pdf_info(fixed_path)
                        fixed_files.append((fixed_path, new_page_count, new_file_size))
                    else:
                        fixed_files.append((pdf_path, page_count, file_size))
                # If fixed_path is None (shouldn't happen in auto mode), skip the file
            
            return fixed_files
        else:
            # No auto-fix or not batch mode - just warn about malformed files
            return check_and_fix_malformation_batch(pdf_files, "extraction")


#################################################################################################
# Integration Helpers

def get_malformation_status_summary(pdf_files: list[tuple[Path, int, float]]) -> dict[str, Any]:
    """
    Get summary of malformation status across multiple files.
    
    Returns:
        Dictionary with malformation statistics
    """
    total_files = len(pdf_files)
    malformed_files = []
    malformation_types = {}
    
    for pdf_path, _, _ in pdf_files:
        is_malformed, description = check_pdf_malformation(pdf_path)
        if is_malformed:
            malformed_files.append((pdf_path, description))
            # Categorize malformation types
            if "Structural corruption" in description:
                malformation_types["structural"] = malformation_types.get("structural", 0) + 1
            elif "Resource duplication" in description:
                malformation_types["resource_duplication"] = malformation_types.get("resource_duplication", 0) + 1
            else:
                malformation_types["other"] = malformation_types.get("other", 0) + 1
    
    return {
        "total_files": total_files,
        "malformed_count": len(malformed_files),
        "malformed_files": malformed_files,
        "malformation_types": malformation_types,
        "ghostscript_available": check_ghostscript_available()
    }
