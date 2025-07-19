# PDF Manipulator

A sophisticated CLI tool to assess PDF files, extract specific pages, split documents, and optimize file sizes with a beautiful terminal interface.


## Features

- 📊 **Smart PDF Assessment** - Scan files/folders and display comprehensive PDF information

- ✂️ **Flexible Page Extraction** - Extract any pages with powerful range syntax

- 🔀 **Smart Extraction Modes** - Extract as single documents, separate files, or respect original groupings

- 📑 **Flexible File Organization** - Choose how extracted pages are organized and named

- 📄 **Document Splitting** - Split multi-page PDFs into individual page files  

- 🗜️ **File Optimization** - Compress PDFs to reduce file sizes (sometimes)

- 🔍 **Content Analysis** - Analyze PDFs to understand file size composition

- 🎨 **Beautiful CLI Interface** - Rich tables and colored output for better readability

- 🛡️ **Safety First** - Explicit confirmations and non-destructive operations by default

- ⚡ **Versatile Processing** - Handle single files or entire folders

- 🚀 **Fast Performance** - Built on pypdf for efficient PDF manipulation


## Installation

**Install Python 3.8+** (if not already installed)


### Option 1: Package Installation (Recommended)

1. **Clone the repository**

   ```
   git clone <your-repo-url>
   cd PDF-Manipulator
   ```

1. **Install dependencies**:

   ```bash
   pip install pypdf rich
   ```

1. **Run as a package**:

   ```bash
   python -m pdf_manipulator
   ```


### Option 2: Development Installation

   ```
   pip install -e .
   ```


## Usage


### Basic Operations

```bash
# Scan current directory for PDFs
python -m pdf_manipulator

# Scan specific directory  
python -m pdf_manipulator /path/to/pdfs

# Process single file
python -m pdf_manipulator document.pdf

# Show version
python -m pdf_manipulator --version
```


### Page Operations

```bash
# Strip multi-page PDFs to first page only
python -m pdf_manipulator --strip-first

# Extract specific pages with flexible syntax
python -m pdf_manipulator --extract-pages="3-7"        # Pages 3 through 7
python -m pdf_manipulator --extract-pages="1-3,7,9-11" # Multiple ranges
python -m pdf_manipulator --extract-pages="first 3"    # First 3 pages
python -m pdf_manipulator --extract-pages="last 2"     # Last 2 pages
python -m pdf_manipulator --extract-pages="::2"        # Odd pages (1,3,5...)
python -m pdf_manipulator --extract-pages="2::2"       # Even pages (2,4,6...)
python -m pdf_manipulator --extract-pages="5:15:3"     # Every 3rd page from 5-15

# Split PDFs into individual pages
python -m pdf_manipulator --split-pages
```


### File Operations

```bash
# Optimize PDF file sizes
python -m pdf_manipulator --optimize

# Analyze PDF content and file sizes
python -m pdf_manipulator --analyze

# Process single file with specific operation
python -m pdf_manipulator document.pdf --extract-pages="3-7"
python -m pdf_manipulator document.pdf --split-pages
python -m pdf_manipulator document.pdf --optimize
```


### Processing Modes

```bash
# Interactive mode (default) - asks for each file
python -m pdf_manipulator --extract-pages="1-3"

# Batch mode - processes all matching files automatically
python -m pdf_manipulator --extract-pages="1-3" --batch

# Replace original files after processing (use with caution!)
python -m pdf_manipulator --optimize --replace
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
| `"1-3,7,9-11"` | Multiple ranges | Pages 1-3, 7, and 9-11 |
| `"1-3,7,9-11"` | With --respect-groups | Pages 1-3 as group, 7 alone, 9-11 as group |
| `::2` | Step syntax | Odd pages (1,3,5...) |
| `2::2` | Step syntax | Even pages (2,4,6...) |
| `5:20:3` | Step with range | Every 3rd page from 5-20 |


## Extraction Options

Control how extracted pages are organized:


### Single Document (Default)

   ```bash
   python -m pdf_manipulator --extract-pages="1-3,7,9-11"
   # Creates: document_pages1-3,7,9-11.pdf
   ```


### Separate Documents

   ```bash
   python -m pdf_manipulator --extract-pages="1-3,7,9-11" --separate-files
   # Creates: document_page01.pdf, document_page02.pdf, document_page03.pdf, 
   #          document_page07.pdf, document_page09.pdf, document_page10.pdf, document_page11.pdf
   ```


### Separate Documents, Ranges Grouped in Single Document

   ```bash
   python -m pdf_manipulator --extract-pages="1-3,7,9-11" --respect-groups
   # Creates: document_pages1-3.pdf, document_page07.pdf, document_pages9-11.pdf
   ```

### Interactive Choice

When using `--extract-pages` without `--separate-files` or `--respect-groups`, the tool will prompt you to choose between the three modes above.



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
python -m pdf_manipulator --strip-first --batch

# Extract pages 2-5 from a presentation
python -m pdf_manipulator slides.pdf --extract-pages="2-5"

# Extract every other page (odd pages)
python -m pdf_manipulator --extract-pages="::2"

# Extract first and last pages only
python -m pdf_manipulator --extract-pages="1,-1"
```


### Batch Processing

```bash
# Optimize all PDFs in a folder
python -m pdf_manipulator /path/to/pdfs --optimize --batch

# Split all multi-page PDFs into individual pages
python -m pdf_manipulator --split-pages --batch

# Extract first 3 pages from all PDFs and replace originals
python -m pdf_manipulator --extract-pages="first 3" --batch --replace
```


### Analysis and Optimization

```bash
# Analyze large PDFs to understand file sizes
python -m pdf_manipulator --analyze

# Optimize a specific large file
python -m pdf_manipulator large_document.pdf --optimize
```


## Safety Features

- **Non-destructive by default** - Original files are preserved unless `--replace` is used
- **Explicit confirmations** - Interactive mode asks before processing each file
- **Clear file naming** - Output files use descriptive names (e.g., `document_pages3-7.pdf`)
- **Long-form arguments only** - No short flags to prevent accidental misuse
- **Validation** - Page ranges are validated before processing


## Design Philosophy

- **Clarity over brevity** - Uses descriptive `--long-arguments` instead of `-s` short flags
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
1. **"Invalid page range"**: Check syntax - use quotes for complex ranges like `"1-3,7"`
1. **"No module named pdf_manipulator"**: Ensure you're running from the correct directory, or add the location of parent folder of `pdf_manipulator` folder to the `PYTHONPATH` environment variable
1. **Import errors**: Try `python -m pdf_manipulator` instead of running files directly


### Performance Tips

- Use `--batch` mode for processing many files
- The `--analyze` operation helps identify large files that benefit from optimization
- Consider `--optimize` for scanned PDFs with large file sizes


## License

GNU General Public License 3.0

This tool is provided as-is for personal and commercial use.


## Contributing

Feel free to extend this tool for your needs. Some enhancement ideas:

- Add GUI interface with tkinter or PyQt
- Support for encrypted PDFs with password handling
- Custom optimization profiles for different use cases
- Integration with cloud storage services
- Batch configuration files for complex processing rules
