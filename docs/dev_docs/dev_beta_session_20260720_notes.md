# dev_beta session notes — 2026-07-20 (TUTORIAL.md)

Applies on top of `dev_beta` at `0069742`. Docs only: 3 files (TUTORIAL.md,
README.md link, this notes file). No code changes; no version bump.

## TUTORIAL.md

A ~950-line guided tour, simple to advanced, all Markdown, with a linked
table of contents at the top and a per-section navigation line (back to
contents + that section's subsections) at the head of every section:

 1. Getting Started (assessment, first extraction, dry-run + batch habits)
 2. Selecting Pages by Number (ranges, reverse, open-ended, first/last,
    slicing, comma order preservation)
 3. Selecting Pages by Content (contains/regex/line-starts, /i, type, size,
    validation behavior)
 4. Boolean Logic (operators, strict spacing, parentheses, numeric
    operands / page windows)
 5. Range Patterns (pattern/number/start/end endpoints, offsets,
    all-sections behavior)
 6. Output Modes and Groups (three modes, dedup strategies, filter-matches,
    boundary detection)
 7. Pattern Files (file: selector, writing PATTERNS.txt)
 8. Scraping Text Data (dump-text, full compact-pattern anatomy: movements,
    types, flags, ^/% trimming, pg/mt, TSV output)
 9. Smart Renaming (template variables, per-page and per-group naming,
    document-level pg specs, sanitization, dry-run real names)
10. Working with Scanned Documents (sandwich PDFs, OCR-artifact regex,
    sidecar text files)
11. Repair and Optimization (brief)
12. Recipes (invoice batch split, TSV audit, chapter extraction,
    destination routing)
13. Quick Reference (three cheat-sheet tables)

## Machine-validated, same as the README pass

- All 82 internal anchor links resolve against GitHub-style slugs (0 broken)
- 64 `--extract-pages` examples parse AND evaluate against the real 84-page
  sample; 11 more fail only because their illustrative content (chapters
  etc.) isn't in an invoice document; 0 syntax failures
- All 30 `--scrape-pattern` examples parse through PatternProcessor
- All 6 `--filename-template` examples pass template validation

## To apply

```bash
cd PDF-Manipulator && git checkout dev_beta
tar xzf pdf_manipulator_dev_beta_20260720.tgz
git add -A
git commit -m "Add step-by-step tutorial with navigable TOC"
```

# End of file #
