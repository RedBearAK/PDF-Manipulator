#!/usr/bin/env python3
"""
Loader defect regression tests for the file selector.
File: tests/test_file_selector_loader.py

Covers the three loader defects observed 2026-07-18:
1. Trailing inline comments on spec lines must be stripped (quote-aware).
2. Regex specs must pass through the loader byte-for-byte (no '*' loss).
3. Echoing specs through rich must never raise MarkupError on [/...] classes.

Runnable standalone or with pytest. Each test prints what it checked,
returns True/False, and main() accumulates the final score.
"""

import io
import sys
import tempfile

from pathlib import Path
from rich.console import Console

# Make project root importable when run directly from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_manipulator.core.page_range.file_selector import FileSelector


KOD_DAL_SPEC = r"regex/i:'K\s*O\s*D\s*[1lI|\\/]\s*D\s*A\s*L'"
SLASH_CLASS_SPEC = r"regex/i:'K\s*O\s*D\s*[/1lI|\\]\s*D\s*A\s*L'"
LOWER_CLASS_SPEC = r"regex/i:'A\s*N\s*C\s*[l1I|\\/]\s*S\s*E\s*A'"


def _load_specs(file_text: str) -> list:
    """Write file_text to a temp patterns file and load it through FileSelector."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        patterns_path = Path(tmp_dir) / "patterns.txt"
        patterns_path.write_text(file_text, encoding='utf-8')
        selector = FileSelector(base_path=Path(tmp_dir))
        return selector.parse_file_selector("file:patterns.txt")


def test_inline_comment_stripped():
    """Trailing comments after a quoted pattern must not reach the parser."""
    print("=== Inline comment stripping ===")
    specs = _load_specs(
        "# full-line comment\n"
        f"{KOD_DAL_SPEC}        # KOD/DAL  Kodiak -> Dalian\n"
    )
    ok = specs == [KOD_DAL_SPEC]
    print(f"{'✓' if ok else '✗'} loaded spec: {specs[0] if specs else '(none)'}")
    if not ok:
        print(f"  expected: {KOD_DAL_SPEC}")
    return ok


def test_hash_inside_quotes_preserved():
    """A '#' inside a quoted pattern value is pattern content, not a comment."""
    print("=== '#' inside quotes preserved ===")
    spec = "contains:'Invoice #42'"
    specs = _load_specs(f"{spec}   # find the invoice page\n")
    ok = specs == [spec]
    print(f"{'✓' if ok else '✗'} loaded spec: {specs[0] if specs else '(none)'}")
    return ok


def test_specs_load_verbatim():
    """Regex metacharacters like '\\s*[' must survive loading byte-for-byte."""
    print("=== Verbatim pass-through (no '*' loss before '[') ===")
    specs = _load_specs(f"{KOD_DAL_SPEC}\n{LOWER_CLASS_SPEC}\n")
    ok = specs == [KOD_DAL_SPEC, LOWER_CLASS_SPEC]
    for spec in specs:
        print(f"{'✓' if ok else '✗'} {spec}")
    return ok


def test_expansion_echo_survives_rich_markup():
    """Echoing specs with [/...] classes must not raise rich MarkupError."""
    print("=== Expansion echo with markup-hostile specs ===")
    import pdf_manipulator.core.page_range.file_selector as fs_module

    with tempfile.TemporaryDirectory() as tmp_dir:
        patterns_path = Path(tmp_dir) / "patterns.txt"
        patterns_path.write_text(
            f"{SLASH_CLASS_SPEC}\n{LOWER_CLASS_SPEC}\n", encoding='utf-8')
        selector = FileSelector(base_path=Path(tmp_dir))

        # Capture console output so we can verify the echo is verbatim
        capture = io.StringIO()
        saved_console = fs_module.console
        fs_module.console = Console(file=capture, force_terminal=False, width=500)
        try:
            expanded = selector.expand_file_selectors("file:patterns.txt")
        except Exception as e:
            print(f"✗ expansion raised {type(e).__name__}: {e}")
            return False
        finally:
            fs_module.console = saved_console

    echoed = capture.getvalue()
    ok = True
    for spec in [SLASH_CLASS_SPEC, LOWER_CLASS_SPEC]:
        if spec not in expanded:
            print(f"✗ expanded string mangled spec: {spec}")
            ok = False
        if spec not in echoed:
            print(f"✗ echo did not show spec verbatim: {spec}")
            ok = False
    if ok:
        print("✓ no MarkupError; expansion and echo both verbatim")
    return ok


def main():
    tests = [
        test_inline_comment_stripped,
        test_hash_inside_quotes_preserved,
        test_specs_load_verbatim,
        test_expansion_echo_survives_rich_markup,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Score: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)

# End of file #
