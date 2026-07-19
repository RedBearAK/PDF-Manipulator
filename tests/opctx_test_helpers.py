"""
Shared OpCtx-aware helpers for test modules.
File: tests/opctx_test_helpers.py

The parse_page_range() and extract_pages() entry points read everything from
OperationContext (OpCtx) rather than their parameters. Test modules that
predate the OpCtx conversion still call them old-style and crash with
"PDF context not initialized". These helpers perform the same setup sequence
the CLI does (reset -> set_args -> set_current_pdf) so tests can drive the
real entry points with one call.

Not a test module itself: no main(), nothing for pytest to collect.
"""

import sys
import argparse

from pathlib import Path

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.operation_context import OpCtx


def make_test_args(**overrides) -> argparse.Namespace:
    """
    Build an argparse.Namespace with the CLI's effective defaults.

    Covers every attribute OpCtx.set_args() and the operations read, so a
    minimal test can override only what it cares about.
    """
    defaults = {
        'extract_pages': None,
        'batch': True,
        'dry_run': False,
        'scrape_pattern': None,
        'scrape_patterns_file': None,
        'filename_template': None,
        'pattern_source_page': 1,
        'dedup': None,
        'respect_groups': False,
        'separate_files': False,
        'conflicts': 'ask',
        'use_timestamp': False,
        'custom_prefix': None,
        'filter_matches': None,
        'group_start': None,
        'group_end': None,
        'text_file': None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def setup_context(range_str: str, total_pages: int, pdf_path=None, **arg_overrides):
    """
    Reset OpCtx and install the context for one parse/extract operation.

    Args:
        range_str: The page range expression under test
        total_pages: Total pages in the (possibly fictional) PDF
        pdf_path: Path to the PDF; a placeholder is used when None, which is
            fine for purely numeric specs that never read the document
        **arg_overrides: Extra argparse attributes (e.g. dedup='none')
    """
    OpCtx.reset()
    OpCtx.set_args(make_test_args(extract_pages=range_str, **arg_overrides))
    path = Path(pdf_path) if pdf_path else Path('test_document.pdf')
    OpCtx.set_current_pdf(path, total_pages)


def parse_with_context(range_str: str, total_pages: int, pdf_path=None, **arg_overrides):
    """
    Parse a page range through the real OpCtx-backed entry point.

    Returns:
        Tuple of (pages set, description, groups) from parse_page_range().
    """
    from pdf_manipulator.core.parser import parse_page_range

    setup_context(range_str, total_pages, pdf_path, **arg_overrides)
    return parse_page_range()


def extract_with_context(pdf_path, range_str: str, total_pages: int = None, **arg_overrides):
    """
    Run extract_pages() through the real OpCtx-backed entry point.

    Args:
        pdf_path: Path to a real PDF on disk
        range_str: Page range expression
        total_pages: Total pages in that PDF; read from the PDF when None
        **arg_overrides: Extra argparse attributes (e.g. conflicts='skip',
            dry_run=True, scrape_pattern=[...], filename_template='...')

    Returns:
        Tuple of (output_path, file_size) from extract_pages().
    """
    from pdf_manipulator.core.operations import extract_pages
    from pdf_manipulator.core.text_extraction import get_pdf_page_count

    if total_pages is None:
        total_pages = get_pdf_page_count(pdf_path)
        if total_pages < 1:
            raise ValueError(f"Could not read page count from {pdf_path}")

    setup_context(range_str, total_pages, pdf_path, **arg_overrides)
    return extract_pages()


# End of file #
