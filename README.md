# PDF Manipulator

A CLI tool to assess PDF files in a folder, show page counts, and optionally strip multi-page PDFs to their first page only, with file size optimization.

## Features

- 📊 Scan folders for PDF files and display page counts
- ✂️ Strip multi-page PDFs to first page only
- 🗜️ Optimize PDF file sizes
- 🔄 Option to replace original files
- 🎨 Beautiful CLI interface with colors and tables
- 🚀 Fast processing using pikepdf (based on qpdf)

## Installation

### Python Version (Recommended)

1. **Install Python 3.7+** if not already installed

2. **Clone or download the script**:
   ```bash
   # Save the Python script as pdf_manipulator.py
   chmod +x pdf_manipulator.py
   ```

3. **Install dependencies**:
   ```bash
   pip install pikepdf rich
   # Optional: pip install Pillow  # for advanced image optimization
   ```

### Bash Version (Alternative)

1. **Install required tools**:
   
   **macOS:**
   ```bash
   brew install qpdf
   # Optional: brew install ghostscript  # for better optimization
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install qpdf
   # Optional: sudo apt-get install ghostscript
   ```
   
   **Fedora:**
   ```bash
   sudo dnf install qpdf
   # Optional: sudo dnf install ghostscript
   ```

2. **Make the script executable**:
   ```bash
   chmod +x pdf_manipulator.sh
   ```

## Usage

### Python Version

```bash
# Scan current directory
./pdf_manipulator.py

# Scan specific directory
./pdf_manipulator.py /path/to/pdfs

# Replace original files after confirmation
./pdf_manipulator.py --replace /path/to/pdfs

# Auto-process all multi-page PDFs
./pdf_manipulator.py --auto /path/to/pdfs

# Only optimize file sizes (keep all pages)
./pdf_manipulator.py --optimize-only /path/to/pdfs
```

### Bash Version

```bash
# Scan current directory
./pdf_manipulator.sh

# Scan specific directory
./pdf_manipulator.sh /path/to/pdfs

# Replace original files
./pdf_manipulator.sh -r /path/to/pdfs

# Auto-process without prompts
./pdf_manipulator.sh -a /path/to/pdfs
```

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

report2023.pdf - 25 pages, 12.30 MB
Strip to first page only? [y/N] y
✓ Created: report2023_page1.pdf (0.85 MB)
Size reduction: 93.1%
```

## Features Comparison

| Feature | Python Version | Bash Version |
|---------|---------------|--------------|
| Page counting | ✅ | ✅ |
| Strip to first page | ✅ | ✅ |
| File optimization | ✅ Advanced | ✅ Basic |
| Beautiful tables | ✅ | ❌ |
| Cross-platform | ✅ | ⚠️ Unix-like |
| Dependencies | pikepdf, rich | qpdf/pdftk |

## Advanced Usage

### Python Script Customization

You can easily extend the Python script to:
- Extract specific page ranges
- Merge multiple PDFs
- Add watermarks
- Compress images more aggressively
- Batch process with custom rules

### Integration with Other Tools

The tool can be combined with other PDF utilities:
- **OCRmyPDF**: Add OCR to scanned PDFs before processing
- **img2pdf**: Convert images to PDF before processing
- **pdftk/qpdf**: Use for additional manipulations

## Troubleshooting

### Common Issues

1. **"pikepdf not found"**: Run `pip install pikepdf rich`
2. **"qpdf not found"**: Install qpdf using your package manager
3. **Permission denied**: Make script executable with `chmod +x`

### Performance Tips

- For large batches, use `--auto` mode
- The Python version is generally faster for complex operations
- Use `--no-optimize` if you only need page stripping

## License

This tool is provided as-is for personal and commercial use.

## Contributing

Feel free to modify and extend this tool for your needs. Some ideas:
- Add GUI with tkinter or PyQt
- Add support for encrypted PDFs
- Implement custom page range extraction
- Add batch configuration files
