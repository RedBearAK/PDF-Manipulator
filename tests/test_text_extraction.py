"""
Unified Text Extraction Test Module
File: tests/test_text_extraction.py

Tests the single-source-of-truth text provider: sidecar parsing, caching,
and the guarantee that page-selection patterns and scraper patterns see
identical text for the same document.

Run: python tests/test_text_extraction.py   (or pytest)
"""

import sys
import tempfile

from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

from pdf_manipulator.core.text_extraction import (
    get_page_text,
    get_page_texts,
    clear_text_cache,
    parse_sidecar_text,
    register_text_file,
    get_pdf_page_count,
    get_registered_text_file,
)


console = Console()

REPORTLAB_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    REPORTLAB_AVAILABLE = False


def _make_test_pdf(path: Path, page_lines: list[list[str]]):
    """Create a simple multi-page PDF with the given lines per page."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for lines in page_lines:
        y = 700
        for line in lines:
            c.drawString(72, y, line)
            y -= 20
        c.showPage()
    c.save()


def test_sidecar_parsing():
    """Sidecar '=== page N ===' markers split into per-page texts correctly."""
    console.print("\n[cyan]Testing sidecar text parsing...[/cyan]")

    sidecar = (
        "=== page 1 ===\n"
        "GalaxSea Freight Forwarding\n"
        "Place of receipt KODIAK, AK\n"
        "\n\n"
        "=== page 2 ===\n"
        "Invoice Date: 7/20/2026\n"
    )

    pages = parse_sidecar_text(sidecar)
    checks = [
        (len(pages) == 2, f"page count: {len(pages)} (expected 2)"),
        ("KODIAK, AK" in pages[0], "page 1 contains KODIAK, AK"),
        ("Invoice Date" in pages[1], "page 2 contains Invoice Date"),
        ("Invoice Date" not in pages[0], "page 1 excludes page 2 content"),
    ]

    # Gap handling: missing pages become empty strings at the right indices
    gappy = "=== page 2 ===\nsecond\n=== page 5 ===\nfifth\n"
    gap_pages = parse_sidecar_text(gappy)
    checks.append((len(gap_pages) == 5, f"gap: length {len(gap_pages)} (expected 5)"))
    checks.append((gap_pages[0] == "" and gap_pages[1] == "second", "gap: page order honored"))
    checks.append((gap_pages[4] == "fifth", "gap: page 5 at index 4"))

    # No markers at all -> empty list (register_text_file uses this to reject)
    checks.append((parse_sidecar_text("just some text") == [], "no markers -> empty list"))

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_sidecar_registration_and_priority():
    """A registered sidecar becomes the text source, bypassing PDF extraction."""
    console.print("\n[cyan]Testing sidecar registration priority...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "doc.pdf"
        _make_test_pdf(pdf_path, [["PDF TEXT PAGE ONE"], ["PDF TEXT PAGE TWO"]])

        sidecar_path = Path(tmpdir) / "doc_corrected.txt"
        sidecar_path.write_text(
            "=== page 1 ===\nSIDECAR TEXT PAGE ONE\n"
            "=== page 2 ===\nSIDECAR TEXT PAGE TWO\n",
            encoding='utf-8'
        )

        # Before registration: text comes from the PDF itself
        before = get_page_text(pdf_path, 1)
        ok_before = "PDF TEXT PAGE ONE" in before

        clear_text_cache()
        register_text_file(pdf_path, sidecar_path)
        after = get_page_text(pdf_path, 1)
        ok_after = "SIDECAR TEXT PAGE ONE" in after and "PDF TEXT" not in after
        ok_registry = get_registered_text_file(pdf_path) == sidecar_path

        # Missing sidecar and marker-free sidecar must both be rejected
        ok_missing = False
        try:
            register_text_file(pdf_path, Path(tmpdir) / "nope.txt")
        except ValueError:
            ok_missing = True

        bad_sidecar = Path(tmpdir) / "bad.txt"
        bad_sidecar.write_text("no markers here", encoding='utf-8')
        ok_bad = False
        try:
            register_text_file(pdf_path, bad_sidecar)
        except ValueError:
            ok_bad = True

    clear_text_cache()

    checks = [
        (ok_before, "PDF extraction used before registration"),
        (ok_after, "sidecar text used after registration"),
        (ok_registry, "registry reports the sidecar path"),
        (ok_missing, "missing sidecar rejected with ValueError"),
        (ok_bad, "marker-free sidecar rejected with ValueError"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_unified_view_across_subsystems():
    """Page-selection patterns and the scraper extractor see identical text."""
    console.print("\n[cyan]Testing unified view across subsystems...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    from pdf_manipulator.core.page_range.patterns import _extract_all_page_texts
    from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "doc.pdf"
        _make_test_pdf(pdf_path, [
            ["Place of receipt VALDEZ, AK", "Invoice Date: 7/23/2026"],
            ["Place of receipt SITKA, AK"],
        ])

        selection_texts = _extract_all_page_texts(pdf_path, 2)
        extractor = PatternExtractor()
        scraper_texts = [extractor._extract_page_text(pdf_path, n) for n in (1, 2)]

        ok_identical = selection_texts[0] == scraper_texts[0] and \
            selection_texts[1] == scraper_texts[1]
        ok_content = "VALDEZ, AK" in selection_texts[0] and "SITKA, AK" in selection_texts[1]

        # Cache behavior: same object list returned on repeat call
        again = get_page_texts(pdf_path, 2)
        ok_cached = again is get_page_texts(pdf_path, 2)

    clear_text_cache()

    checks = [
        (ok_identical, "selection and scraper texts byte-identical"),
        (ok_content, "expected content present in both"),
        (ok_cached, "repeat calls served from cache"),
    ]

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def test_bounds_and_fallbacks():
    """Out-of-range pages and unreadable files degrade to empty strings."""
    console.print("\n[cyan]Testing bounds and fallbacks...[/cyan]")

    if not REPORTLAB_AVAILABLE:
        console.print("  [yellow]skipped: reportlab not available[/yellow]")
        return True

    clear_text_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "doc.pdf"
        _make_test_pdf(pdf_path, [["ONLY PAGE"]])

        checks = [
            (get_page_text(pdf_path, 0) == "", "page 0 -> empty string"),
            (get_page_text(pdf_path, 99) == "", "page 99 -> empty string"),
            (get_pdf_page_count(pdf_path) == 1, "page count correct"),
            (len(get_page_texts(pdf_path, 5)) == 5, "padding to requested length"),
        ]

        # A non-PDF file must not raise, just yield empties
        junk_path = Path(tmpdir) / "junk.pdf"
        junk_path.write_bytes(b"this is not a pdf")
        clear_text_cache()
        try:
            junk_texts = get_page_texts(junk_path, 2)
            checks.append((junk_texts == ["", ""], "non-PDF -> empty pages, no crash"))
        except Exception as e:
            checks.append((False, f"non-PDF raised: {e}"))

    clear_text_cache()

    passed = 0
    for ok, description in checks:
        marker = "✓" if ok else "[red]✗[/red]"
        console.print(f"  {marker} {description}")
        if ok:
            passed += 1

    return passed == len(checks)


def main():
    """Run all text extraction tests and report the score."""
    console.print("[bold blue]Unified Text Extraction Tests[/bold blue]")

    tests = [
        ("Sidecar Parsing", test_sidecar_parsing),
        ("Sidecar Registration Priority", test_sidecar_registration_and_priority),
        ("Unified View Across Subsystems", test_unified_view_across_subsystems),
        ("Bounds and Fallbacks", test_bounds_and_fallbacks),
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
