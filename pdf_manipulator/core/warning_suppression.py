"""
PDF Warning Suppression System
Create: pdf_manipulator/core/warning_suppression.py

This module provides comprehensive suppression of noisy PyPDF warnings
while still allowing important errors to surface.
"""

import io
import sys
import warnings

from typing import Optional
from contextlib import contextmanager, redirect_stderr
from rich.console import Console


console = Console()


class PDFWarningFilter:
    """Filter and categorize PDF-related warnings."""
    
    # Patterns for warnings we want to suppress
    SUPPRESS_PATTERNS = [
        "Ignoring wrong pointing object",
        "wrong pointing object",
        "Object stream not found",
        "Invalid destination",
        "Broken outline",
        "Invalid parent",
        "Multiple definitions",
        "Stream length invalid",
        "Corrupted object",
    ]
    
    # Patterns for warnings we want to keep (important errors)
    KEEP_PATTERNS = [
        "Could not read",
        "File not found", 
        "Permission denied",
        "Invalid PDF",
        "Encrypted PDF",
    ]
    
    def __init__(self):
        self.suppressed_count = 0
        self.suppressed_types = {}
        self.important_warnings = []
    
    def should_suppress(self, warning_text: str) -> bool:
        """Check if a warning should be suppressed."""
        warning_lower = warning_text.lower()
        
        # Keep important warnings
        for pattern in self.KEEP_PATTERNS:
            if pattern.lower() in warning_lower:
                self.important_warnings.append(warning_text)
                return False
        
        # Suppress noisy warnings
        for pattern in self.SUPPRESS_PATTERNS:
            if pattern.lower() in warning_lower:
                self.suppressed_count += 1
                self.suppressed_types[pattern] = self.suppressed_types.get(pattern, 0) + 1
                return True
        
        return False
    
    def get_summary(self) -> Optional[str]:
        """Get a summary of suppressed warnings."""
        if self.suppressed_count == 0:
            return None
        
        if self.suppressed_count == 1:
            return f"Suppressed 1 PDF structure warning"
        
        # Group similar warnings
        major_issues = []
        for pattern, count in self.suppressed_types.items():
            if count > 1:
                major_issues.append(f"{count}x {pattern}")
            else:
                major_issues.append(pattern)
        
        if len(major_issues) <= 2:
            detail = f" ({', '.join(major_issues)})"
        else:
            detail = f" ({len(self.suppressed_types)} types)"
        
        return f"Suppressed {self.suppressed_count} PDF structure warnings{detail}"


class FilteredStringIO(io.StringIO):
    """StringIO that filters warnings through PDFWarningFilter."""
    
    def __init__(self, filter_instance: PDFWarningFilter):
        super().__init__()
        self.filter = filter_instance
        self.original_stderr = sys.stderr
    
    def write(self, text: str) -> int:
        """Write text, filtering out unwanted warnings."""
        if not text or text.isspace():
            return len(text)
        
        lines = text.splitlines(keepends=True)
        kept_lines = []
        
        for line in lines:
            if not self.filter.should_suppress(line):
                kept_lines.append(line)
        
        if kept_lines:
            # Write important warnings to original stderr
            for line in kept_lines:
                self.original_stderr.write(line)
        
        return len(text)  # Always return original length


@contextmanager
def suppress_pdf_warnings(show_summary: bool = False):
    """
    Context manager to suppress noisy PDF warnings while preserving important ones.
    
    Args:
        show_summary: Whether to show a summary of suppressed warnings
    
    Usage:
        with suppress_pdf_warnings(show_summary=True):
            reader = PdfReader(pdf_path)
            # PDF operations here - warnings will be filtered
    """
    warning_filter = PDFWarningFilter()
    filtered_stderr = FilteredStringIO(warning_filter)
    
    # Also suppress Python warnings module
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
        warnings.filterwarnings("ignore", message=".*wrong pointing object.*")
        
        with redirect_stderr(filtered_stderr):
            try:
                yield warning_filter
            finally:
                # Show summary if requested and warnings were suppressed
                if show_summary:
                    summary = warning_filter.get_summary()
                    if summary:
                        console.print(f"[dim]{summary}[/dim]")


@contextmanager 
def suppress_all_pdf_warnings():
    """
    Completely suppress all PDF warnings (for batch operations).
    
    Usage:
        with suppress_all_pdf_warnings():
            # All PDF warnings will be completely silenced
            process_many_pdfs()
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        # Redirect stderr to null
        null_stderr = io.StringIO()
        with redirect_stderr(null_stderr):
            yield


def safe_pdf_operation(operation_func, *args, show_warnings: bool = True, **kwargs):
    """
    Safely execute a PDF operation with warning suppression.
    
    Args:
        operation_func: Function to execute
        *args, **kwargs: Arguments for the function
        show_warnings: Whether to show summary of suppressed warnings
    
    Returns:
        Result of operation_func
    """
    try:
        with suppress_pdf_warnings(show_summary=show_warnings):
            return operation_func(*args, **kwargs)
    except Exception as e:
        # Re-raise with additional context
        raise type(e)(f"PDF operation failed: {e}") from e
