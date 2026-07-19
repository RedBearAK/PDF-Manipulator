# dev_beta session notes — 2026-07-19b (per-file smart naming, old CLI retired)

Applies on top of `dev_beta` at `54dc5b8`. Tarball extracts into the repo
root: 5 files. All 43 test modules pass after applying.

## Per-file smart naming (separate and grouped modes)

Patterns + `--filename-template` now drive output names in ALL THREE
extraction modes, with one deliberate semantic per mode:

- **Separate** (`--separate-files`): `source_page` is THE PAGE BEING
  EXTRACTED, so patterns without pg specs read each page's own content —
  every invoice page names itself. Patterns WITH explicit pg specs stay
  document-level (e.g. a shared batch code from page 1 appears in every
  filename).
- **Grouped** (`--respect-groups`): `source_page` is each group's FIRST page
  (in the group's own order).
- **Single** (unchanged behavior, now routed through the same helper).

Duplicate extracted values resolve to unique names via the existing conflict
machinery (`INV-DUP.pdf`, `INV-DUP_copy_01.pdf` under conflicts='rename').

**Dry runs now preview REAL extracted names.** Pattern extraction is
read-only, so the naming helper always performs actual extraction; dry runs
show "Would create: GXY27597_KODIAK-AK.pdf" instead of PREVIEW_* placeholders.
This applies to all three modes, including plain `--extract-pages` (behavior
change from the previous PREVIEW_* dry-run output).

Real-world validation on the 84-page smart-OCR'd sample:

    pdf-manipulator 20260703151503_smartocr.pdf --extract-pages=1-5 \
        --separate-files --batch \
        --scrape-pattern="inv=No:wd1" \
        --scrape-pattern="city=Place of receipt:wd2_" \
        --filename-template="GXY{inv}_{city}.pdf"

    -> GXY27597_KODIAK-AK.pdf, GXY27594_KODIAK-AK.pdf,
       GXY27586_SEWARD-AK.pdf, GXY27606_KODIAK-AK.pdf, GXY27605_KODIAK-AK.pdf

(The `_` flag excludes spaces, so "KODIAK, AK" sanitizes to "KODIAK-AK".)

## Old standalone scraper CLI retired

`pdf_manipulator/scraper/__main__.py` is now a redirect stub: running
`python -m pdf_manipulator.scraper` prints the merged-CLI equivalents
(Phase 4 syntax) and exits 1. Nothing imports `scraper/cli.py` anymore;
delete it after extracting:

```bash
git rm pdf_manipulator/scraper/cli.py
```

## New test module

`tests/test_per_file_smart_naming.py` (4/4): separate-mode per-page naming,
grouped-mode first-page naming, document-level pg1 spec shared across
outputs while per-page values differ, duplicate-value uniqueness, and
dry-run output containing real names and no PREVIEW placeholders.

## To apply

```bash
cd PDF-Manipulator && git checkout dev_beta
tar xzf pdf_manipulator_dev_beta_20260719b.tgz
git rm pdf_manipulator/scraper/cli.py
git add -A
git commit -m "Per-file smart naming for separate/grouped modes; retire old scraper CLI"
```

# End of file #
