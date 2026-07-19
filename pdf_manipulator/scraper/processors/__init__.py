"""
PDF processors package - Pluggable backends for PDF text extraction.
"""

from pdf_manipulator.scraper.processors.base import PDFProcessor
from pdf_manipulator.scraper.processors.pypdf_processor import PyPDFProcessor

__all__ = ['PDFProcessor', 'PyPDFProcessor']
