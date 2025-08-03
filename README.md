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
- **Malformed PDF Repair**: Automatic detection and fixing with Ghostscript integration
- **Batch Processing**: Handle entire folders with intelligent automation
- **Multiple Output Modes**: Single document, separate files, or respect logical groupings

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-manipulator.git
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
3-                   # Page 3 to end
-7                   # Start to page 7
1-3,7,9-11          # Multiple ranges (use quotes)
```

#### Special Selectors
```bash
"first 3"           # First 3 pages
"last 2"            # Last 2 pages  
all                 # All pages
::2                 # Odd pages (every 2nd starting from 1)
2::2                # Even pages (every 2nd starting from 2)
5:20:3              # Every 3rd page from 5 to 20
```

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
```

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
pdf-manipulator document.pdf --extract-pages="contains:'Appendix' to $"
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
```

## 🛠️ Command Reference

### Operations
```bash
--extract-pages=RANGE     # Extract specific pages/content
--split-pages             # Split into individual pages
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

