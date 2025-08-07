"""
PDF processors package - Pluggable backends for PDF text extraction.
"""

from simple_pdf_scraper.processors.base import PDFProcessor
from simple_pdf_scraper.processors.pypdf_processor import PyPDFProcessor

__all__ = ['PDFProcessor', 'PyPDFProcessor']
