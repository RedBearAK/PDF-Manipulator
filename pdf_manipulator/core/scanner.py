"""File system scanning and PDF info extraction."""

from pypdf import PdfReader
from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings

console = Console()


def get_pdf_info(pdf_path: Path) -> tuple[int, float]:
    """Get page count and file size for a PDF."""
    try:
        with suppress_pdf_warnings():
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                page_count = len(reader.pages)

            file_size = pdf_path.stat().st_size / (1024 * 1024)  # Convert to MB
            return page_count, file_size
    except Exception as e:
        console.print(f"[red]Error reading {pdf_path.name}: {e}[/red]")
        return 0, 0


def scan_folder(folder_path: Path) -> list[tuple[Path, int, float]]:
    """Scan folder for PDF files and return their info."""
    pdf_files = []

    for pdf_path in folder_path.glob("*.pdf"):
        # Skip processing hidden files ".", including macOS metadata files "._"
        if pdf_path.name.startswith("."):
            continue
        page_count, file_size = get_pdf_info(pdf_path)
        if page_count > 0:
            pdf_files.append((pdf_path, page_count, file_size))

    return sorted(pdf_files, key=lambda x: x[0].name)


def scan_file(file_path: Path) -> list[tuple[Path, int, float]]:
    """Get info for a single PDF file."""
    if not file_path.exists():
        console.print(f"[red]Error: File {file_path} does not exist[/red]")
        return []

    if not file_path.suffix.lower() == '.pdf':
        console.print(f"[red]Error: {file_path} is not a PDF file[/red]")
        return []

    page_count, file_size = get_pdf_info(file_path)
    if page_count > 0:
        return [(file_path, page_count, file_size)]
    return []
