"""
Command line interface for Simple PDF Scraper.
File: simple_pdf_scraper/cli.py
"""

import os
import sys
import glob
import argparse
import warnings

from pathlib import Path

from simple_pdf_scraper.output.tsv_writer import TSVWriter
from simple_pdf_scraper.processors.pypdf_processor import PyPDFProcessor
from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


def parse_pattern(pattern_str):
    """
    Parse pattern string in format: keyword:direction:distance:extract_type
    
    Examples:
        "Invoice Number:right:2:number" - Find number 2 words to the right of "Invoice Number"
        "Total:below:1:line" - Extract entire line 1 line below "Total"
        "Date:left:3:word" - Extract single word 3 words to the left of "Date"
    """
    parts = pattern_str.split(':')
    if len(parts) != 4:
        raise ValueError(f"Pattern must have format 'keyword:direction:distance:extract_type', got: {pattern_str}")
    
    keyword, direction, distance, extract_type = parts
    
    try:
        distance = int(distance)
    except ValueError:
        raise ValueError(f"Distance must be a number, got: {distance}")
    
    if direction not in ['left', 'right', 'above', 'below']:
        raise ValueError(f"Direction must be one of: left, right, above, below, got: {direction}")
    
    if extract_type not in ['word', 'number', 'line', 'text']:
        raise ValueError(f"Extract type must be one of: word, number, line, text, got: {extract_type}")
    
    return {
        'keyword': keyword.strip(),
        'direction': direction,
        'distance': distance,
        'extract_type': extract_type
    }


def parse_patterns_file(file_path):
    """Parse patterns from a file, one pattern per line."""
    patterns = []
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and comments
                try:
                    patterns.append(parse_pattern(line))
                except ValueError as e:
                    print(f"Error in patterns file line {line_num}: {e}", file=sys.stderr)
                    return None
    return patterns


def suppress_pypdf_warnings():
    """Suppress pypdf warnings about malformed PDFs."""
    # Suppress specific pypdf warnings
    warnings.filterwarnings("ignore", message=".*wrong pointing object.*")
    warnings.filterwarnings("ignore", message=".*Ignoring wrong pointing object.*")
    
    # Redirect stderr temporarily to capture and filter pypdf messages
    class FilteredStderr:
        def __init__(self, original_stderr):
            self.original = original_stderr
            
        def write(self, message):
            # Filter out pypdf error messages
            if not ("wrong pointing object" in message or 
                   "Ignoring wrong pointing object" in message):
                self.original.write(message)
                
        def flush(self):
            self.original.flush()
            
        def __getattr__(self, name):
            return getattr(self.original, name)
    
    return FilteredStderr(sys.stderr)


def dump_text_from_pdf(pdf_file, processor, verbose=False, output_file=None):
    """Extract and dump raw text from a PDF file."""
    try:
        if verbose:
            print(f"Extracting text from: {pdf_file}")
        
        pages = processor.extract_pages(pdf_file)
        
        # Determine output destination
        if output_file:
            output = open(output_file, 'w', encoding='utf-8')
            if verbose:
                print(f"Writing text to: {output_file}")
        else:
            output = sys.stdout
        
        try:
            print(f"\n{'='*60}", file=output)
            print(f"TEXT DUMP: {pdf_file}", file=output)
            print(f"{'='*60}", file=output)
            print(f"Total pages: {len(pages)}", file=output)
            print(f"Extracted: {sum(1 for p in pages if p.strip())}/{len(pages)} pages with text\n", file=output)
            
            for page_num, page_text in enumerate(pages, 1):
                print(f"--- PAGE {page_num} ---", file=output)
                if page_text.strip():
                    print(page_text, file=output)
                    # Show line count for this page
                    line_count = len([line for line in page_text.split('\n') if line.strip()])
                    if verbose:
                        print(f"(Page {page_num}: {line_count} lines)", file=output)
                else:
                    print("(No text found on this page)", file=output)
                print(file=output)
            
            # Show summary
            total_lines = sum(len([line for line in page.split('\n') if line.strip()]) for page in pages)
            print(f"--- SUMMARY ---", file=output)
            print(f"Total text lines across all pages: {total_lines}", file=output)
            
        finally:
            if output_file:
                output.close()
        
        return True
        
    except Exception as e:
        print(f"Error processing {pdf_file}: {e}", file=sys.stderr)
        return False


def create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract targeted text data from PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dump raw text to console (debugging)
  python -m simple_pdf_scraper --dump-text document.pdf
  
  # Dump text to file
  python -m simple_pdf_scraper --dump-text document.pdf -o extracted_text.txt
  
  # Extract invoice number (word immediately right of "Invoice #")
  python -m simple_pdf_scraper invoice.pdf --pattern "Invoice #:right:0:word"
  
  # Extract company name (line above "Invoice #") 
  python -m simple_pdf_scraper invoice.pdf --pattern "Invoice #:above:1:line"
  
  # Multiple patterns from file
  python -m simple_pdf_scraper *.pdf --patterns-file patterns.txt -o results.tsv

Pattern format: keyword:direction:distance:extract_type
  keyword:       Text to search for (case-insensitive)
  direction:     left, right, above, below
  distance:      Number of words/lines to move from keyword
  extract_type:  word, number, line, text

Note: Text maintains line structure internally, so 'above' and 'below'
work even though TSV output flattens results into cells.
        """
    )
    
    parser.add_argument('files', nargs='+', help='PDF file(s) to process (supports wildcards)')
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--dump-text', action='store_true',
                           help='Extract and display raw text from PDFs (debugging mode)')
    mode_group.add_argument('--pattern', action='append', 
                           help='Single pattern (can be used multiple times)')
    mode_group.add_argument('--patterns-file', 
                           help='File containing patterns, one per line')
    
    # Output options
    parser.add_argument('--output', '-o', 
                       help='Output file name (default: extracted_data.tsv for patterns, stdout for --dump-text)')
    parser.add_argument('--headers', nargs='+',
                       help='Custom column headers (default: auto-generated from patterns)')
    
    # Processing options
    parser.add_argument('--processor', default='pypdf', choices=['pypdf'],
                       help='PDF processing backend (default: pypdf)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress pypdf warnings about malformed PDFs')
    
    # Verbosity
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed processing information')
    
    return parser


def expand_file_paths(file_patterns):
    """Expand file patterns and return list of actual PDF files."""
    pdf_files = []
    for pattern in file_patterns:
        if '*' in pattern or '?' in pattern:
            matches = glob.glob(pattern)
            pdf_files.extend([f for f in matches if f.lower().endswith('.pdf')])
        else:
            if pattern.lower().endswith('.pdf') and Path(pattern).exists():
                pdf_files.append(pattern)
            else:
                print(f"Warning: Skipping non-PDF or non-existent file: {pattern}", file=sys.stderr)
    
    return sorted(set(pdf_files))  # Remove duplicates and sort


def main():
    """Main entry point for the CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set up error filtering for pypdf
    original_stderr = sys.stderr
    if args.quiet or args.dump_text:
        sys.stderr = suppress_pypdf_warnings()
    
    try:
        # Expand file paths
        pdf_files = expand_file_paths(args.files)
        if not pdf_files:
            print("Error: No PDF files found", file=sys.stderr)
            return 1
        
        # Initialize processor
        if args.processor == 'pypdf':
            processor = PyPDFProcessor()
        else:
            print(f"Error: Unknown processor: {args.processor}", file=sys.stderr)
            return 1
        
        # Handle dump-text mode
        if args.dump_text:
            if args.verbose:
                print(f"Found {len(pdf_files)} PDF files to dump")
            
            success_count = 0
            for pdf_file in pdf_files:
                if dump_text_from_pdf(pdf_file, processor, args.verbose, args.output):
                    success_count += 1
            
            if args.verbose:
                print(f"\nProcessed {success_count}/{len(pdf_files)} files successfully")
            
            return 0 if success_count > 0 else 1
        
        # Handle pattern extraction mode
        if not (args.pattern or args.patterns_file):
            print("Error: Must specify --pattern or --patterns-file when not using --dump-text", file=sys.stderr)
            return 1
        
        # Parse patterns
        if args.pattern:
            try:
                patterns = [parse_pattern(p) for p in args.pattern]
            except ValueError as e:
                print(f"Error parsing pattern: {e}", file=sys.stderr)
                return 1
        else:
            patterns = parse_patterns_file(args.patterns_file)
            if patterns is None:
                return 1
        
        if not patterns:
            print("Error: No valid patterns specified", file=sys.stderr)
            return 1
        
        # Set default output file for pattern mode
        output_file = args.output or 'extracted_data.tsv'
        
        if args.verbose:
            print(f"Found {len(pdf_files)} PDF files to process")
            print(f"Using {len(patterns)} extraction patterns")
        
        extractor = PatternExtractor()
        
        # Set up column headers
        if args.headers:
            if len(args.headers) != len(patterns):
                print(f"Error: Number of headers ({len(args.headers)}) must match number of patterns ({len(patterns)})", file=sys.stderr)
                return 1
            headers = ['filename', 'page'] + args.headers
        else:
            headers = ['filename', 'page'] + [p['keyword'] for p in patterns]
        
        # Process files
        all_results = []
        total_files = len(pdf_files)
        processed_files = 0
        
        for pdf_file in pdf_files:
            if args.verbose:
                print(f"Processing: {pdf_file}")
            
            try:
                pages = processor.extract_pages(pdf_file)
                for page_num, page_text in enumerate(pages, 1):
                    row = [pdf_file, page_num]
                    
                    for pattern in patterns:
                        result = extractor.extract_pattern(page_text, pattern)
                        row.append(result if result is not None else '')
                    
                    # Only add row if at least one pattern matched
                    if any(cell != '' for cell in row[2:]):
                        all_results.append(row)
                
                processed_files += 1
                
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}", file=sys.stderr)
                continue
        
        # Write results
        if all_results:
            writer = TSVWriter()
            writer.write_results(output_file, headers, all_results)
            
            if args.verbose:
                print(f"Successfully processed {processed_files}/{total_files} files")
                print(f"Extracted {len(all_results)} rows of data")
                print(f"Results written to: {output_file}")
        else:
            print("No data extracted from any files", file=sys.stderr)
            return 1
        
        return 0
        
    finally:
        # Restore original stderr
        sys.stderr = original_stderr


if __name__ == "__main__":
    sys.exit(main())

# End of file #
