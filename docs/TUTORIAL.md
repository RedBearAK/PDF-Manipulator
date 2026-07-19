# PDF Manipulator Tutorial

A guided tour from your first extraction to content-driven batch workflows.
Every command here is runnable as shown; start at the top or jump straight
to the part you need.

<a id="contents"></a>
## Contents

1. [Getting Started](#1-getting-started)
2. [Selecting Pages by Number](#2-selecting-pages-by-number)
3. [Selecting Pages by Content](#3-selecting-pages-by-content)
4. [Combining Criteria with Boolean Logic](#4-combining-criteria-with-boolean-logic)
5. [Extracting Sections with Range Patterns](#5-extracting-sections-with-range-patterns)
6. [Output Modes and Groups](#6-output-modes-and-groups)
7. [Pattern Files](#7-pattern-files)
8. [Scraping Text Data](#8-scraping-text-data)
9. [Smart Renaming](#9-smart-renaming)
10. [Working with Scanned Documents](#10-working-with-scanned-documents)
11. [Repair and Optimization](#11-repair-and-optimization)
12. [Recipes](#12-recipes)
13. [Quick Reference](#13-quick-reference)

---

## 1. Getting Started

> [◂ Contents](#contents) ·
> [Your first look at a PDF](#your-first-look-at-a-pdf) ·
> [Your first extraction](#your-first-extraction) ·
> [Two habits to build early](#two-habits-to-build-early)

### Your first look at a PDF

Point the tool at a file with no operation and it assesses the document:

```bash
pdf-manipulator report.pdf
```

You get a table of page count, file size, and status (including whether the
PDF looks malformed). Point it at a folder and every PDF inside is assessed.
For a page-by-page breakdown:

```bash
pdf-manipulator report.pdf --analyze-detailed
```

### Your first extraction

```bash
pdf-manipulator report.pdf --extract-pages=3-7
```

This creates `report_extracted_Pages_3-7.pdf` next to the original. The
original file is never modified by extraction; you always get a new file.

### Two habits to build early

**Habit one: `--dry-run`.** Every extraction command accepts it, and it shows
exactly what would be created — including, later on, the actual content-based
filenames — without writing anything:

```bash
pdf-manipulator report.pdf --extract-pages=3-7 --dry-run
```

**Habit two: know your mode.** By default the tool is interactive and will
prompt you (for example, how to handle a filename that already exists). Add
`--batch` for unattended runs; prompts are replaced with safe defaults, such
as auto-renaming instead of asking about conflicts:

```bash
pdf-manipulator invoices/ --extract-pages=1 --batch
```

**Quoting:** wrap any page selection containing spaces, quotes, or special
characters in double quotes: `--extract-pages="contains:'Invoice'"`. The
examples below quote whenever it matters.

---

## 2. Selecting Pages by Number

> [◂ Contents](#contents) ·
> [Single pages and ranges](#single-pages-and-ranges) ·
> [Reverse ranges](#reverse-ranges) ·
> [Open-ended ranges](#open-ended-ranges) ·
> [First, last, and friends](#first-last-and-friends) ·
> [Slicing](#slicing) ·
> [Combining specs with commas](#combining-specs-with-commas)

### Single pages and ranges

```bash
pdf-manipulator doc.pdf --extract-pages=5          # just page 5
pdf-manipulator doc.pdf --extract-pages=3-7        # pages 3 through 7
pdf-manipulator doc.pdf --extract-pages=3:7        # same thing
pdf-manipulator doc.pdf --extract-pages=3..7       # also the same thing
```

All three range spellings are equivalent; use whichever reads best to you.

### Reverse ranges

Write the range backwards and the pages come out backwards:

```bash
pdf-manipulator doc.pdf --extract-pages=10-7       # pages 10, 9, 8, 7 in that order
pdf-manipulator doc.pdf --extract-pages=50-1       # the whole document, reversed
```

The output PDF's page order matches — useful for documents scanned in
reverse.

### Open-ended ranges

Leave off one side to run to the document boundary:

```bash
pdf-manipulator doc.pdf --extract-pages=3-         # page 3 to the end
pdf-manipulator doc.pdf --extract-pages=-7         # start through page 7
```

### First, last, and friends

```bash
pdf-manipulator doc.pdf --extract-pages="first 3"  # first 3 pages
pdf-manipulator doc.pdf --extract-pages=first-3    # same, no quotes needed
pdf-manipulator doc.pdf --extract-pages="last 2"   # last 2 pages
pdf-manipulator doc.pdf --extract-pages=last-2     # same
pdf-manipulator doc.pdf --extract-pages=all        # every page
pdf-manipulator doc.pdf --extract-pages=odd        # 1, 3, 5, ...
pdf-manipulator doc.pdf --extract-pages=even       # 2, 4, 6, ...
```

### Slicing

Python-style `start:stop:step`, adapted for pages: **1-indexed, and the stop
is included**. Any part can be omitted.

```bash
pdf-manipulator doc.pdf --extract-pages=::2        # every 2nd page from 1 -> 1, 3, 5...
pdf-manipulator doc.pdf --extract-pages=2::2       # every 2nd page from 2 -> 2, 4, 6...
pdf-manipulator doc.pdf --extract-pages=5:10:2     # from 5 through 10 -> 5, 7, 9
pdf-manipulator doc.pdf --extract-pages=:10:3      # from 1 through 10 -> 1, 4, 7, 10
pdf-manipulator doc.pdf --extract-pages=3:         # page 3 to the end
```

Mistakes fail loudly: a backwards slice (`10:5`), a zero step (`5:10:0`),
or a start beyond the document all produce clear error messages rather than
silently selecting nothing.

### Combining specs with commas

Comma-separate any mix of the above:

```bash
pdf-manipulator doc.pdf --extract-pages="1-3,7,9-11"
```

**Order is preserved whenever it carries meaning.** If you write numbers out
of order, use reverse ranges, or mix in first/last or content patterns, the
output keeps your order:

```bash
pdf-manipulator doc.pdf --extract-pages="10,5,1"        # pages come out 10, 5, 1
pdf-manipulator doc.pdf --extract-pages="last 2,first 3" # end pages first, then the start
```

A plain ascending list (`"1,5,10"`) is simply sorted. Duplicate pages across
specs are removed by default; see [Output Modes and Groups](#6-output-modes-and-groups)
for the deduplication strategies.

---

## 3. Selecting Pages by Content

> [◂ Contents](#contents) ·
> [Text search with contains](#text-search-with-contains) ·
> [Regular expressions](#regular-expressions) ·
> [Line starts](#line-starts) ·
> [Page type](#page-type) ·
> [Page size](#page-size)

Content patterns select pages by what is *on* them rather than where they
are. This is where the tool starts earning its keep.

### Text search with contains

```bash
pdf-manipulator doc.pdf --extract-pages="contains:'Invoice'"
pdf-manipulator doc.pdf --extract-pages="contains/i:'invoice'"   # case-insensitive
```

Quote the search text with single quotes inside the double-quoted argument.
Anything inside those quotes is literal — spaces, ampersands, even the word
`to` — and will never be mistaken for operator syntax.

### Regular expressions

```bash
pdf-manipulator doc.pdf --extract-pages="regex:'INV-\d+'"
pdf-manipulator doc.pdf --extract-pages="regex/i:'chapter \d+'"
```

The `/i` suffix works on every text pattern type. Regex becomes essential
for OCR'd documents, where recognized text has unreliable spacing — see
[Working with Scanned Documents](#10-working-with-scanned-documents).

### Line starts

Match only at the beginning of a line — good for headings:

```bash
pdf-manipulator doc.pdf --extract-pages="line-starts:'Summary'"
pdf-manipulator doc.pdf --extract-pages="line-starts/i:'appendix'"
```

### Page type

Every page classifies as one of four types:

```bash
pdf-manipulator doc.pdf --extract-pages=type:text    # text-heavy pages
pdf-manipulator doc.pdf --extract-pages=type:image   # scanned/image pages
pdf-manipulator doc.pdf --extract-pages=type:mixed   # both text and images
pdf-manipulator doc.pdf --extract-pages=type:empty   # blank or near-blank
```

Any other value (`type:invalid`) is rejected immediately with the list of
valid types — it will never silently match nothing.

> **Scanned-document note:** pages from OCR'd "sandwich" PDFs contain both
> the scan image and an invisible text layer, so they classify as
> `type:mixed`, not `type:text`.

### Page size

Compare against each page's contribution to file size:

```bash
pdf-manipulator doc.pdf --extract-pages="size:>1MB"
pdf-manipulator doc.pdf --extract-pages="size:<500KB"
pdf-manipulator doc.pdf --extract-pages="size:>=2MB"
pdf-manipulator doc.pdf --extract-pages="size:<=100KB"
```

Units are `B`, `KB`, `MB`, `GB` (bare numbers mean bytes). A malformed
condition (`size:huge`) is rejected with examples of the accepted forms.

---
## 4. Combining Criteria with Boolean Logic

> [◂ Contents](#contents) ·
> [The three operators](#the-three-operators) ·
> [Spacing rules](#spacing-rules) ·
> [Parentheses](#parentheses) ·
> [Page windows: numeric operands](#page-windows-numeric-operands)

### The three operators

```bash
# AND: both must match
pdf-manipulator doc.pdf --extract-pages="type:text & contains:'Important'"

# OR: either matches
pdf-manipulator doc.pdf --extract-pages="type:image | size:>2MB"

# NOT: exclude matches
pdf-manipulator doc.pdf --extract-pages="all & !contains:'DRAFT'"
pdf-manipulator doc.pdf --extract-pages="!type:empty"
```

Precedence is parentheses, then NOT, then AND, then OR — the usual order.
The keywords `all`, `odd`, and `even` work as operands, which is why
`all & !X` is the idiomatic "everything except X".

### Spacing rules

Operator spacing is deliberately strict: `&` and `|` count as operators only
with **exactly one space on each side**. Anything else — `a& b`, `a &b`,
`a  &  b`, a trailing `type:text |` — raises a clear error instead of being
quietly misread as a content pattern that never matches.

Inside quotes you are always free: `contains:'A & B'` searches for the
literal text `A & B`.

### Parentheses

Group logic explicitly when mixing operators:

```bash
pdf-manipulator doc.pdf --extract-pages="(type:text | type:mixed) & !contains:'DRAFT'"
pdf-manipulator doc.pdf --extract-pages="!(type:empty | size:<10KB)"
```

Unbalanced parentheses are reported as such.

### Page windows: numeric operands

Anything from [Selecting Pages by Number](#2-selecting-pages-by-number) —
single pages, ranges, slices, first/last — is a valid boolean operand. That
turns boolean logic into a way of confining content searches to part of a
document:

```bash
# Only within pages 5-15 (every 2nd), which pages mention KODIAK?
pdf-manipulator doc.pdf --extract-pages="5:15:2 & regex/i:'K\s*O\s*D'"

# Mixed-content pages among the first ten
pdf-manipulator doc.pdf --extract-pages="first-10 & type:mixed"

# Everything except pages 4-7
pdf-manipulator doc.pdf --extract-pages="all & !4-7"

# Two windows joined
pdf-manipulator doc.pdf --extract-pages="3-5 | 8-9"
```

---

## 5. Extracting Sections with Range Patterns

> [◂ Contents](#contents) ·
> [From one pattern to another](#from-one-pattern-to-another) ·
> [Mixing endpoint types](#mixing-endpoint-types) ·
> [Offsets](#offsets) ·
> [Every matching section](#every-matching-section)

Range patterns select runs of consecutive pages between two markers, using
` to ` as the separator.

### From one pattern to another

```bash
pdf-manipulator book.pdf --extract-pages="contains:'Chapter 1' to contains:'Chapter 2'"
```

The separator is matched in any case (`to`, `TO`, `To`), and quoted text
never triggers it: `contains:'A to B'` is an ordinary text search.

### Mixing endpoint types

Each side can independently be a content pattern, a plain page number, or
the boundary keywords `start` and `end`:

```bash
pdf-manipulator doc.pdf --extract-pages="5 to contains:'Appendix'"
pdf-manipulator doc.pdf --extract-pages="contains:'Introduction' to 20"
pdf-manipulator doc.pdf --extract-pages="contains:'Appendix' to end"
pdf-manipulator doc.pdf --extract-pages="start to contains:'Chapter 2'"
pdf-manipulator doc.pdf --extract-pages="2 to 5"
```

### Offsets

Nudge a pattern endpoint with `+N` or `-N` pages — for example, to skip the
heading page itself, or stop just before the closing marker:

```bash
pdf-manipulator doc.pdf --extract-pages="contains:'Section'+1 to contains:'References'-1"
```

### Every matching section

A range pattern finds **all** start→end sections, not just the first. In a
document with five chapters, `"contains:'Chapter' to contains:'Summary'"`
yields five sections, and each becomes its own group — which matters in the
next section.

---

## 6. Output Modes and Groups

> [◂ Contents](#contents) ·
> [Three ways to write output](#three-ways-to-write-output) ·
> [Deduplication strategies](#deduplication-strategies) ·
> [Filtering groups](#filtering-groups) ·
> [Boundary detection](#boundary-detection)

### Three ways to write output

```bash
# Default: one combined document
pdf-manipulator doc.pdf --extract-pages="1-5,10"

# One file per page
pdf-manipulator doc.pdf --extract-pages="1-5,10" --separate-files

# Respect groupings: each comma-separated spec (or matched section)
# becomes its own file; ranges stay multi-page
pdf-manipulator doc.pdf --extract-pages="1-3,7,9-11" --respect-groups
```

In interactive mode (no `--batch`), a multi-group selection shows the
detected groups — each labeled with the spec or pattern that produced it —
and asks which mode you want.

### Deduplication strategies

When specs overlap, `--dedup` controls what happens to repeated pages:

```bash
--dedup=strict     # default: each page appears once overall
--dedup=groups     # unique within each group; groups may share pages
--dedup=none       # keep every occurrence, in order
--dedup=warn       # like strict, but reports what was removed
--dedup=fail       # refuse to proceed if duplicates exist
```

### Filtering groups

After selection produces groups, keep only some of them:

```bash
# By index: keep the 1st, 3rd, and 4th matched sections
pdf-manipulator doc.pdf --extract-pages="contains:'Chapter' to contains:'Summary'" \
    --filter-matches="1,3,4" --respect-groups

# By content: keep only groups whose pages match further criteria
pdf-manipulator doc.pdf --extract-pages="contains:'Article' to contains:'End'" \
    --filter-matches="contains:'Feature'" --respect-groups
```

### Boundary detection

Split a flat selection into groups at marker pages:

```bash
# Start a new group at every chapter heading
pdf-manipulator doc.pdf --extract-pages=type:text \
    --group-start="contains:'Chapter'" --respect-groups

# Close groups at summary pages too
pdf-manipulator doc.pdf --extract-pages=all \
    --group-start="contains:'Chapter'" --group-end="contains:'Summary'" \
    --respect-groups
```

---

## 7. Pattern Files

> [◂ Contents](#contents) ·
> [The file selector](#the-file-selector) ·
> [Writing a patterns file](#writing-a-patterns-file)

### The file selector

When a selection grows past a couple of criteria, move it into a file and
reference it with `file:`:

```bash
pdf-manipulator scans.pdf --extract-pages="file:PATTERNS.txt" --respect-groups
```

Each line of the file is one spec — any syntax from this tutorial. Groups
appear in the file's line order, so with `--respect-groups` you get one
output file per line, in a predictable sequence.

You can also mix file selectors with inline specs:

```bash
pdf-manipulator scans.pdf --extract-pages="1-3,file:PATTERNS.txt"
```

### Writing a patterns file

```text
# PATTERNS.txt - lines starting with # are comments, blank lines ignored
regex/i:'K\s*O\s*D\s*I\s*A\s*K'
regex/i:'S\s*E\s*W\s*A\s*R\s*D'
contains:'HOMER'
5:10:2
last 2
```

---

## 8. Scraping Text Data

> [◂ Contents](#contents) ·
> [Dumping raw text](#dumping-raw-text) ·
> [Your first scrape pattern](#your-first-scrape-pattern) ·
> [Anatomy of a compact pattern](#anatomy-of-a-compact-pattern) ·
> [Movements](#movements) ·
> [Extraction types and counts](#extraction-types-and-counts) ·
> [Flags](#flags) ·
> [Trimming](#trimming) ·
> [Page and match selection](#page-and-match-selection) ·
> [Scraping to TSV](#scraping-to-tsv)

Beyond extracting pages, the tool extracts *data*: pull an invoice number, a
date, a total out of every PDF into a spreadsheet-ready TSV.

### Dumping raw text

Before writing patterns, look at what the tool actually sees — patterns
match against this text, not against the PDF's visual layout:

```bash
pdf-manipulator invoice.pdf --dump-text                    # to the terminal
pdf-manipulator invoice.pdf --dump-text --output raw.txt   # to a file
```

Pages are separated by `--- PAGE N ---` markers.

### Your first scrape pattern

Suppose page text contains the line `Invoice Number: INV-2024-001`. This
pattern extracts the number:

```bash
pdf-manipulator invoice.pdf --scrape-text \
    --scrape-pattern="invoice=Invoice Number:wd1" \
    --output data.tsv
```

Read it as: find the keyword `Invoice Number`, then take one word (`wd1`).
With no movement given, extraction starts **at the word right after the
keyword** — which is almost always what you want.

### Anatomy of a compact pattern

```text
[variable=]keyword:[movements][type][count][flags][^start_trim][%end_trim][pgN][mtN]
          └──────┘ └────────────────────────────── compact spec ──────────────────┘
```

- `variable=` names the output column (or template variable). Omit it and a
  name is derived from the keyword.
- `keyword` is the text to search for (multi-word is fine; punctuation is
  tolerated). Everything after the **last** colon is the compact spec.

### Movements

Walk from the keyword to the content before extracting. Up to two moves:

```text
u2      up 2 lines        d1      down 1 line
l3      left 3 words      r2      right 2 words
```

```bash
# The total is on the line below the word "Total:", first word
--scrape-pattern="total=Total:d1wd1"

# Two lines down, then second word on that line
--scrape-pattern="ref=Reference:d2r2wd1"
```

Vertical movement counts only non-empty lines (blank lines in OCR text are
layout noise), and rightward movement stops at the end of the line rather
than falling off it.

### Extraction types and counts

```text
wdN     N words           (wd0 = rest of the line)
lnN     N lines           (ln0 = to end of document)
nbN     N numbers         (digits with , and . kept: 1,250.00)
```

```bash
--scrape-pattern="company=Company:wd3"     # three words after the keyword
--scrape-pattern="desc=Description:wd0"    # everything to end of line
--scrape-pattern="amount=Total:nb1"        # just the number, e.g. 1,250.00
```

### Flags

Append after the count:

```text
-       cross line breaks while extracting (flexible mode)
_       strip spaces from the extracted result
```

```bash
--scrape-pattern="city=Place of receipt:wd2_"   # "KODIAK, AK" -> "KODIAK,AK"
```

### Trimming

Shave unwanted pieces off either end of the extracted content. `^` trims
from the start, `%` trims from the end (chosen over `$` so patterns stay
safe inside double-quoted shell arguments):

```text
^chN  ^wdN  ^lnN  ^nbN      trim N characters/words/lines/numbers from the start
%chN  %wdN  %lnN  %nbN      trim the same from the end
```

```bash
# "INV-2024-001-DRAFT" -> "INV-2024-001"
--scrape-pattern="invoice=Invoice Number:wd1%ch6"

# "$1,250.00" -> "1,250.00"
--scrape-pattern="amount=Total:wd1^ch1"

# Multiple operations per block, applied in order
--scrape-pattern="ref=Reference:wd4_^wd1%ch3"
```

### Page and match selection

By default a pattern searches the page given by `--pattern-source-page`
(page 1 unless you say otherwise) and takes the first match. Override per
pattern:

```text
pg3     page 3 only          pg2-4   pages 2-4        pg3-   page 3 to end
pg-2    last 2 pages         pg0     all pages
mt2     2nd match            mt1-3   matches 1-3      mt-2   last 2 matches
mt0     all matches
```

```bash
# First invoice number found anywhere in the document
--scrape-pattern="invoice=No:wd1pg0"

# The second "Total" on page 2
--scrape-pattern="total=Total:nb1pg2mt2"
```

### Scraping to TSV

Point `--scrape-text` at a file or a whole folder. Output is one row per
PDF: a `filename` column plus one column per pattern, in pattern order:

```bash
pdf-manipulator invoices/ --scrape-text \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="date=Invoice Date:wd1" \
    --scrape-pattern="city=Place of receipt:wd2" \
    --output invoice_data.tsv
```

Failed extractions appear as `No_Match` so rows stay aligned for spreadsheet
cleanup. Many patterns? Put them in a file, one per line, and use
`--scrape-patterns-file=my_patterns.txt`.

---
## 9. Smart Renaming

> [◂ Contents](#contents) ·
> [Patterns plus a template](#patterns-plus-a-template) ·
> [Template variables](#template-variables) ·
> [Per-file naming in separate mode](#per-file-naming-in-separate-mode) ·
> [Per-group naming](#per-group-naming) ·
> [Document-level values with pg](#document-level-values-with-pg) ·
> [Safety nets](#safety-nets)

Everything from the previous section can feed the *filenames* of extracted
PDFs: add `--filename-template` alongside your `--scrape-pattern` options.

### Patterns plus a template

```bash
pdf-manipulator invoice.pdf --extract-pages=1 --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="date=Invoice Date:wd1_" \
    --filename-template="INV{inv}_{date}.pdf"
# -> INV27679_7-23-2026.pdf
```

Extracted values are sanitized for the filesystem automatically: slashes in
the date became dashes, currency symbols and unsafe characters are stripped
or replaced. You never have to pre-clean a value for filename use.

### Template variables

- `{name}` — any variable defined by your patterns
- `{range}` — the page or group description (`Pages_3-7`, `page05`, `group01`)
- `{original_name}` — the source PDF's stem
- `{name|fallback}` — use `fallback` when extraction found nothing

### Per-file naming in separate mode

This is where it gets powerful. In `--separate-files` mode, patterns without
a `pg` spec read **the page being extracted** — so every page names itself:

```bash
pdf-manipulator batch_smartocr.pdf --extract-pages=all --separate-files --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="city=Place of receipt:wd2_" \
    --filename-template="GXY{inv}_{city}.pdf"
# -> GXY27597_KODIAK-AK.pdf
#    GXY27594_KODIAK-AK.pdf
#    GXY27586_SEWARD-AK.pdf
#    ...one correctly-named file per invoice page
```

A scanned batch of invoices becomes a folder of individually named invoice
files in one command.

### Per-group naming

In `--respect-groups` mode, each group is named from its **first page** — so
a multi-page invoice grouped by a range pattern still takes its name from
its opening page:

```bash
pdf-manipulator batch.pdf --extract-pages="contains:'INVOICE' to contains:'Page 1 of'" \
    --respect-groups --batch \
    --scrape-pattern="inv=No:wd1" \
    --filename-template="{inv}_{range}.pdf"
```

### Document-level values with pg

A pattern **with** an explicit `pg` spec keeps its own page in every mode.
Use this for values that belong to the whole document:

```bash
# Every per-page file carries the page-1 batch code AND its own invoice number
pdf-manipulator batch.pdf --extract-pages=all --separate-files --batch \
    --scrape-pattern="batch=Batch:wd1pg1" \
    --scrape-pattern="inv=Invoice Number:wd1" \
    --filename-template="{batch}_{inv}.pdf"
```

### Safety nets

- **Real names in dry runs.** Pattern extraction is read-only, so
  `--dry-run` previews the actual final filenames — verify a whole batch
  before writing a single file.
- **Duplicates stay unique.** Two pages yielding the same value produce
  `NAME.pdf` and `NAME_copy_01.pdf` rather than an overwrite.
- **Failure never crashes a run.** If a pattern finds nothing, the file
  falls back to simple naming and a visible warning tells you which pattern
  missed.

---

## 10. Working with Scanned Documents

> [◂ Contents](#contents) ·
> [The sandwich PDF](#the-sandwich-pdf) ·
> [Regex for OCR artifacts](#regex-for-ocr-artifacts) ·
> [Sidecar text files](#sidecar-text-files)

### The sandwich PDF

A raw scan has no text at all — every content pattern matches nothing. Run
scans through an OCR step (the companion smart-pdf-ocr tool produces
"sandwich" PDFs: the scan image with an invisible corrected text layer) and
they behave like ordinary documents here, with two things to remember:

- Sandwich pages classify as `type:mixed`, not `type:text`.
- One unified text extractor feeds *every* feature — page selection,
  scraping, renaming, `--dump-text` — so a keyword that selects a page is
  guaranteed to be visible to a scrape pattern on that same page.

### Regex for OCR artifacts

OCR output has unreliable spacing and confuses similar glyphs (`I`/`l`/`1`,
`O`/`0`). Write patterns that absorb this: `\s*` between letters tolerates
inserted spaces, and character classes cover the usual confusions:

```bash
# Matches KODIAK, K ODIAK, K O D I A K, ...
pdf-manipulator scans.pdf --extract-pages="regex/i:'K\s*O\s*D\s*I\s*A\s*K'"

# Port pair like KOD/DAL where the slash may read as 1, l, I, |, / or \
pdf-manipulator scans.pdf \
    --extract-pages="regex/i:'K\s*O\s*D\s{0,2}[1lI|\\/]\s{0,2}D\s*A\s*L'"
```

Build a library of these in a patterns file
(see [Pattern Files](#7-pattern-files)) and reuse it across batches.

### Sidecar text files

If the OCR step produced a corrected text dump, hand it to the tool
directly and skip PDF text extraction entirely — the sidecar becomes the
text source for selection, scraping, and dumping alike. Both marker styles
are accepted: `=== page N ===` (smart-pdf-ocr) and `--- PAGE N ---` (this
tool's own `--dump-text`), which enables a full round trip: dump the text,
hand-correct it, feed it back with `--text-file`.

```bash
pdf-manipulator scan.pdf --text-file corrected.txt \
    --extract-pages="contains:'KODIAK'"

pdf-manipulator scan.pdf --text-file corrected.txt --scrape-text \
    --scrape-pattern="inv=No:wd1" --output data.tsv
```

Single-PDF runs only; the file is validated up front (missing or marker-free
sidecars are rejected before any work happens).

---

## 11. Repair and Optimization

> [◂ Contents](#contents) ·
> [Diagnosis](#diagnosis) ·
> [Fixing and shrinking](#fixing-and-shrinking)

Real-world PDFs are frequently malformed; the tool checks for this during
assessment and can repair via Ghostscript (install it separately).

### Diagnosis

```bash
pdf-manipulator odd.pdf --analyze              # quick health check
pdf-manipulator odd.pdf --analyze-detailed     # page-by-page breakdown
```

### Fixing and shrinking

```bash
pdf-manipulator odd.pdf --gs-fix                       # repair one file
pdf-manipulator scans/ --gs-batch-fix --recursive      # repair a tree
pdf-manipulator big.pdf --optimize                     # reduce file size
pdf-manipulator big.pdf --optimize --gs-quality=ebook  # pick a quality preset
```

Batch extraction also detects malformation as it scans and offers to fix
files before processing (suppress with `--no-auto-fix`).

---

## 12. Recipes

> [◂ Contents](#contents) ·
> [Split a scanned invoice batch](#split-a-scanned-invoice-batch) ·
> [Audit a batch into a spreadsheet](#audit-a-batch-into-a-spreadsheet) ·
> [Pull chapters from a report](#pull-chapters-from-a-report) ·
> [Route pages by destination](#route-pages-by-destination)

End-to-end workflows combining the pieces above.

### Split a scanned invoice batch

One scanned stack in, one named file per invoice out:

```bash
# 1. OCR the scan (smart-pdf-ocr) -> batch_smartocr.pdf
# 2. Preview the names the batch will produce
pdf-manipulator batch_smartocr.pdf --extract-pages=all --separate-files --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="city=Place of receipt:wd2_" \
    --filename-template="GXY{inv}_{city}.pdf" \
    --dry-run

# 3. Same command without --dry-run to write the files
```

### Audit a batch into a spreadsheet

```bash
pdf-manipulator batch_smartocr.pdf --scrape-text \
    --scrape-pattern="inv=No:wd1pg0" \
    --scrape-pattern="date=Invoice Date:wd1" \
    --scrape-pattern="city=Place of receipt:wd2" \
    --scrape-pattern="total=Total:nb1" \
    --output audit.tsv
```

Open `audit.tsv` in a spreadsheet, clean the stragglers by hand, done.

### Pull chapters from a report

```bash
# Every chapter as its own file, skipping the heading page of each
pdf-manipulator report.pdf \
    --extract-pages="contains:'Chapter'+1 to contains:'Summary'" \
    --respect-groups --batch

# Only chapters 1, 3 and 4
pdf-manipulator report.pdf \
    --extract-pages="contains:'Chapter' to contains:'Summary'" \
    --filter-matches="1,3,4" --respect-groups --batch
```

### Route pages by destination

Keep a pattern library of destinations, split a mixed batch by it:

```bash
# routes.txt: one OCR-tolerant regex per destination, in output order
pdf-manipulator batch_smartocr.pdf \
    --extract-pages="file:routes.txt" --respect-groups --batch \
    --scrape-pattern="inv=No:wd1" \
    --filename-template="{inv}_{range}.pdf"
```

Each destination's pages land in their own file, named by the first
invoice number in the group.

---

## 13. Quick Reference

> [◂ Contents](#contents)

### Page selection

| Spec | Meaning |
|---|---|
| `5` / `3-7` / `3:7` / `3..7` | single page / range (three spellings) |
| `10-7` | reverse range, pages in reverse order |
| `3-` / `-7` | open-ended to end / from start |
| `first 3` / `first-3` / `last 2` / `last-2` | document ends |
| `all` / `odd` / `even` | whole-document selectors |
| `::2` / `5:10:2` / `:10:3` | slices (1-indexed, stop inclusive) |
| `contains:'X'` / `regex:'P'` / `line-starts:'X'` | text patterns (`/i` = case-insensitive) |
| `type:text\|image\|mixed\|empty` | page classification |
| `size:>1MB` `size:<=100KB` | page size conditions |
| `A & B` / `A \| B` / `!A` / `( )` | boolean logic (single-space operators) |
| `A to B` | section between markers; endpoints = pattern / number / `start` / `end` |
| `file:specs.txt` | one spec per line, `#` comments |

### Scrape pattern spec

```text
[var=]keyword:[u|d|l|r N]...[wd|ln|nb]N[-_][^trim][%trim][pgN][mtN]
```

| Piece | Meaning |
|---|---|
| `u2 d1 l3 r2` | move up/down lines, left/right words (max two moves) |
| `wd2` / `ln1` / `nb1` | extract words / lines / numbers (`0` = to end) |
| `-` / `_` | cross line breaks / strip spaces |
| `^ch4` `%wd1` | trim from start / end (`ch` `wd` `ln` `nb`) |
| `pg2-4` `pg0` | page selection for this pattern |
| `mt2` `mt0` | which keyword match(es) |

### Common flags

| Flag | Purpose |
|---|---|
| `--extract-pages=SPEC` | select and extract pages |
| `--separate-files` / `--respect-groups` | output mode |
| `--scrape-text` / `--dump-text` | data extraction modes |
| `--scrape-pattern=P` / `--scrape-patterns-file=F` | extraction patterns |
| `--filename-template=T` | smart output naming |
| `--pattern-source-page=N` | fallback page for patterns (default 1) |
| `--text-file=F` | OCR sidecar text source |
| `--output=F` | TSV / text dump destination |
| `--dedup=S` | `strict` `groups` `none` `warn` `fail` |
| `--conflicts=S` | `ask` `rename` `overwrite` `skip` `fail` |
| `--batch` / `--dry-run` | unattended / preview |

---

*Generated for PDF Manipulator; see README.md for installation and the
complete command reference.*

<!-- End of file -->
