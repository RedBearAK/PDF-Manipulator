"""
PyPDF processor implementation with improved error handling.
File: simple_pdf_scraper/processors/pypdf_processor.py
"""

import io
import sys
import warnings

from pathlib import Path
from contextlib import redirect_stderr

import pypdf

from simple_pdf_scraper.processors.base import PDFProcessor


class PyPDFProcessor(PDFProcessor):
    """
    PDF processor using the pypdf library.
    
    Good balance of speed and reliability for machine-generated PDFs.
    Includes improved error handling for corrupted or malformed PDFs.
    """
    
    def __init__(self, suppress_warnings=True):
        """
        Initialize the processor.
        
        Args:
            suppress_warnings (bool): Whether to suppress pypdf warnings
        """
        self.suppress_warnings = suppress_warnings
        
        if suppress_warnings:
            # Suppress pypdf warnings about malformed PDFs
            warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
    
    def extract_pages(self, pdf_path):
        """Extract text from all pages using pypdf."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        pages_text = []
        
        try:
            with open(pdf_path, 'rb') as file:
                # Capture stderr to suppress pypdf error messages if needed
                stderr_capture = io.StringIO() if self.suppress_warnings else None
                
                with redirect_stderr(stderr_capture) if stderr_capture else self._null_context():
                    reader = pypdf.PdfReader(file)
                    
                    # Check if PDF is encrypted
                    if reader.is_encrypted:
                        raise Exception("PDF is password protected and cannot be processed")
                    
                    for page_num, page in enumerate(reader.pages):
                        try:
                            # Extract text and clean up common pypdf artifacts
                            text = page.extract_text()
                            # Normalize whitespace but preserve line structure
                            text = self._clean_text(text)
                            pages_text.append(text)
                        except Exception as page_error:
                            # If individual page fails, add empty text but continue
                            pages_text.append("")
                            if not self.suppress_warnings:
                                print(f"Warning: Failed to extract text from page {page_num + 1}: {page_error}", file=sys.stderr)
                    
        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages for common issues
            if "PDF starts with" in error_msg:
                raise Exception(f"File {pdf_path} is not a valid PDF")
            elif "decrypt" in error_msg.lower():
                raise Exception(f"PDF {pdf_path} is encrypted and cannot be processed")
            elif "damaged" in error_msg.lower() or "corrupt" in error_msg.lower():
                raise Exception(f"PDF {pdf_path} appears to be corrupted")
            else:
                raise Exception(f"Error reading PDF {pdf_path}: {error_msg}")
        
        return pages_text
    
    def extract_page(self, pdf_path, page_number):
        """Extract text from a specific page using pypdf."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            with open(pdf_path, 'rb') as file:
                stderr_capture = io.StringIO() if self.suppress_warnings else None
                
                with redirect_stderr(stderr_capture) if stderr_capture else self._null_context():
                    reader = pypdf.PdfReader(file)
                    
                    if reader.is_encrypted:
                        raise Exception("PDF is password protected and cannot be processed")
                    
                    if page_number < 1 or page_number > len(reader.pages):
                        raise IndexError(f"Page {page_number} out of range (1-{len(reader.pages)})")
                    
                    page = reader.pages[page_number - 1]  # Convert to 0-based
                    text = page.extract_text()
                    return self._clean_text(text)
                    
        except (IndexError, FileNotFoundError):
            raise
        except Exception as e:
            error_msg = str(e)
            if "PDF starts with" in error_msg:
                raise Exception(f"File {pdf_path} is not a valid PDF")
            elif "decrypt" in error_msg.lower():
                raise Exception(f"PDF {pdf_path} is encrypted and cannot be processed")
            else:
                raise Exception(f"Error reading page {page_number} from PDF {pdf_path}: {error_msg}")
    
    def get_page_count(self, pdf_path):
        """Get page count efficiently using pypdf."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            with open(pdf_path, 'rb') as file:
                stderr_capture = io.StringIO() if self.suppress_warnings else None
                
                with redirect_stderr(stderr_capture) if stderr_capture else self._null_context():
                    reader = pypdf.PdfReader(file)
                    
                    if reader.is_encrypted:
                        raise Exception("PDF is password protected and cannot be processed")
                    
                    return len(reader.pages)
        except FileNotFoundError:
            raise
        except Exception as e:
            error_msg = str(e)
            if "PDF starts with" in error_msg:
                raise Exception(f"File {pdf_path} is not a valid PDF")
            elif "decrypt" in error_msg.lower():
                raise Exception(f"PDF {pdf_path} is encrypted and cannot be processed")
            else:
                raise Exception(f"Error reading PDF {pdf_path}: {error_msg}")
    
    def validate_pdf(self, pdf_path):
        """
        Check if a file is a valid PDF that can be processed.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            dict: Validation result with 'valid' (bool), 'error' (str), and 'info' (dict)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return {
                'valid': False,
                'error': 'File does not exist',
                'info': {}
            }
        
        if not pdf_path.is_file():
            return {
                'valid': False,
                'error': 'Path is not a file',
                'info': {}
            }
        
        try:
            with open(pdf_path, 'rb') as file:
                stderr_capture = io.StringIO() if self.suppress_warnings else None
                
                with redirect_stderr(stderr_capture) if stderr_capture else self._null_context():
                    reader = pypdf.PdfReader(file)
                    
                    info = {
                        'page_count': len(reader.pages),
                        'encrypted': reader.is_encrypted,
                        'metadata': reader.metadata if hasattr(reader, 'metadata') else None
                    }
                    
                    if reader.is_encrypted:
                        return {
                            'valid': False,
                            'error': 'PDF is password protected',
                            'info': info
                        }
                    
                    # Try to extract text from first page to test readability
                    if len(reader.pages) > 0:
                        try:
                            reader.pages[0].extract_text()
                        except Exception as extract_error:
                            return {
                                'valid': False,
                                'error': f'Cannot extract text: {extract_error}',
                                'info': info
                            }
                    
                    return {
                        'valid': True,
                        'error': None,
                        'info': info
                    }
                    
        except Exception as e:
            error_msg = str(e)
            if "PDF starts with" in error_msg:
                error = "Not a valid PDF file"
            elif "decrypt" in error_msg.lower():
                error = "PDF is encrypted"
            elif "damaged" in error_msg.lower() or "corrupt" in error_msg.lower():
                error = "PDF appears to be corrupted"
            else:
                error = f"PDF processing error: {error_msg}"
            
            return {
                'valid': False,
                'error': error,
                'info': {}
            }
    
    def _clean_text(self, text):
        """
        Clean up text extracted by pypdf.
        
        Remove common artifacts while preserving the structure needed
        for pattern matching.
        """
        if not text:
            return ""
        
        # Replace multiple consecutive spaces with single space
        # but preserve line breaks for positional matching
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Normalize spaces within lines
            cleaned_line = ' '.join(line.split())
            if cleaned_line:  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def _null_context(self):
        """Return a null context manager for when we don't want to redirect stderr."""
        from contextlib import nullcontext
        return nullcontext()
    
    def get_processor_info(self):
        """Return information about this processor."""
        return {
            'name': 'PyPDF',
            'library': 'pypdf',
            'version': getattr(pypdf, '__version__', 'unknown'),
            'features': ['text_extraction', 'page_count', 'fast_processing', 'encryption_detection'],
            'best_for': 'machine_generated_pdfs',
            'suppress_warnings': self.suppress_warnings
        }
    
    def set_warning_suppression(self, suppress):
        """
        Enable or disable warning suppression.
        
        Args:
            suppress (bool): Whether to suppress pypdf warnings
        """
        self.suppress_warnings = suppress
        
        if suppress:
            warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
        else:
            warnings.filterwarnings("default", category=UserWarning, module="pypdf")

# End of file #
