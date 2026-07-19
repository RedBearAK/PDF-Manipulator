"""
Per-File Smart Naming Test Module
File: tests/test_per_file_smart_naming.py

Tests smart (pattern + template) naming in separate and grouped extraction:
- Separate mode: each page names itself (source_page = the extracted page)
- Grouped mode: each group names itself from its first page
- Document-level pg specs stay document-level across all outputs
- Duplicate extracted values resolve to unique filenames
- Dry runs preview REAL extracted names, not PREVIEW_* placeholders

Run: python tests/test_per_file_smart_naming.py   (or pytest)
"""

import io
import sys
import tempfile
import contextlib

from pathlib import Path

# Add the project root and tests dir to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console

from opctx_test_helpers import setup_context


console = Console()

REPORTLAB_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    REPORTLAB_AVAILABLE = False


def _make_invoice_batch_pdf(path: Path, invoice_numbers: list[str], batch_code: str = "BATCH-77"):
    """
    Create a multi-page PDF where each page carries its own invoice number.

    The batch code appears ONLY on page 1, for document-level pg spec tests.
    """
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_idx, invoice in enumerate(invoice_numbers):
        c.drawString(72, 700, "GalaxSea Freight Forwarding")
        c.drawString(72, 680, f"Invoice Number: {invoice}")
        if page_idx == 0:
            c.drawString(72, 660, f"Batch: {batch_code}")
        c.showPage()
    c.save()


def test_separate_mode_per_page_naming():
    """Each separately extracted page is named from its OWN content."""
    console.print("\n[cyan]Testing separate mode per-page naming...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    from pdf_manipulator.core.operations import extract_pages_separate
    from pdf_manipulator.core.text_extraction import clear_text_cache

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "batch.pdf"
        _make_invoice_batch_pdf(pdf_path, ["INV-001", "INV-002", "INV-003"])

        setup_context("1-3", 3, pdf_path,
                        dry_run=False, conflicts='rename', batch=True,
                        scrape_pattern=["inv=Invoice Number:wd1"],
                        filename_template="{inv}_{range}.pdf")
        results = extract_pages_separate()

        created = sorted(f.name for f in workdir.glob("INV-*.pdf"))
        expected = ["INV-001_page01.pdf", "INV-002_page02.pdf", "INV-003_page03.pdf"]

        ok_count = len(results) == 3
        ok_names = created == expected
        if not ok_names:
            console.print(f"  [dim]created: {created}[/dim]")

        # Each output must be a valid one-page PDF
        ok_valid = True
        from pypdf import PdfReader
        for output_path, _size in results:
            try:
                if len(PdfReader(output_path).pages) != 1:
                    ok_valid = False
            except Exception:
                ok_valid = False

    clear_text_cache()

    checks = [
        (ok_count, "three files created"),
        (ok_names, "each page named from its own invoice number"),
        (ok_valid, "each output is a valid one-page PDF"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_grouped_mode_per_group_naming():
    """Each extracted group is named from its FIRST page's content."""
    console.print("\n[cyan]Testing grouped mode per-group naming...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    from pdf_manipulator.core.operations import extract_pages_grouped
    from pdf_manipulator.core.text_extraction import clear_text_cache

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "batch.pdf"
        # Pages 1-2 form one invoice (INV-100 on page 1), page 3 another
        _make_invoice_batch_pdf(pdf_path, ["INV-100", "INV-100-CONT", "INV-200"])

        setup_context("1-2,3", 3, pdf_path,
                        dry_run=False, conflicts='rename', batch=True,
                        dedup='groups',
                        scrape_pattern=["inv=Invoice Number:wd1"],
                        filename_template="{inv}_{range}.pdf")
        results = extract_pages_grouped()

        created = sorted(f.name for f in workdir.glob("INV-*.pdf"))
        expected = ["INV-100_group01.pdf", "INV-200_group02.pdf"]

        ok_count = len(results) == 2
        ok_names = created == expected
        if not ok_names:
            console.print(f"  [dim]created: {created}[/dim]")

        # First group must contain both of its pages
        ok_pages = False
        if results:
            from pypdf import PdfReader
            try:
                ok_pages = len(PdfReader(results[0][0]).pages) == 2
            except Exception:
                ok_pages = False

    clear_text_cache()

    checks = [
        (ok_count, "two group files created"),
        (ok_names, "each group named from its first page"),
        (ok_pages, "first group contains both of its pages"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_document_level_pg_spec():
    """Patterns with explicit pg specs stay document-level across outputs."""
    console.print("\n[cyan]Testing document-level pg spec across outputs...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    from pdf_manipulator.core.operations import extract_pages_separate
    from pdf_manipulator.core.text_extraction import clear_text_cache

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "batch.pdf"
        # Batch code only exists on page 1; pg1 spec must find it for BOTH files
        _make_invoice_batch_pdf(pdf_path, ["INV-001", "INV-002"], batch_code="BATCH-77")

        setup_context("1-2", 2, pdf_path,
                        dry_run=False, conflicts='rename', batch=True,
                        scrape_pattern=["inv=Invoice Number:wd1",
                                        "batch=Batch:wd1pg1"],
                        filename_template="{batch}_{inv}.pdf")
        results = extract_pages_separate()

        created = sorted(f.name for f in workdir.glob("BATCH-*.pdf"))
        expected = ["BATCH-77_INV-001.pdf", "BATCH-77_INV-002.pdf"]
        ok_names = created == expected
        if not ok_names:
            console.print(f"  [dim]created: {created}[/dim]")

    clear_text_cache()

    marker = "✓" if ok_names else "[red]✗[/red]"
    console.print(f"  {marker} pg1 batch code shared, per-page invoice numbers distinct")
    return ok_names


def test_duplicate_values_and_dry_run():
    """Duplicate extracted values get unique names; dry runs show real names."""
    console.print("\n[cyan]Testing duplicate values and dry-run naming...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    from pdf_manipulator.core.operations import extract_pages_separate
    from pdf_manipulator.core.text_extraction import clear_text_cache

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        pdf_path = workdir / "batch.pdf"
        # Two pages with the SAME invoice number and a template ignoring {range}
        _make_invoice_batch_pdf(pdf_path, ["INV-DUP", "INV-DUP"])

        setup_context("1-2", 2, pdf_path,
                        dry_run=False, conflicts='rename', batch=True,
                        scrape_pattern=["inv=Invoice Number:wd1"],
                        filename_template="{inv}.pdf")
        results = extract_pages_separate()

        created = sorted(f.name for f in workdir.glob("INV-DUP*.pdf"))
        ok_two_files = len(created) == 2
        ok_unique = len(set(created)) == 2
        if not (ok_two_files and ok_unique):
            console.print(f"  [dim]created: {created}[/dim]")

        # Dry run: captured output must contain the REAL extracted name,
        # never a PREVIEW_* placeholder
        clear_text_cache()
        pdf_path2 = workdir / "dryrun.pdf"
        _make_invoice_batch_pdf(pdf_path2, ["INV-REAL"])
        setup_context("1", 1, pdf_path2,
                        dry_run=True, conflicts='rename', batch=True,
                        scrape_pattern=["inv=Invoice Number:wd1"],
                        filename_template="{inv}_{range}.pdf")
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            extract_pages_separate()
        output = capture.getvalue()
        ok_real_name = "INV-REAL" in output
        ok_no_preview = "PREVIEW" not in output
        if not (ok_real_name and ok_no_preview):
            console.print(f"  [dim]dry-run output: {output[-200:]}[/dim]")

    clear_text_cache()

    checks = [
        (ok_two_files, "duplicate values produced two files"),
        (ok_unique, "conflict resolution made the names unique"),
        (ok_real_name, "dry run shows the real extracted name"),
        (ok_no_preview, "dry run contains no PREVIEW placeholders"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def main():
    """Run all per-file smart naming tests and report the score."""
    console.print("[bold blue]Per-File Smart Naming Tests[/bold blue]")

    tests = [
        ("Separate Mode Per-Page Naming", test_separate_mode_per_page_naming),
        ("Grouped Mode Per-Group Naming", test_grouped_mode_per_group_naming),
        ("Document-Level pg Spec", test_document_level_pg_spec),
        ("Duplicates and Dry-Run Naming", test_duplicate_values_and_dry_run),
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
