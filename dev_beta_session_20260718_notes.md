# dev_beta session notes — 2026-07-18 (finish-line push, part 1)

Applies on top of `dev_beta` at `d7caf08` ("Fix some pattern bugs in selector").
The tarball extracts into the repo root; every file is either new or a full
replacement of the file at that path. No deletions are required for this
changeset to work.

## Branch question answered

`old_dev_beta` is "8 commits behind main" only because those 8 commits are the
merge commits of its own PRs (#1-#7) back into main, plus `d7caf08` which was
committed directly to main. Nothing on the old branch was unmerged; the new
`dev_beta` started identical to main's tip. No work was lost.

## What changed

### B. Unified text extraction (the two-truths fix)

New `pdf_manipulator/core/text_extraction.py`: the single source of page text
for the whole tool. Priority: registered sidecar text file -> raw pdfplumber ->
pypdf fallback, cached per resolved path. Verified against the sample PDFs that
pypdf and raw pdfplumber genuinely reconstruct the smart-OCR text layer
differently ("Date:7/23/2026" vs "Date: 7/23/2026", merged vs split lines),
which is why the page selector and the scraper used to disagree.

- `core/page_range/patterns.py`: `_extract_all_page_texts` and
  `_clear_extraction_cache` now delegate to the provider (public behavior
  unchanged; local cache removed).
- `scraper/extractors/pattern_extractor.py`: `_extract_page_text` and
  `_get_pdf_page_count` delegate to the provider; the private `PyPDFProcessor`
  instance is gone. Scrape patterns now see exactly the text page-selection
  patterns see.
- New CLI flag `--text-file FILE` (single-PDF mode only): registers a
  smart-pdf-ocr corrected text dump ("=== page N ===" markers) as the text
  source for page selection, scrape patterns, and `--dump-text`. Missing files
  and marker-free files are rejected at startup.

### C. Standalone scraper modes implemented

`handle_scraper_operations` in `cli.py` was a stub ("not yet implemented in
Phase 1") while the epilog advertised the modes. Now real:

- `--dump-text` [--output FILE]: page-by-page text via the unified provider,
  `--- PAGE N ---` format, notes the sidecar when one is registered.
- `--scrape-text`: Phase 4 compact patterns -> TSV via the existing TSVWriter
  (`filename` column + one column per variable, in pattern order; default
  output `extracted_data.tsv`). Works on a single PDF or a folder of PDFs.
  Pattern syntax is validated before any PDF is opened.

### D. Phase 4 landed with `%` end trimmers

`$` -> `%` throughout: `renamer_regex_patterns.py` (COMPACT_PATTERN_RGX,
STRAY_END_TRIMMER_RGX), `pattern_processor.py` (parsing, error messages,
docstrings, examples), the CLI epilog (now documents full Phase 4 syntax
including trimming, flags, and the sidecar), and the Phase 4 test modules.
No deprecation shim: `$` is simply no longer valid, per decision.

### Renamer chain repaired (three latent breaks)

The smart-rename path could never have run; it failed at three different
seams, silently caught by fallback naming:

1. `FilenameGenerator` called `PatternProcessor.extract_from_pdf(...)` which
   did not exist. Added: builds the enhanced pattern, resolves the page spec
   (pattern `pg` spec, else `source_page`), runs extraction, then applies
   Phase 4 post-processing (space-exclusion flag, `^`/`%` trimmers) to the
   selected match (lists from `mt` ranges handled item-wise). Trimming
   failures downgrade to warnings, never crashes.
2. `FilenameGenerator` unpacked `validate_pattern_list()` results as 3-tuples;
   they are dicts. All three sites now consume dicts.
3. `FilenameGenerator` called `TemplateEngine.apply_template()` which did not
   exist; routed to `substitute_variables()`.

Also: `process_pdf_with_patterns` called nonexistent
`PyPDFProcessor.extract_text_simple`; rewritten on the unified provider and it
now backs `--scrape-text`. Added `convert_to_enhanced_pattern()` and a
top-level `'flexible'` compat key in parsed specs (Phase 2/3 API expectations).

### operations.py: smart naming wired in + two positional-arg bugs

- `extract_pages` previously ignored `patterns`/`template` entirely ("no
  renamer complexity"). It now uses `FilenameGenerator.generate_smart_filename`
  when both are supplied, with visible fallback warnings; grouped/separate
  extraction keeps simple naming for now (per-file smart naming is a follow-up).
- Two call sites passed `generate_extraction_filename(pdf, desc, use_timestamp,
  custom_prefix)` positionally, so `use_timestamp` landed in `extraction_mode`
  and `custom_prefix` in `timestamp` — `--timestamp` silently did nothing on
  those paths. Fixed with explicit mode arguments ('single', 'separate').

### Extractor movement semantics (bugs exposed by test_phase2_integration)

- `extract_pattern` routed any dict with a `'keyword'` to the enhanced branch,
  so legacy `direction`/`distance` patterns crashed on missing
  `'extract_count'`. Routing now keys on `'movements'`; the legacy branch
  accepts both `direction`/`distance` and older `movement_*` key names.
- u/d movements now skip empty lines (blank lines in OCR text are layout
  noise, not content the pattern author counts); previously `d2` across a
  blank line could land on the blank and `r1` then produced word index -1 and
  an IndexError.
- Zero movements now means "content right after the keyword" (position
  keyword+1), matching the old scraper's `right:0` semantics; previously it
  extracted the keyword itself, which nobody wants.
- Explicit `r` movements still clamp to the last word of the line (the
  forgiving `d25r10`-style overshoot behavior is preserved).

### Sanitizer: real-world bug found by the sample PDFs

`sanitize_filename('7/23/2026')` returned it unchanged: the "monetary amount"
branch used `re.match`, which anchored only at the start, so the date's leading
digit sent it down the currency path that never strips `/`. The slashes reached
`open()` as directory separators -> `FileNotFoundError`. Fixed with
`re.fullmatch` plus an unconditional unsafe-character scrub after both branches
(no unsafe character may survive the function, whichever branch ran). Regression
pinned in `tests/test_scraper_modes.py`.

### Cleanup in touched files

`scraper/extractors/trimming.py`: `typing` module removed (natural
`list[tuple[str, int]]` annotations). Version bumped to `20260718.0`. README
gains sections for the unified provider/sidecar, `%` trimming, and the
standalone scraper modes.

## Test status

New modules (house style: standalone, boolean returns, accumulated score,
pytest-compatible):

- `tests/test_text_extraction.py` — 4/4: sidecar parsing (markers, gaps,
  rejection), sidecar priority over PDF extraction, byte-identical text across
  page-selection and scraper subsystems, bounds/fallbacks (junk file -> empty
  pages, no crash).
- `tests/test_scraper_modes.py` — 4/4, end-to-end through subprocess CLI:
  `--dump-text` (stdout + file), `--scrape-text` with `%` trimming/`nb`/`pg`
  specs into TSV, `--text-file` sidecar (including folder rejection), and
  `--extract-pages` + patterns + template smart renaming with the slash
  regression pinned.

Updated and passing: `test_phase2_integration.py` 5/5 (was 1/5 at baseline),
`test_phase3_patterns.py` 100% (was 85.7%), `test_phase4_patterns.py`,
`test_phase4_fixed.py`, `test_phase4_trimming.py` all pass on `%`,
`test_phase3_cli_integration.py`, `test_file_selector_loader.py` 4/4,
`test_operation_context.py` pass unchanged.

Pre-existing failures, identical on unmodified `d7caf08` (verified via a git
worktree; NOT regressions, left for the cleanup phase):
`test_advanced_page_selection`, `test_architecture_fixes`,
`test_basic_page_ranges`, `test_comprehensive_conflict_integration`,
`test_conflict_resolution_integration`, `test_file_selector` (includes the
known `5:10:2` slicing loader/parser mismatch), `test_numeric_reordering`,
`test_page_features`, `test_pattern_matching`, `test_range_patterns`,
`test_reverse_ranges`, `test_simple_boolean`, `test_smart_filename_patterns`.

## Real-world validation (project sample PDFs)

- Originals confirmed image-only (no text layer at all); smart-OCR'd
  companions read cleanly.
- 84-page `20260703151503_smartocr.pdf`: OCR-artifact regex
  `regex/i:'K\s*O\s*D\s*I\s*A\s*K'` selected 25 pages;
  `--scrape-text` returned invoice `27597`, date `7/20/2026`,
  receipt `KODIAK, AK`.
- 35-page `20260716144334_smartocr.pdf`: full chain
  `--extract-pages=1 --scrape-pattern="inv=No:wd1"
  --scrape-pattern="date=Invoice Date:wd1_"
  --filename-template="INV{inv}_{date}.pdf"` produced
  `INV27679_7-23-2026.pdf` (after the sanitizer fix that this exact run
  uncovered).

## To apply

```bash
cd PDF-Manipulator
git checkout dev_beta
tar xzf pdf_manipulator_dev_beta_20260718.tgz
git add -A
git commit -m "Unified text extraction, % trimmers, scraper modes, renamer repair"
```

## Deferred (cleanup phase, needs deletions a tarball cannot do)

```bash
# Duplicate legacy tree and its test copies (fully superseded by
# pdf_manipulator/scraper/; only tests/debug_text_extraction.py still imports
# it, and only as an optional comparison path):
git rm -r simple_pdf_scraper simple_pdf_scraper_tests tests/scraper_tests
# Leftover working copies:
git rm "pdf_manipulator/core/parser copy.py" pdf_manipulator/core/DEPRECATED__advanced_page_selection.py
```

Also deferred: the 13 pre-existing test failures above; per-file smart naming
for grouped/separate extraction; the `5:10:2` slicing decision (implement in
PageRangeParser or reject at load time); `extract_pages` docstrings still
describing the discarded parameters of the OpCtx shim.

# End of file #
