"""
Enhanced interactive prompts for PDF manipulation operations.
File: pdf_manipulator/ui_enhanced.py
"""

from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

console = Console()


def confirm_deduplication_strategy(duplicate_info: dict, output_mode: str, default_strategy: str) -> str:
    """
    Prompt user to confirm deduplication strategy when duplicates detected.
    
    Args:
        duplicate_info: Dictionary with duplicate analysis results
        output_mode: Output mode ('single', 'separate', 'grouped')  
        default_strategy: Default strategy for this mode
        
    Returns:
        Selected deduplication strategy
    """
    console.print("\n[yellow]⚠️  Duplicate Pages Detected[/yellow]")
    
    # Show duplicate summary
    console.print(f"Found {len(duplicate_info['duplicate_pages'])} pages appearing in multiple groups:")
    console.print(duplicate_info['overlap_summary'])
    
    # Show strategy options with context
    console.print(f"\n[cyan]Deduplication options for {output_mode} mode:[/cyan]")
    
    strategies = {
        'strict': 'Remove all duplicates (first occurrence wins)',
        'groups': 'Allow duplicates between groups, remove within groups',
        'none': 'Keep all duplicates (may create identical pages)',
        'warn': 'Continue with warning (use default strategy)',
        'fail': 'Stop extraction (fix selection manually)'
    }
    
    # Show recommended strategy
    console.print(f"[dim]Recommended for {output_mode} mode: {default_strategy}[/dim]")
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Option", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Effect", style="dim")
    
    for strategy, description in strategies.items():
        if strategy == default_strategy:
            table.add_row(f"[bold]{strategy}[/bold]", f"[bold]{description}[/bold]", "[green]✓ Recommended[/green]")
        else:
            table.add_row(strategy, description, "")
    
    console.print(table)
    
    # Get user choice
    choices = list(strategies.keys())
    selected = Prompt.ask(
        "Choose deduplication strategy",
        choices=choices,
        default=default_strategy
    )
    
    return selected


def prompt_single_filename(default_name: str, page_count: int, argument_summary: str) -> str:
    """
    Allow user to modify single output filename.
    
    Args:
        default_name: Default filename
        page_count: Number of pages being extracted
        argument_summary: Summary of selection arguments
        
    Returns:
        Final filename (with .pdf extension)
    """
    console.print(f"\n[cyan]Single File Output[/cyan]")
    console.print(f"Pages: {page_count}")
    console.print(f"Selection: {argument_summary}")
    console.print(f"Default filename: [bold]{default_name}[/bold]")
    
    if not Confirm.ask("Modify filename?", default=False):
        return default_name
    
    # Extract stem for editing
    stem = default_name.replace('.pdf', '')
    
    while True:
        new_stem = Prompt.ask("Enter filename (without .pdf)", default=stem)
        
        if not new_stem:
            return default_name
        
        new_filename = f"{new_stem}.pdf"
        
        # Basic validation
        if any(char in new_filename for char in '<>:"/\\|?*'):
            console.print("[red]Invalid characters in filename. Please try again.[/red]")
            continue
        
        return new_filename


def prompt_base_filename(default_base: str, group_count: int, argument_summary: str) -> str:
    """
    Allow user to modify base filename for multiple outputs.
    
    Args:
        default_base: Default base filename
        group_count: Number of groups/files to be created
        argument_summary: Summary of selection arguments
        
    Returns:
        Final base filename
    """
    console.print(f"\n[cyan]Multiple File Output[/cyan]")
    console.print(f"Will create: {group_count} files")
    console.print(f"Selection: {argument_summary}")
    console.print(f"Base filename: [bold]{default_base}[/bold]")
    console.print("[dim]Individual files will be: {base}_group1.pdf, {base}_group2.pdf, etc.[/dim]")
    
    if not Confirm.ask("Modify base filename?", default=False):
        return default_base
    
    while True:
        new_base = Prompt.ask("Enter base filename", default=default_base)
        
        if not new_base:
            return default_base
        
        # Basic validation
        if any(char in new_base for char in '<>:"/\\|?*'):
            console.print("[red]Invalid characters in filename. Please try again.[/red]")
            continue
        
        return new_base


def show_extraction_preview(pdf_path: Path, pages_to_extract: set, groups: list, 
                           extraction_mode: str, output_paths: list[Path]) -> bool:
    """
    Show comprehensive preview of extraction operation.
    
    Args:
        pdf_path: Source PDF file
        pages_to_extract: Set of pages to extract
        groups: List of page groups
        extraction_mode: Extraction mode
        output_paths: Planned output file paths
        
    Returns:
        True if user confirms, False if cancelled
    """
    console.print("\n[cyan]📋 Extraction Preview[/cyan]")
    
    # Source info
    console.print(f"[bold]Source:[/bold] {pdf_path.name}")
    console.print(f"[bold]Pages to extract:[/bold] {len(pages_to_extract)} pages")
    console.print(f"[bold]Mode:[/bold] {extraction_mode}")
    
    # Group breakdown
    if groups and len(groups) > 1:
        console.print(f"\n[yellow]Groups ({len(groups)}):[/yellow]")
        for i, group in enumerate(groups, 1):
            if hasattr(group, 'pages') and group.pages:
                pages_str = ', '.join(map(str, sorted(group.pages)[:5]))
                if len(group.pages) > 5:
                    pages_str += f" ... ({len(group.pages)} total)"
                spec = getattr(group, 'original_spec', f"group{i}")
                console.print(f"  {i}. {spec}: {pages_str}")
    
    # Output files
    console.print(f"\n[green]Output files ({len(output_paths)}):[/green]")
    for path in output_paths:
        console.print(f"  • {path.name}")
    
    # Size estimation
    estimated_size = estimate_output_size(pdf_path, len(pages_to_extract))
    if estimated_size:
        console.print(f"\n[dim]Estimated total size: ~{estimated_size:.1f} MB[/dim]")
    
    return Confirm.ask("\nProceed with extraction?", default=True)


def show_conflict_resolution_summary(conflicts: list[Path], resolution_strategy: str) -> None:
    """
    Show summary of how file conflicts will be resolved.
    
    Args:
        conflicts: List of conflicting file paths
        resolution_strategy: Selected resolution strategy
    """
    if not conflicts:
        return
    
    console.print(f"\n[yellow]⚠️  File Conflicts ({len(conflicts)})[/yellow]")
    
    strategy_descriptions = {
        'overwrite': 'Will overwrite existing files',
        'skip': 'Will skip existing files (keep originals)',
        'rename': 'Will rename new files with suffix',
        'ask': 'Will prompt for each conflict'
    }
    
    description = strategy_descriptions.get(resolution_strategy, f"Using strategy: {resolution_strategy}")
    console.print(f"[cyan]Resolution:[/cyan] {description}")
    
    if len(conflicts) <= 5:
        for path in conflicts:
            console.print(f"  • {path.name}")
    else:
        for path in conflicts[:3]:
            console.print(f"  • {path.name}")
        console.print(f"  ... and {len(conflicts) - 3} more")


def prompt_complex_operation_confirmation(operation_summary: dict) -> bool:
    """
    Prompt for confirmation of complex operations with multiple steps.
    
    Args:
        operation_summary: Dictionary with operation details
        
    Returns:
        True if user confirms, False otherwise
    """
    console.print("\n[cyan]🔄 Complex Operation Summary[/cyan]")
    
    # Create summary panel
    summary_lines = []
    if 'source_files' in operation_summary:
        summary_lines.append(f"Source files: {operation_summary['source_files']}")
    if 'total_pages' in operation_summary:
        summary_lines.append(f"Total pages: {operation_summary['total_pages']}")
    if 'output_files' in operation_summary:
        summary_lines.append(f"Output files: {operation_summary['output_files']}")
    if 'deduplication' in operation_summary:
        summary_lines.append(f"Deduplication: {operation_summary['deduplication']}")
    if 'conflicts' in operation_summary:
        summary_lines.append(f"File conflicts: {operation_summary['conflicts']}")
    
    panel = Panel(
        "\n".join(summary_lines),
        title="Operation Summary",
        border_style="cyan"
    )
    console.print(panel)
    
    # Show warnings if any
    if 'warnings' in operation_summary and operation_summary['warnings']:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in operation_summary['warnings']:
            console.print(f"  ⚠️  {warning}")
    
    return Confirm.ask("Continue with this operation?", default=True)


def estimate_output_size(pdf_path: Path, page_count: int) -> Optional[float]:
    """
    Estimate output file size based on source PDF.
    
    Args:
        pdf_path: Source PDF file path
        page_count: Number of pages being extracted
        
    Returns:
        Estimated size in MB, or None if cannot estimate
    """
    try:
        source_size = pdf_path.stat().st_size / (1024 * 1024)  # MB
        
        # Get total pages for ratio calculation
        from pypdf import PdfReader
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            total_pages = len(reader.pages)
        
        if total_pages > 0:
            ratio = page_count / total_pages
            return source_size * ratio
    except Exception:
        pass
    
    return None


def show_help_for_complex_extractions() -> None:
    """Show help information for complex extraction scenarios."""
    console.print("\n[cyan]📚 Complex Extraction Help[/cyan]")
    
    help_table = Table(show_header=True, header_style="bold blue")
    help_table.add_column("Scenario", style="yellow")
    help_table.add_column("Recommended Approach", style="white")
    help_table.add_column("Options", style="dim")
    
    scenarios = [
        (
            "Many duplicate pages", 
            "Use --dedup=strict for clean output",
            "--dedup=groups to allow between groups"
        ),
        (
            "File conflicts", 
            "Use --conflicts=rename for safety",
            "--conflicts=ask for manual control"
        ),
        (
            "Complex filenames",
            "Use --smart-names --name-prefix",
            "--no-timestamp to simplify names"
        ),
        (
            "Large batch operations",
            "Use --preview to check first",
            "--interactive for step-by-step control"
        )
    ]
    
    for scenario, approach, options in scenarios:
        help_table.add_row(scenario, approach, options)
    
    console.print(help_table)
    console.print("\n[dim]Use --help for complete option reference[/dim]")


# End of file #
