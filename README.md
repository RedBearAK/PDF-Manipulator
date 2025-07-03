# PDF Manipulator

A sophisticated CLI tool to assess PDF files, extract specific pages, split documents, and optimize file sizes with a beautiful terminal interface.

## Features

- 📊 **Smart PDF Assessment** - Scan files/folders and display comprehensive PDF information
- ✂️ **Flexible Page Extraction** - Extract any pages with powerful range syntax
- 📄 **Document Splitting** - Split multi-page PDFs into individual page files  
- 🗜️ **File Optimization** - Compress PDFs to reduce file sizes
- 🔍 **Content Analysis** - Analyze PDFs to understand file size composition
- 🎨 **Beautiful CLI Interface** - Rich tables and colored output for better readability
- 🛡️ **Safety First** - Explicit confirmations and non-destructive operations by default
- ⚡ **Versatile Processing** - Handle single files or entire folders
- 🚀 **Fast Performance** - Built on pypdf for efficient PDF manipulation

## Installation

1. **Install Python 3.7+** if not already installed

2. **Install dependencies**:
   ```bash
   pip install pypdf rich
   ```

3. **Download the script**:
   ```bash
   # Save as pdf_manipulator.py and make executable
   chmod +x pdf_manipulator.py
   ```

## Usage

### Basic Operations

```bash
# Scan current directory for PDFs
./pdf_manipulator.py

# Scan specific directory  
./pdf_manipulator.py /path/to/pdfs

# Process single file
./pdf_manipulator.py document.pdf

# Show version
./pdf_manipulator.py --version
```

### Page Operations

```bash
# Strip multi-page PDFs to first page only
./pdf_manipulator.py --strip-first

# Extract specific pages with flexible syntax
./pdf_manipulator.py --extract-pages="3-7"        # Pages 3 through 7
./pdf_manipulator.py --extract-pages="1-3,7,9-11" # Multiple ranges
./pdf_manipulator.py --extract-pages="first 3"    # First 3 pages
./pdf_manipulator.py --extract-pages="last 2"     # Last 2 pages
./pdf_manipulator.py --extract-pages="::2"        # Odd pages (1,3,5...)
./pdf_manipulator.py --extract-pages="2::2"       # Even pages (2,4,6...)
./pdf_manipulator.py --extract-pages="5:15:3"     # Every 3rd page from 5-15

# Split PDFs into individual pages
./pdf_manipulator.py --split-pages
```

### File Operations

```bash
# Optimize PDF file sizes
./pdf_manipulator.py --optimize

# Analyze PDF content and file sizes
./pdf_manipulator.py --analyze

# Process single file with specific operation
./pdf_manipulator.py document.pdf --extract-pages="3-7"
./pdf_manipulator.py document.pdf --split-pages
./pdf_manipulator.py document.pdf --optimize
```

### Processing Modes

```bash
# Interactive mode (default) - asks for each file
./pdf_manipulator.py --extract-pages="1-3"

# Batch mode - processes all matching files automatically
./pdf_manipulator.py --extract-pages="1-3" --batch

# Replace original files after processing (use with caution!)
./pdf_manipulator.py --optimize --replace
```

## Page Range Syntax

The `--extract-pages` option supports powerful and intuitive syntax:

| Syntax | Description | Example |
|--------|-------------|---------|
| `5` | Single page | Page 5 only |
| `3-7` | Range | Pages 3 through 7 |
| `3:7` | Range (alternative) | Pages 3 through 7 |
| `3..7` | Range (alternative) | Pages 3 through 7 |
| `3-` | Open-ended | Page 3 to end |
| `-7` | Open-ended | Start to page 7 |
| `first 3` | First N pages | Pages 1, 2, 3 |
| `last 2` | Last N pages | Last 2 pages |
| `1-3,7,9-11` | Multiple ranges | Pages 1-3, 7, and 9-11 |
| `::2` | Step syntax | Odd pages (1,3,5...) |
| `2::2` | Step syntax | Even pages (2,4,6...) |
| `5:20:3` | Step with range | Every 3rd page from 5-20 |

## Example Output

```
Scanning /home/user/documents/pdfs...

                    PDF Files Assessment
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ File              ┃  Pages ┃ Size (MB)  ┃ Status        ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ document1.pdf     │      1 │       0.45 │ ✓ Single page │
│ report2023.pdf    │     25 │      12.30 │ ⚠️  Multi-page │
│ invoice.pdf       │      3 │       1.20 │ ⚠️  Multi-page │
└───────────────────┴────────┴────────────┴───────────────┘

Found 2 multi-page PDFs

Available operations:
  --strip-first   Strip to first page only
  --extract-pages Extract specific pages (e.g., "3-7", "last 2")
  --split-pages   Split into individual pages
  --optimize      Optimize file sizes
  --analyze       Analyze PDF contents
```

## Advanced Examples

### Extract Specific Content

```bash
# Extract first page only from all PDFs
./pdf_manipulator.py --strip-first --batch

# Extract pages 2-5 from a presentation
./pdf_manipulator.py slides.pdf --extract-pages="2-5"

# Extract every other page (odd pages)
./pdf_manipulator.py --extract-pages="::2"

# Extract first and last pages only
./pdf_manipulator.py --extract-pages="1,-1"
```

### Batch Processing

```bash
# Optimize all PDFs in a folder
./pdf_manipulator.py /path/to/pdfs --optimize --batch

# Split all multi-page PDFs into individual pages
./pdf_manipulator.py --split-pages --batch

# Extract first 3 pages from all PDFs and replace originals
./pdf_manipulator.py --extract-pages="first 3" --batch --replace
```

### Analysis and Optimization

```bash
# Analyze large PDFs to understand file sizes
./pdf_manipulator.py --analyze

# Optimize a specific large file
./pdf_manipulator.py large_document.pdf --optimize
```

## Safety Features

- **Non-destructive by default** - Original files are preserved unless `--replace` is used
- **Explicit confirmations** - Interactive mode asks before processing each file
- **Clear file naming** - Output files use descriptive names (e.g., `document_pages3-7.pdf`)
- **Long-form arguments only** - No short flags to prevent accidental misuse
- **Validation** - Page ranges are validated before processing

## Design Philosophy

- **Clarity over brevity** - Uses descriptive `--long-arguments` instead of `-short` flags
- **Safety first** - Destructive operations require explicit confirmation
- **Explicit is better than implicit** - No ambiguous behavior or hidden defaults
- **Rich feedback** - Beautiful tables and progress indicators for better user experience

## Integration with Other Tools

The tool works well with other PDF utilities:

- **OCRmyPDF**: Add OCR to scanned PDFs before processing
- **img2pdf**: Convert images to PDF before manipulation  
- **pandoc**: Convert documents to PDF before processing
- **pdfunite/pdftk**: Merge PDFs before page extraction

## Troubleshooting

### Common Issues

1. **"pypdf not found"**: Run `pip install pypdf rich`
2. **"Permission denied"**: Make script executable with `chmod +x pdf_manipulator.py`
3. **"Invalid page range"**: Check syntax - use quotes for complex ranges like `"1-3,7"`

### Performance Tips

- Use `--batch` mode for processing many files
- The `--analyze` operation helps identify large files that benefit from optimization
- Consider `--optimize` for scanned PDFs with large file sizes

## License

This tool is provided as-is for personal and commercial use.

## Contributing

Feel free to extend this tool for your needs. Some enhancement ideas:

- Add GUI interface with tkinter or PyQt
- Support for encrypted PDFs with password handling
- Custom optimization profiles for different use cases
- Integration with cloud storage services
- Batch configuration files for complex processing rules
