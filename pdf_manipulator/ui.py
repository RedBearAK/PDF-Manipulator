"""User interface components - prompts, displays, interactions."""

from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from pdf_manipulator.core.parser import PageGroup

console = Console()



def show_single_file_help(page_count: int):
    """Show available operations for single file mode."""
    if page_count > 1:
        console.print(f"\n[yellow]This PDF has {page_count} pages.[/yellow]")
        console.print("\nAvailable operations:")
        console.print("  --strip-first      Strip to first page only")
        console.print("  --extract-pages    Extract specific pages (e.g., \"3-7\", \"last 2\")")
        console.print("  --separate-files   Use with --extract-pages to create separate files")
        console.print("  --respect-groups   Use with --extract-pages to respect groupings")
        console.print("  --split-pages      Split into individual pages")
        console.print("  --optimize         Optimize file size")
        console.print("  --analyze          Analyze PDF contents")


def show_folder_help(pdf_files: list[tuple[Path, int, float]]):
    """Show available operations for folder mode."""
    multi_page_count = sum(1 for _, pages, _ in pdf_files if pages > 1)
    if multi_page_count > 0:
        console.print(f"\n[yellow]Found {multi_page_count} multi-page PDF(s).[/yellow]")
        console.print("\nAvailable operations:")
        console.print("  --strip-first      Strip to first page only")
        console.print("  --extract-pages    Extract specific pages (e.g., \"3-7\", \"last 2\")")
        console.print("  --separate-files   Use with --extract-pages to create separate files")
        console.print("  --respect-groups   Use with --extract-pages to respect groupings")
        console.print("  --split-pages      Split into individual pages")
        console.print("  --optimize         Optimize file sizes")
        console.print("  --analyze          Analyze PDF contents")
        console.print("\nAdd --batch to process all files without prompting")
        console.print("Add --replace to overwrite originals (use with extreme caution!)")


def display_pdf_table(pdf_files: list[tuple[Path, int, float]], title: str = "PDF Files Assessment"):
    """Display PDF files in a formatted table."""
    table = Table(title=title)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Pages", justify="right", style="magenta")
    table.add_column("Size (MB)", justify="right", style="green")
    table.add_column("Status", style="yellow")

    for pdf_path, page_count, file_size in pdf_files:
        status = "⚠️  Multi-page" if page_count > 1 else "✓ Single page"
        table.add_row(
            pdf_path.name,
            str(page_count),
            f"{file_size:.2f}",
            status
        )

    console.print(table)


def decide_extraction_mode(pages_to_extract: set[int], groups: list[PageGroup], interactive: bool = True) -> str:
    """
    Decide extraction mode. Returns 'single', 'separate', or 'grouped'.
    """
    if not interactive:
        return 'single'  # Default to single document in batch mode
    
    num_pages = len(pages_to_extract)
    num_groups = len(groups)
    
    if num_pages == 1:
        return 'single'  # Single page - no need to ask
    
    # Show what groups we detected
    console.print(f"\n[yellow]Extracting {num_pages} pages in {num_groups} groups:[/yellow]")
    for group in groups:
        if group.is_range:
            page_range = f"{min(group.pages)}-{max(group.pages)}" if len(group.pages) > 1 else str(group.pages[0])
            console.print(f"  Range: {group.original_spec} → pages {page_range}")
        else:
            console.print(f"  Single: page {group.pages[0]}")
    
    console.print("\nHow would you like to extract these pages?")
    console.print("  1. As a single document (combine all pages)")
    console.print("  2. As separate documents (one file per page)")
    console.print("  3. Respect groupings (ranges→multi-page, individuals→single files)")
    
    while True:
        choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="1")
        if choice == "1":
            return 'single'
        elif choice == "2":
            return 'separate'
        elif choice == "3":
            return 'grouped'
