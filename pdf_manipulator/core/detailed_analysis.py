"""
Enhanced PDF analysis for detailed page-by-page breakdown.
Create: pdf_manipulator/core/detailed_analysis.py
"""

import re
from pathlib import Path
from rich.text import Text
from rich.table import Table
from rich.console import Console

from pdf_manipulator.core.page_analysis import PageAnalyzer
from pdf_manipulator.core.malformation_utils import check_and_fix_malformation_with_args


console = Console()


def analyze_pdf_detailed(pdf_path: Path, show_summary: bool = True) -> None:
    """
    Provide detailed page-by-page analysis to help craft boolean expressions.
    
    Args:
        pdf_path: Path to PDF file
        show_summary: Whether to show summary statistics
    """
    console.print(f"\n[bold blue]📊 Detailed Page Analysis: {pdf_path.name}[/bold blue]\n")
    
    # Check for malformed PDF and offer to fix
    pdf_files = [(pdf_path, 0, 0)]  # Dummy data for malformation checker
    try:
        import argparse
        
        # Create minimal args object for malformation checker
        args = argparse.Namespace()
        args.batch = False
        
        fixed_files = check_and_fix_malformation_with_args(pdf_files, args)
        if not fixed_files:
            console.print("[yellow]Analysis cancelled[/yellow]")
            return
        
        # Use the potentially fixed PDF path
        pdf_path = fixed_files[0][0]
        
    except ImportError:
        # Malformation checker not available, continue with original
        pass
    except Exception as e:
        console.print(f"[yellow]Warning: Could not check for malformation: {e}[/yellow]")
    
    try:
        with PageAnalyzer(pdf_path) as analyzer:
            analyses = analyzer.analyze_all_pages()
            
            if not analyses:
                console.print("[yellow]No pages found in PDF[/yellow]")
                return
            
            # Create detailed table
            _display_detailed_table(analyses)
            
            if show_summary:
                _display_summary_statistics(analyses)
                
    except Exception as e:
        console.print(f"[red]Error analyzing PDF: {e}[/red]")


def _display_detailed_table(analyses: list) -> None:
    """Display detailed page-by-page table."""
    
    table = Table(title="Page-by-Page Analysis")
    table.add_column("Page", style="cyan", justify="right", min_width=4)
    table.add_column("Type", style="magenta", min_width=6)
    table.add_column("Size", style="green", justify="right", min_width=10)  # Increased for MB ranges
    table.add_column("Text Len", style="yellow", justify="right", min_width=8)
    table.add_column("Images", style="red", justify="right", min_width=6)
    table.add_column("Sample Content", style="white", min_width=30, max_width=45)  # Increased for better alignment
    
    for analysis in analyses:
        # Format size appropriately
        size_str = _format_size(analysis.size_bytes)
        
        # Get sample content with consistent formatting
        sample_content = _get_sample_content(analysis, max_length=40)
        
        # Add row with proper text objects to avoid Rich markup issues
        table.add_row(
            str(analysis.page_number),
            analysis.page_type,
            size_str,
            f"{analysis.text_length:,}",  # Add commas to text length too
            str(analysis.image_count),
            Text(sample_content, style="none")  # Prevent Rich markup interpretation
        )
    
    console.print(table)


def _display_summary_statistics(analyses: list) -> None:
    """Display summary statistics about the PDF."""
    
    total_pages = len(analyses)
    total_size = sum(a.size_bytes for a in analyses)
    
    # Type distribution
    type_counts = {}
    size_by_type = {}
    
    for analysis in analyses:
        page_type = analysis.page_type
        type_counts[page_type] = type_counts.get(page_type, 0) + 1
        size_by_type[page_type] = size_by_type.get(page_type, 0) + analysis.size_bytes
    
    console.print(f"\n[bold yellow]📋 Summary Statistics[/bold yellow]")
    console.print(f"Total pages: {total_pages}")
    console.print(f"Total size: {_format_size(total_size)}")
    console.print(f"Average page size: {_format_size(total_size // total_pages if total_pages > 0 else 0)}")
    
    console.print(f"\n[yellow]Page Type Distribution:[/yellow]")
    for page_type in ['text', 'mixed', 'image', 'empty']:
        count = type_counts.get(page_type, 0)
        if count > 0:
            percentage = (count / total_pages) * 100
            avg_size = size_by_type[page_type] / count
            console.print(f"  {page_type:>6}: {count:>3} pages ({percentage:>5.1f}%) - Avg: {_format_size(int(avg_size))}")
    
    # Size distribution
    console.print(f"\n[yellow]Size Distribution:[/yellow]")
    size_ranges = [
        ("< 50 KB", lambda s: s < 50 * 1024),
        ("50-200 KB", lambda s: 50 * 1024 <= s < 200 * 1024),
        ("200KB-1MB", lambda s: 200 * 1024 <= s < 1024 * 1024),
        ("1-5 MB", lambda s: 1024 * 1024 <= s < 5 * 1024 * 1024),
        ("> 5 MB", lambda s: s >= 5 * 1024 * 1024)
    ]
    
    for range_name, condition in size_ranges:
        count = sum(1 for a in analyses if condition(a.size_bytes))
        if count > 0:
            percentage = (count / total_pages) * 100
            console.print(f"  {range_name:>10}: {count:>3} pages ({percentage:>5.1f}%)")


def _format_size(size_bytes: int) -> str:
    """Format size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _get_sample_content(analysis, max_length: int = 35) -> str:
    """
    Get sample content for display with consistent formatting.
    
    Returns quoted text if actual content, parenthetical description if not.
    """
    # For empty pages
    if analysis.page_type == 'empty':
        return "(Empty or minimal content)"
    
    # For image-only pages
    if analysis.page_type == 'image' and analysis.text_length < 50:
        if analysis.image_count == 1:
            return "(Single image/scan)"
        else:
            return f"({analysis.image_count} images/scanned content)"
    
    # For pages with actual text content
    if analysis.text_length >= 20:
        # This is a simplified approach - in a real implementation,
        # we'd need to extract actual text from the PDF page
        # For now, we'll create representative content based on analysis
        
        if analysis.page_type == 'mixed':
            # Format with consistent padding: 4 digits for chars, 2 digits for images
            text_len_formatted = f"{analysis.text_length:,}".rjust(5)  # Right-align with commas
            image_count_formatted = f"{analysis.image_count:2d}"        # 2-digit padding
            return f"(Mixed: {text_len_formatted} chars + {image_count_formatted} images)"
        elif analysis.page_type == 'text':
            # In real implementation, would extract first meaningful sentence
            if analysis.text_length > 500:
                return "(Substantial text content)"
            else:
                return "(Text content)"
    
    # Fallback for edge cases
    return f"({analysis.page_type} content)"


def _extract_sample_text(pdf_path: Path, page_number: int, max_length: int = 30) -> str:
    """
    Extract sample text from a specific page (helper for future enhancement).
    
    This is a placeholder - could be enhanced to extract actual text snippets.
    """
    try:
        from pypdf import PdfReader
        from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings
        
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            page = reader.pages[page_number - 1]  # Convert to 0-indexed
            text = page.extract_text()
            
            if not text or len(text.strip()) < 20:
                return None
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Find first meaningful sentence or phrase
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:  # Meaningful content
                    if len(sentence) <= max_length:
                        return f'"{sentence}"'
                    else:
                        return f'"{sentence[:max_length-3]}..."'
            
            # Fallback to first chunk
            if len(text) <= max_length:
                return f'"{text}"'
            else:
                return f'"{text[:max_length-3]}..."'
                
    except Exception:
        return None


# Integration function for CLI
def handle_detailed_analysis(pdf_path: Path) -> None:
    """Handle --analyze-detailed flag from CLI."""
    try:
        analyze_pdf_detailed(pdf_path, show_summary=True)
        
        console.print("\n[bold green]💡 Analysis Complete![/bold green]")
        console.print("\n[yellow]Use this data to craft boolean expressions:[/yellow]")
        console.print("  • Extract by type: type:text, type:image, type:mixed, type:empty")
        console.print("  • Filter by size: size:<100KB, size:>1MB, size:>=500KB")
        console.print("  • Combine conditions: type:text & size:<500KB")
        console.print("  • Search content: contains:'keyword' or contains/i:'keyword'")
        
    except Exception as e:
        console.print(f"[red]Detailed analysis failed: {e}[/red]")
