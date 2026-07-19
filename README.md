# PDF Manipulator

**Advanced PDF page extraction and manipulation tool with intelligent content analysis**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PDF Manipulator is a powerful command-line tool that goes beyond simple page extraction. It understands PDF content, allowing you to extract pages by type, size, text content, or complex boolean expressions. Perfect for processing documents, reports, and scanned materials with precision.

## 🚀 Key Features

- **Content-Aware Selection**: Extract pages by type (text/image/mixed), size, or text content
- **Advanced Boolean Logic**: Combine criteria with AND, OR, NOT operations
- **Range Patterns**: Find sections like "Chapter 1 to Chapter 2" across multiple occurrences  
- **Group Filtering**: Process results and filter by index or additional criteria
- **Boundary Detection**: Split pages into logical groups at chapter/section boundaries
- **Smart Renaming**: Name every output file from its own extracted content (invoice numbers, dates, cities)
- **Text Scraping**: Pull structured data from PDFs into TSV with compact patterns and precise trimming
- **Unified Text Extraction**: One text source for all features, with smart-pdf-ocr sidecar support
- **Malformed PDF Repair**: Automatic detection and fixing with Ghostscript integration
- **Batch Processing**: Handle entire folders with intelligent automation
- **Multiple Output Modes**: Single document, separate files, or respect logical groupings

## 🔤 Unified Text Extraction and Smart-OCR Sidecar Text

All text-based features (page selection patterns, scrape patterns, `--dump-text`)
read page text through a single unified provider, so a keyword that selects a
page is always visible to a scrape pattern on that same page. The provider uses
raw pdfplumber (best line reconstruction for OCR'd documents) with a pypdf
fallback, cached per document.

For scanned documents processed with the separate **smart-pdf-ocr** tool, the
corrected text output can be supplied directly as the text source:

```bash
# Use smart-pdf-ocr corrected text ("=== page N ===" markers) instead of PDF extraction
pdf-manipulator scan.pdf --text-file corrected.txt --extract-pages="contains:'KODIAK'"
pdf-manipulator scan.pdf --text-file corrected.txt --scrape-text \
    --scrape-pattern="invoice=No:wd1" --output data.tsv
```

The smart-pdf-ocr searchable PDFs (`--pdf-out`) also work directly as input,
since their corrected text layer is extracted like any other text.

## ✂️ Phase 4 Pattern Trimming

Scrape patterns support start/end trimming for precise cleanup of extracted
content. End trimmers use `%` (not `$`) so patterns are safe inside
double-quoted shell arguments:

```bash
# "INV-2024-001-DRAFT" -> "INV-2024-001"  (trim 6 chars from the end)
pdf-manipulator file.pdf --scrape-text --scrape-pattern="invoice=Invoice Number:wd1%ch6"

# Trim words/chars/lines/numbers from either end, multiple per block
#   ^chN ^wdN ^lnN ^nbN   from the start
#   %chN %wdN %lnN %nbN   from the end
pdf-manipulator file.pdf --scrape-text --scrape-pattern="ref=Reference:r1wd4_^wd1%ch3"
```

## 📊 Standalone Scraper Modes

```bash
# Dump page-by-page text (debugging; uses the unified provider)
pdf-manipulator file.pdf --dump-text --output raw.txt

# Extract pattern data to TSV (one row per PDF, one column per variable)
pdf-manipulator invoices/ --scrape-text \
    --scrape-pattern="invoice=No:wd1" \
    --scrape-pattern="date=Invoice Date:wd1" \
    --output extracted_data.tsv
```

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/RedBearAK/PDF-Manipulator.git
cd pdf-manipulator

# Install dependencies
pip install -r requirements.txt

# Optional: Install Ghostscript for PDF repair capabilities
# macOS: brew install ghostscript
# Ubuntu: sudo apt-get install ghostscript
# Windows: Download from https://www.ghostscript.com/download/
```

## ⚡ Quick Examples

### Basic Page Extraction
```bash
# Extract specific pages
pdf-manipulator document.pdf --extract-pages="1-5,10,15-20"

# Extract first 3 pages  
pdf-manipulator document.pdf --extract-pages="first 3"

# Extract odd pages only
pdf-manipulator document.pdf --extract-pages="::2"
```

### Content-Based Selection
```bash
# Extract all text-heavy pages
pdf-manipulator document.pdf --extract-pages="type:text"

# Extract large pages (over 1MB each)
pdf-manipulator document.pdf --extract-pages="size:>1MB"

# Find pages containing specific text
pdf-manipulator document.pdf --extract-pages="contains:'Invoice'"

# Extract pages with figures or charts
pdf-manipulator document.pdf --extract-pages="contains:'Figure' | contains:'Chart'"
```

### Advanced Boolean Logic
```bash
# Text pages under 500KB (efficient pages)
pdf-manipulator document.pdf --extract-pages="type:text & size:<500KB"

# Important pages excluding drafts
pdf-manipulator document.pdf --extract-pages="contains:'Important' & !contains:'DRAFT'"

# All pages except empty ones
pdf-manipulator document.pdf --extract-pages="all & !type:empty"
```

### Section Extraction (Range Patterns)
```bash
# Extract all chapters (finds every "Chapter X to Chapter Y" section)
pdf-manipulator document.pdf --extract-pages="contains:'Chapter' to contains:'Summary'"

# From page 5 to first appendix
pdf-manipulator document.pdf --extract-pages="5 to contains:'Appendix'"

# Article sections with offsets
pdf-manipulator document.pdf --extract-pages="contains:'Article'+1 to contains:'References'-1"
```

### Group Filtering & Boundary Detection
```bash
# Find chapters, but only extract chapters 1, 3, and 4
pdf-manipulator document.pdf \
  --extract-pages="contains:'Chapter' to contains:'Summary'" \
  --filter-matches="1,3,4"

# Extract text pages, split at section boundaries, keep only important sections
pdf-manipulator document.pdf \
  --extract-pages="type:text" \
  --group-start="contains:'Section'" \
  --filter-matches="contains:'Critical'"

# Complex filtering with page exclusions
pdf-manipulator document.pdf \
  --extract-pages="type:text | type:mixed" \
  --filter-matches="contains:'Important' & !25-40"
```

## 📖 Complete Usage Guide

### Page Range Syntax

#### Basic Ranges
```bash
5                    # Single page
3-7                  # Pages 3 through 7
3:7                  # Alternative range syntax  
3..7                 # Another range syntax
10-7                 # REVERSE range: pages 10, 9, 8, 7 in that order
3-                   # Page 3 to end
-7                   # Start to page 7
1-3,7,9-11          # Multiple ranges (use quotes)
10,5,1               # Comma order is preserved: extracts 10, then 5, then 1
```

Comma-separated specs keep the order you wrote them in whenever it carries
meaning (out-of-order numbers, reverse ranges, first/last, patterns). Plain
ascending numeric lists are simply sorted.

#### Special Selectors
```bash
"first 3"           # First 3 pages (or the dash form: first-3)
"last 2"            # Last 2 pages  (or: last-2)
all                 # All pages
odd / even          # Odd or even pages
```

#### Slicing (start:stop:step, any part omitted)
1-indexed with an INCLUSIVE stop -- page-range semantics, not Python's:
```bash
::2                 # Every 2nd page from page 1 -> 1, 3, 5, ...
2::2                # Every 2nd page from page 2 -> 2, 4, 6, ...
5:10                # Pages 5 through 10 (same as 5-10)
5:10:2              # Every 2nd page from 5 through 10 -> 5, 7, 9
:10:3               # Every 3rd page from 1 through 10 -> 1, 4, 7, 10
3:                  # Page 3 to end
```
Backwards slices, zero steps, and starts beyond the document raise clear
errors instead of silently matching nothing.

### Content-Based Patterns

#### Text Matching
```bash
contains:"Invoice"           # Pages containing "Invoice"
contains/i:"invoice"         # Case-insensitive search
regex:"Ch\d+"               # Regular expression matching
line-starts:"Summary"       # Lines starting with "Summary"
```

#### Page Type Classification
```bash
type:text                   # Text-heavy pages
type:image                  # Scanned/image pages  
type:mixed                  # Pages with both text and images
type:empty                  # Blank or minimal content pages
```

Invalid type values and malformed size conditions fail immediately with
usage guidance rather than silently matching nothing.

**Smart-OCR note**: pages from smart-pdf-ocr searchable PDFs classify as
`type:mixed` (they contain the scan image AND the text layer), not
`type:text`. Use `type:mixed` or content patterns when selecting on OCR'd
documents.

#### Size-Based Filtering
```bash
size:<500KB                 # Pages under 500KB
size:>1MB                   # Pages over 1MB
size:>=2MB                  # Pages 2MB or larger
size:<=100KB                # Pages 100KB or smaller
```

### Boolean Expressions

#### Basic Operations
```bash
# AND: Both conditions must be true
"type:text & contains:'Important'"

# OR: Either condition can be true  
"type:image | size:>2MB"

# NOT: Exclude matching pages
"all & !contains:'DRAFT'"
"!type:empty"
```

**Operator spacing is strict**: `&` and `|` must have exactly one space on
each side. Malformed operators (`a& b`, `a  &  b`, trailing `type:text |`)
raise a clear error instead of being silently treated as content patterns.
Quoted text is always free: `contains:'A & B'` searches for the literal
ampersand.

#### Numeric Operands (Page-Window Intersections)

Pages, ranges, slices, and first/last are valid boolean operands, so
selections can be confined to a page window:

```bash
# Every 2nd page from 5-15 that ALSO matches the pattern
"5:15:2 & regex/i:'K\s*O\s*D'"

# Mixed-content pages within the first 10
"first-10 & type:mixed"

# Everything except pages 4-7
"all & !4-7"

# Two windows joined
"3-5 | 8-9"
```

#### Complex Combinations
```bash
# Multiple conditions
"type:text & size:<500KB & contains:'Summary'"

# Grouped logic with parentheses
"(type:text | type:mixed) & !contains:'DRAFT'"

# Range exclusions
"contains:'Article' & !15-25"
```

### Range Patterns (Section Extraction)

Find content between patterns - extracts ALL matching sections:

```bash
# Pattern to pattern
"contains:'Chapter 1' to contains:'Chapter 2'"

# Number to pattern
"5 to contains:'Appendix'"

# Pattern to number  
"contains:'Introduction' to 20"

# With offset adjustments
"contains:'Section'+1 to contains:'References'-1"

# Document boundary keywords
"contains:'Appendix' to end"
"start to contains:'Introduction'"
```

Endpoints can be content patterns (with optional `+N`/`-N` offsets), plain
page numbers, or the keywords `start`/`end` for the document boundaries.
The ` to ` separator matches in any case (`TO`, `To`, `tO`). Quoted text like
`contains:'A to B'` never triggers range detection.

### Advanced Group Processing

#### Group Filtering
Filter the groups that result from page selection:

```bash
# Keep only specific group indices
--filter-matches="1,3,5"              # Groups 1, 3, and 5
--filter-matches="2-4"                 # Groups 2 through 4

# Content-based group filtering
--filter-matches="contains:'Important'"    # Groups containing "Important"
--filter-matches="size:>1MB"              # Groups over 1MB total
--filter-matches="type:text & !25-40"     # Text groups not overlapping pages 25-40
```

#### Boundary Detection
Split pages into logical groups at specific boundaries:

```bash
# Start new groups at chapter boundaries
--group-start="contains:'Chapter'"

# End groups at summary pages
--group-end="contains:'Summary'"  

# Both start and end boundaries
--group-start="contains:'Article'" --group-end="contains:'References'"
```

### Output Modes

```bash
# Default: Single combined document
pdf-manipulator file.pdf --extract-pages="1-5,10"

# Separate files (one per page)
pdf-manipulator file.pdf --extract-pages="1-5,10" --separate-files

# Respect groupings (ranges→multi-page, individuals→single files)
pdf-manipulator file.pdf --extract-pages="1-3,7,9-11" --respect-groups
```

### Smart Renaming (Pattern-Based Filenames)

Combine `--scrape-pattern` with `--filename-template` and every output file
is named from its own extracted content. Works in all three output modes:

```bash
# Single document: variables extracted from --pattern-source-page (default 1)
pdf-manipulator invoice.pdf --extract-pages=1 --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="date=Invoice Date:wd1_" \
    --filename-template="INV{inv}_{date}.pdf"
# -> INV27679_7-23-2026.pdf

# Separate files: EACH PAGE NAMES ITSELF -- patterns without pg specs read
# the page being extracted, so an invoice batch splits into per-invoice files
pdf-manipulator batch.pdf --extract-pages=1-5 --separate-files --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="city=Place of receipt:wd2_" \
    --filename-template="GXY{inv}_{city}.pdf"
# -> GXY27597_KODIAK-AK.pdf, GXY27594_KODIAK-AK.pdf, GXY27586_SEWARD-AK.pdf, ...

# Grouped files: each group is named from its FIRST page
pdf-manipulator batch.pdf --extract-pages="1-2,3" --respect-groups --batch \
    --scrape-pattern="inv=Invoice Number:wd1" \
    --filename-template="{inv}_{range}.pdf"
```

Semantics worth knowing:

- Patterns **without** `pg` specs read from the page being extracted
  (separate mode) or the group's first page (grouped mode). Patterns
  **with** explicit `pg` specs stay document-level: `batch=Batch:wd1pg1`
  puts the same page-1 batch code into every filename alongside each page's
  own values.
- Built-in variables: `{range}` (page/group description),
  `{original_name}`, and `{var|fallback}` fallback syntax.
- Extracted values are sanitized for filenames automatically (slashes in
  dates become dashes: `7/23/2026` -> `7-23-2026`; the `_` pattern flag
  drops spaces so `KODIAK, AK` -> `KODIAK-AK`).
- Duplicate extracted values resolve to unique names
  (`INV-DUP.pdf`, `INV-DUP_copy_01.pdf`).
- `--dry-run` previews the REAL extracted names (extraction is read-only),
  so you can verify a whole batch before writing anything.
- If extraction fails, naming falls back to the simple scheme with a
  visible warning -- a bad pattern never crashes an extraction run.

### Batch Processing

```bash
# Process entire folder interactively
pdf-manipulator /path/to/folder --extract-pages="type:text"

# Batch mode (no prompts)
pdf-manipulator /path/to/folder --extract-pages="type:text" --batch

# Replace originals (CAREFUL!)
pdf-manipulator /path/to/folder --extract-pages="first 1" --batch --replace
```

## 🔧 PDF Repair & Optimization

### Malformed PDF Detection & Repair
```bash
# Analyze PDF for issues
pdf-manipulator document.pdf --analyze

# Detailed page-by-page analysis  
pdf-manipulator document.pdf --analyze-detailed

# Fix malformed PDF
pdf-manipulator document.pdf --gs-fix

# Batch fix all PDFs in folder
pdf-manipulator /path/to/folder --gs-batch-fix

# Optimize file size
pdf-manipulator document.pdf --optimize
```

### Ghostscript Integration
```bash
# Different quality settings
pdf-manipulator document.pdf --gs-fix --gs-quality=ebook

# Process recursively
pdf-manipulator /path/to/folder --gs-batch-fix --recursive

# Dry run (see what would be fixed)
pdf-manipulator /path/to/folder --gs-batch-fix --dry-run
```

## 💡 Real-World Examples

### Document Processing
```bash
# Extract executive summary from annual reports
pdf-manipulator annual-report.pdf --extract-pages="contains:'Executive Summary' to contains:'Financial'"

# Get all financial tables (large, image-heavy pages)
pdf-manipulator report.pdf --extract-pages="type:mixed & size:>1MB"

# Extract appendices only
pdf-manipulator document.pdf --extract-pages="contains:'Appendix' to end"
```

### Academic Papers
```bash
# Extract just the methodology sections from multiple papers
pdf-manipulator papers/ --extract-pages="contains:'Methodology' to contains:'Results'" --batch

# Get figures and charts only
pdf-manipulator paper.pdf --extract-pages="contains:'Figure' | contains:'Chart' | contains:'Table'"

# Everything except references
pdf-manipulator paper.pdf --extract-pages="all & !contains:'References'"
```

### Magazine/Newsletter Processing
```bash
# Extract articles, filter for important ones, exclude ads
pdf-manipulator magazine.pdf \
  --extract-pages="contains:'Article' to type:empty" \
  --filter-matches="contains:'Feature' | size:>500KB" \
  --separate-files
```

### Invoice/Receipt Processing  
```bash
# Extract invoices by detecting invoice numbers
pdf-manipulator statements.pdf --extract-pages="regex:'INV-\d+'"

# Financial summaries only
pdf-manipulator documents.pdf --extract-pages="contains:'Total' & contains:'$'"

# Split a scanned invoice batch into per-invoice files, each named from its
# own content (run smart-pdf-ocr first for the searchable PDF)
pdf-manipulator batch_smartocr.pdf --extract-pages=all --separate-files --batch \
    --scrape-pattern="inv=No:wd1" \
    --scrape-pattern="city=Place of receipt:wd2_" \
    --filename-template="GXY{inv}_{city}.pdf"

# Scrape the whole batch to a spreadsheet instead of splitting it
pdf-manipulator batch_smartocr.pdf --scrape-text \
    --scrape-pattern="inv=No:wd1pg0" \
    --scrape-pattern="date=Invoice Date:wd1" \
    --scrape-pattern="city=Place of receipt:wd2" \
    --output batch_data.tsv
```

### OCR'd Document Selection (pattern files)
```bash
# OCR text has unreliable spacing and character confusion; regex patterns
# with optional whitespace handle it: K\s*O\s*D matches "KOD", "K OD", "K O D"
pdf-manipulator scans.pdf --extract-pages="regex/i:'K\s*O\s*D\s*I\s*A\s*K'"

# Keep a library of city/route patterns in a file, one spec per line
# (lines starting with # are comments); groups appear in pattern order
pdf-manipulator scans.pdf --extract-pages="file:PATTERNS.txt" --respect-groups

# Search only within a page window
pdf-manipulator scans.pdf --extract-pages="40:60 & regex/i:'S\s*E\s*W\s*A\s*R\s*D'"
```

## 🛠️ Command Reference

### Operations
```bash
--extract-pages=RANGE     # Extract specific pages/content
--split-pages             # Split into individual pages
--scrape-text             # Extract pattern data to TSV (no page extraction)
--dump-text               # Dump page-by-page text (debugging)
--optimize                # Optimize file size
--analyze                 # Basic PDF analysis
--analyze-detailed        # Detailed page-by-page breakdown
--gs-fix                  # Fix malformed PDF with Ghostscript
--gs-batch-fix            # Batch fix malformed PDFs
```

### Extraction Options
```bash
--separate-files          # Extract as separate documents
--respect-groups          # Respect comma-separated groupings
--filter-matches=CRITERIA # Filter groups by index or content
--group-start=PATTERN     # Start new groups at pattern
--group-end=PATTERN       # End groups at pattern
```

### Pattern Extraction & Naming
```bash
--scrape-pattern=PATTERN  # Compact extraction pattern (repeatable)
--scrape-patterns-file=F  # Load patterns from a file (one per line)
--filename-template=TMPL  # Name outputs from extracted variables
--pattern-source-page=N   # Fallback page for patterns without pg specs
--text-file=FILE          # smart-pdf-ocr sidecar text as the text source
--output=FILE             # Output file for --scrape-text / --dump-text
```

### Processing Modes
```bash
--batch                   # Process without prompts
--recursive               # Process subdirectories (with --gs-batch-fix)
--dry-run                 # Show what would be done
--replace                 # Replace original files
--no-auto-fix             # Disable automatic malformation fixing
```

### Ghostscript Options
```bash
--gs-quality=SETTING      # Quality: screen, ebook, printer, prepress, default
--replace-originals       # Replace originals with fixed versions
```

## 🐛 Troubleshooting

### Common Issues

**"Malformed PDF detected"**
- Use `--gs-fix` to repair structural issues
- Add `--no-auto-fix` to skip automatic repairs in batch mode

**"No pages found matching criteria"**  
- Use `--analyze-detailed` to see page content breakdown
- Try broader criteria: `type:text | type:mixed`

**Large file sizes after extraction**
- Use `--optimize` to compress results
- Consider `--gs-fix` for malformed PDFs (often reduces size significantly)

**Ghostscript not found**
- Install Ghostscript: `brew install ghostscript` (macOS) or `apt install ghostscript` (Ubuntu)

### Getting Help
```bash
pdf-manipulator --help                    # Full help
pdf-manipulator document.pdf --analyze    # Understand your PDF structure  
pdf-manipulator document.pdf --analyze-detailed  # Page-by-page breakdown
```

## 🔍 Advanced Tips

### Pattern Development
1. Start with `--analyze-detailed` to understand your PDF
2. Test patterns on small ranges first: `--extract-pages="contains:'test' & 1-10"`
3. Use boolean logic to refine: `pattern & !unwanted_pattern`

### Performance Optimization
- Use `--batch` mode for multiple files
- Consider `--gs-fix` for malformed PDFs (often improves processing speed)
- Use content filters to avoid processing irrelevant pages

### Complex Workflows
```bash
# Multi-stage processing: fix, analyze, then extract
pdf-manipulator document.pdf --gs-fix
pdf-manipulator document_gs_fixed.pdf --analyze-detailed  
pdf-manipulator document_gs_fixed.pdf --extract-pages="your_refined_criteria"
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests for any improvements.

---

