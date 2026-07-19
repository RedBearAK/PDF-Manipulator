# dev_beta session notes — 2026-07-20b (dual sidecar marker styles)

Applies on top of `dev_beta` at `ebb3250`. Tarball extracts into the repo
root: 6 files. All 44 test modules pass after applying.

## Sidecar parser accepts both marker styles

`parse_sidecar_text` now recognizes page markers as any 3+ fence of `=` or
`-` around "page N" (case-insensitive), covering both known producers:

- `=== page N ===`  (smart-pdf-ocr corrected text)
- `--- PAGE N ---`  (this tool's own --dump-text)

Mixed and longer fences are tolerated (hand-edited files), while dashed
CONTENT lines without the "page N" core are never mistaken for markers.
The rejection message, --text-file help text, and tutorial all describe
both styles.

## Round trip unlocked and pinned

The workflow this enables: `--dump-text` a PDF, hand-correct the text,
feed it back with `--text-file` — no marker conversion step. Pinned
end-to-end in test_scraper_modes (dump, edit a value, scrape via sidecar,
assert the corrected value lands in the TSV), plus parser-level cases for
the dump style, mixed fences, and dashed-content false-positive protection
in test_text_extraction.

## To apply

```bash
cd PDF-Manipulator && git checkout dev_beta
tar xzf pdf_manipulator_dev_beta_20260720b.tgz
git add -A
git commit -m "Accept both sidecar marker styles; enable dump/correct/reload round trip"
```

# End of file #
