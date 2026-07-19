"""
Unified page text extraction for all pdf-manipulator subsystems.
File: pdf_manipulator/core/text_extraction.py

This module is the single source of truth for page text. Both the page-selection
pattern engine (core/page_range/patterns.py) and the scraper/renamer pattern
extractor (scraper/extractors/pattern_extractor.py) read text through here, so a
keyword that selects a page is guaranteed to be visible to a scrape pattern on
that same page. Before this module existed the two subsystems used different
libraries (raw pdfplumber vs pypdf "smart spacing") and could disagree about
the text on the very same page.

Text sources, in priority order:

1. Registered sidecar text file: a per-page text dump with marker lines
   in either style -- "=== page N ===" (smart-pdf-ocr) or "--- PAGE N ---"
   (this tool's own --dump-text). When a sidecar is registered for a PDF,
   its text is used verbatim and no PDF extraction happens at all.
2. Raw pdfplumber extract_text(). Chosen deliberately over the tuned
   PDFPlumberProcessor: character-position line reconstruction keeps lines like
   "Place of receipt VALDEZ, AK" intact, and the adaptive spacing tuning can
   over-correct and insert unwanted spaces/tabs.
3. pypdf extract_text() as a last-resort fallback when pdfplumber is missing
   or fails on a document.

Results are cached per resolved PDF path so multiple patterns against the same
document never re-extract.
"""

import re

from pathlib import Path

from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings

from pypdf import PdfReader

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


# Sidecar page markers. Both known styles are accepted -- smart-pdf-ocr's
# "=== page 1 ===" and this tool's own --dump-text "--- PAGE 1 ---" -- plus
# any 3+ run of = or - as the fences (mixed fences tolerated), so dumped
# text can be hand-corrected and fed straight back in. The marker requires
# the literal word "page" and a number between fences, so it cannot collide
# with extracted content like "City, ST" or "XXX/YYY" port pairs.
SIDECAR_PAGE_MARKER_RGX = re.compile(r'^[=\-]{3,}\s+page\s+(\d+)\s+[=\-]{3,}\s*$', re.IGNORECASE)


# Cache of extracted page texts. Key: resolved PDF path string.
# Value: list of page text strings (0-indexed).
_page_texts_cache = {}

# Registered sidecar text files. Key: resolved PDF path string.
# Value: Path to the sidecar text file.
_sidecar_registry = {}


def _cache_key(pdf_path: Path) -> str:
    """Stable cache key for a PDF file."""
    return str(Path(pdf_path).resolve())


def clear_text_cache():
    """Clear the extraction cache and sidecar registry (useful for testing)."""
    global _page_texts_cache, _sidecar_registry
    _page_texts_cache = {}
    _sidecar_registry = {}


def register_text_file(pdf_path: Path, text_path: Path):
    """
    Register a sidecar text file as the text source for a PDF.

    The sidecar is a per-page text dump using marker lines to separate
    pages. Both "=== page N ===" (smart-pdf-ocr) and "--- PAGE N ---"
    (this tool's --dump-text) styles are accepted, so dumped text can be
    hand-corrected and fed straight back in. Once registered, all
    text-based operations (page selection patterns, scrape patterns, text dumps)
    read from the sidecar instead of extracting from the PDF.

    Args:
        pdf_path: The PDF the sidecar belongs to
        text_path: Path to the sidecar text file

    Raises:
        ValueError: If the text file does not exist or contains no page markers
    """
    text_path = Path(text_path)
    if not text_path.exists():
        raise ValueError(f"Sidecar text file not found: {text_path}")

    pages = parse_sidecar_text(text_path.read_text(encoding='utf-8'))
    if not pages:
        raise ValueError(
            f"Sidecar text file has no page markers: {text_path}\n"
            f"Expected '=== page N ===' (smart-pdf-ocr) or "
            f"'--- PAGE N ---' (--dump-text) marker lines."
        )

    key = _cache_key(pdf_path)
    _sidecar_registry[key] = text_path
    # Pre-populate the cache directly from the parsed sidecar
    _page_texts_cache[key] = pages


def get_registered_text_file(pdf_path: Path):
    """Return the registered sidecar Path for a PDF, or None."""
    return _sidecar_registry.get(_cache_key(pdf_path))


def parse_sidecar_text(text: str) -> list[str]:
    """
    Parse a per-page text dump into per-page texts.

    Pages are delimited by marker lines in either known style
    ("=== page N ===" or "--- PAGE N ---"; any 3+ fence of = or - works). Page numbers in the
    markers are honored: gaps become empty pages, so page 5 of the sidecar is
    always index 4 of the returned list even if pages 2-4 are missing.

    Args:
        text: Full contents of the sidecar file

    Returns:
        List of page texts (0-indexed). Empty list if no markers found.
    """
    page_map = {}
    current_page = None
    current_lines = []

    for line in text.splitlines():
        marker = SIDECAR_PAGE_MARKER_RGX.match(line)
        if marker:
            if current_page is not None:
                page_map[current_page] = '\n'.join(current_lines).strip('\n')
            current_page = int(marker.group(1))
            current_lines = []
        elif current_page is not None:
            current_lines.append(line)

    if current_page is not None:
        page_map[current_page] = '\n'.join(current_lines).strip('\n')

    if not page_map:
        return []

    highest = max(page_map.keys())
    return [page_map.get(page_num, "") for page_num in range(1, highest + 1)]


def get_pdf_page_count(pdf_path: Path) -> int:
    """
    Get the total number of pages in a PDF via pypdf.

    Returns:
        Page count, or 0 if the PDF cannot be read.
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            return len(reader.pages)
    except Exception:
        return 0


def get_page_texts(pdf_path: Path, total_pages: int = None) -> list[str]:
    """
    Get text for all pages of a PDF, from sidecar or extraction, with caching.

    Args:
        pdf_path: Path to the PDF file
        total_pages: Number of pages expected. When None, the PDF's own page
            count is used. The returned list is padded with empty strings if
            the source yields fewer pages than requested.

    Returns:
        List of page text strings (0-indexed), length >= total_pages.
    """
    pdf_path = Path(pdf_path)
    key = _cache_key(pdf_path)

    if total_pages is None:
        total_pages = get_pdf_page_count(pdf_path)

    cached = _page_texts_cache.get(key)
    if cached is not None:
        if len(cached) >= total_pages:
            return cached
        # Cache holds fewer pages than requested (e.g., short sidecar):
        # pad without discarding the cached source text.
        padded = cached + [""] * (total_pages - len(cached))
        _page_texts_cache[key] = padded
        return padded

    texts = _extract_with_pdfplumber(pdf_path, total_pages)
    if texts is None:
        texts = _extract_with_pypdf(pdf_path, total_pages)

    if len(texts) < total_pages:
        texts += [""] * (total_pages - len(texts))

    _page_texts_cache[key] = texts
    return texts


def get_page_text(pdf_path: Path, page_num: int) -> str:
    """
    Get text for a single page (1-indexed).

    Returns:
        Page text, or empty string when the page is out of range or unreadable.
    """
    if page_num < 1:
        return ""

    texts = get_page_texts(pdf_path)
    if page_num > len(texts):
        return ""

    return texts[page_num - 1]


def _extract_with_pdfplumber(pdf_path: Path, total_pages: int):
    """
    Extract all page texts with raw pdfplumber.

    Returns:
        List of page texts, or None when pdfplumber is unavailable or the
        document cannot be opened (caller falls back to pypdf).
    """
    if not PDFPLUMBER_AVAILABLE:
        return None

    try:
        texts = []
        with pdfplumber.open(pdf_path) as pdf:
            page_limit = min(total_pages, len(pdf.pages)) if total_pages else len(pdf.pages)
            for i in range(page_limit):
                try:
                    text = pdf.pages[i].extract_text()
                    texts.append(text if text else "")
                except Exception:
                    texts.append("")
        return texts
    except Exception:
        return None


def _extract_with_pypdf(pdf_path: Path, total_pages: int) -> list[str]:
    """
    Extract all page texts with pypdf (fallback path).

    Returns:
        List of page texts; empty strings for unreadable pages or documents.
    """
    try:
        with suppress_pdf_warnings():
            reader = PdfReader(pdf_path)
            texts = []
            page_limit = min(total_pages, len(reader.pages)) if total_pages else len(reader.pages)
            for i in range(page_limit):
                try:
                    text = reader.pages[i].extract_text()
                    texts.append(text if text else "")
                except Exception:
                    texts.append("")
            return texts
    except Exception:
        return [""] * (total_pages or 0)


# End of file #
