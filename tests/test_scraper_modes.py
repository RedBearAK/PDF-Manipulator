"""
Standalone Scraper Modes and Smart Renaming CLI Test Module
File: tests/test_scraper_modes.py

End-to-end tests through the real CLI (subprocess execution) covering:
- --dump-text to stdout and to a file
- --scrape-text with Phase 4 patterns (including % end trimming) to TSV
- --text-file sidecar as the text source
- --extract-pages with --scrape-pattern + --filename-template smart renaming

Run: python tests/test_scraper_modes.py   (or pytest)
"""

import sys
import tempfile
import subprocess

from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console


console = Console()

PROJECT_ROOT = Path(__file__).parent.parent

REPORTLAB_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    REPORTLAB_AVAILABLE = False


def _make_invoice_pdf(path: Path):
    """Create a two-page invoice-like PDF with known content."""
    c = canvas.Canvas(str(path), pagesize=letter)
    # Page 1
    for y, line in [
        (700, "GalaxSea Freight Forwarding"),
        (680, "Invoice Number: INV-2024-001-DRAFT"),
        (670, "Invoice Date: 7/23/2026"),
        (660, "Place of receipt KODIAK, AK"),
        (640, "Total: $1,250.00"),
    ]:
        c.drawString(72, y, line)
    c.showPage()
    # Page 2
    for y, line in [
        (700, "Continuation page"),
        (680, "Place of receipt VALDEZ, AK"),
    ]:
        c.drawString(72, y, line)
    c.showPage()
    c.save()


def _run_cli(cli_args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run the pdf-manipulator CLI as a subprocess from the given directory."""
    return subprocess.run(
        [sys.executable, '-m', 'pdf_manipulator'] + cli_args,
        capture_output=True, text=True, timeout=120, cwd=str(cwd),
        env={'PYTHONPATH': str(PROJECT_ROOT), 'PATH': '/usr/bin:/bin:/usr/local/bin'},
    )


def test_dump_text_modes():
    """--dump-text writes page-by-page text to stdout and to a file."""
    console.print("\n[cyan]Testing --dump-text...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "invoice.pdf"
        _make_invoice_pdf(pdf_path)

        # To stdout
        result = _run_cli([str(pdf_path), '--dump-text'], workdir)
        ok_exit = result.returncode == 0
        ok_pages = '--- PAGE 1 ---' in result.stdout and '--- PAGE 2 ---' in result.stdout
        ok_content = 'KODIAK, AK' in result.stdout and 'VALDEZ, AK' in result.stdout

        # To a file
        out_path = workdir / "dump.txt"
        result2 = _run_cli([str(pdf_path), '--dump-text', '--output', str(out_path)], workdir)
        dumped = out_path.read_text(encoding='utf-8') if out_path.exists() else ""
        ok_file = result2.returncode == 0 and 'KODIAK, AK' in dumped

    checks = [
        (ok_exit, "exit code 0"),
        (ok_pages, "page markers present"),
        (ok_content, "both pages' content present"),
        (ok_file, "--output writes the dump to a file"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_scrape_text_with_trimming():
    """--scrape-text extracts Phase 4 patterns (with % trimming) into a TSV."""
    console.print("\n[cyan]Testing --scrape-text with % trimming...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "invoice.pdf"
        _make_invoice_pdf(pdf_path)
        tsv_path = workdir / "out.tsv"

        result = _run_cli([
            str(pdf_path), '--scrape-text',
            # "Invoice Number: INV-2024-001-DRAFT" -> word after keyword,
            # then trim 6 chars ("-DRAFT") from the end
            '--scrape-pattern', 'invoice=Invoice Number:wd1%ch6',
            # "Total: $1,250.00" -> number extraction
            '--scrape-pattern', 'total=Total:nb1',
            # Page 2 content via pg spec
            '--scrape-pattern', 'receipt2=Place of receipt:wd2pg2',
            '--output', str(tsv_path),
        ], workdir)

        ok_exit = result.returncode == 0
        content = tsv_path.read_text(encoding='utf-8') if tsv_path.exists() else ""
        lines = [ln for ln in content.splitlines() if ln.strip()]

        ok_header = bool(lines) and lines[0].split('\t') == \
            ['filename', 'invoice', 'total', 'receipt2']
        row = lines[1].split('\t') if len(lines) > 1 else []
        ok_trimmed = len(row) > 1 and row[1] == 'INV-2024-001'
        ok_number = len(row) > 2 and '1,250' in row[2]
        ok_page2 = len(row) > 3 and 'VALDEZ' in row[3]

        if not (ok_trimmed and ok_number and ok_page2):
            console.print(f"  [dim]TSV row: {row}[/dim]")
            console.print(f"  [dim]stderr: {result.stderr[-300:]}[/dim]")

    checks = [
        (ok_exit, "exit code 0"),
        (ok_header, "TSV header is filename + variables in order"),
        (ok_trimmed, "% end trimming removed '-DRAFT' suffix"),
        (ok_number, "number extraction captured the total"),
        (ok_page2, "pg2 spec reached page 2 content"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_sidecar_text_source():
    """--text-file overrides PDF extraction for both dump and scrape modes."""
    console.print("\n[cyan]Testing --text-file sidecar source...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "invoice.pdf"
        _make_invoice_pdf(pdf_path)

        sidecar = workdir / "corrected.txt"
        sidecar.write_text(
            "=== page 1 ===\n"
            "CORRECTED Invoice Number: FIXED-999\n"
            "=== page 2 ===\n"
            "CORRECTED second page\n",
            encoding='utf-8'
        )

        # Dump uses sidecar text, not PDF text
        result = _run_cli([str(pdf_path), '--dump-text', '--text-file', str(sidecar)], workdir)
        ok_sidecar_text = 'FIXED-999' in result.stdout
        ok_not_pdf_text = 'KODIAK' not in result.stdout

        # Scrape sees the sidecar too
        tsv_path = workdir / "out.tsv"
        result2 = _run_cli([
            str(pdf_path), '--scrape-text', '--text-file', str(sidecar),
            '--scrape-pattern', 'invoice=Invoice Number:wd1',
            '--output', str(tsv_path),
        ], workdir)
        content = tsv_path.read_text(encoding='utf-8') if tsv_path.exists() else ""
        ok_scrape = result2.returncode == 0 and 'FIXED-999' in content

        # Folder path with --text-file must be rejected
        result3 = _run_cli([str(workdir), '--dump-text', '--text-file', str(sidecar)], workdir)
        ok_folder_rejected = result3.returncode != 0

    checks = [
        (ok_sidecar_text, "dump shows sidecar text"),
        (ok_not_pdf_text, "dump excludes PDF-extracted text"),
        (ok_scrape, "scrape pattern matched against sidecar text"),
        (ok_folder_rejected, "--text-file with a folder is rejected"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_smart_rename_extraction():
    """--extract-pages with patterns + template names the output from content."""
    console.print("\n[cyan]Testing smart renaming during extraction...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "invoice.pdf"
        _make_invoice_pdf(pdf_path)

        result = _run_cli([
            str(pdf_path), '--extract-pages=1', '--batch',
            '--scrape-pattern', 'invoice=Invoice Number:wd1%ch6',
            # Date contains slashes: pins the sanitizer regression where
            # "7/23/2026" took the monetary branch and kept its slashes
            '--scrape-pattern', 'date=Invoice Date:wd1',
            '--filename-template', '{invoice}_{date}_pages{range}.pdf',
        ], workdir)

        created = sorted(workdir.glob('INV-2024-001_7-23-2026*.pdf'))
        ok_created = len(created) == 1
        ok_exit = result.returncode == 0

        if not ok_created:
            console.print(f"  [dim]dir: {[f.name for f in workdir.iterdir()]}[/dim]")
            console.print(f"  [dim]stderr: {result.stderr[-400:]}[/dim]")

        # The output must be a valid one-page PDF
        ok_valid = False
        if ok_created:
            from pypdf import PdfReader
            try:
                reader = PdfReader(created[0])
                ok_valid = len(reader.pages) == 1
            except Exception:
                ok_valid = False

    checks = [
        (ok_exit, "exit code 0"),
        (ok_created, "output named from extracted content, slashes sanitized"),
        (ok_valid, "output is a valid one-page PDF"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def main():
    """Run all scraper mode tests and report the score."""
    console.print("[bold blue]Standalone Scraper Modes and Smart Renaming Tests[/bold blue]")

    tests = [
        ("Dump Text Modes", test_dump_text_modes),
        ("Scrape Text with Trimming", test_scrape_text_with_trimming),
        ("Sidecar Text Source", test_sidecar_text_source),
        ("Smart Rename Extraction", test_smart_rename_extraction),
    ]

    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                console.print(f"[red]✗ {test_name} failed[/red]")
        except Exception as e:
            console.print(f"[red]✗ {test_name} crashed: {e}[/red]")

    console.print(f"\nScore: {passed}/{len(tests)} tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    exit(main())


# End of file #
