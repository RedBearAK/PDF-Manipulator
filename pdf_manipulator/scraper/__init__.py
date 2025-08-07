"""
Simple PDF Scraper - Extract targeted text data from standardized PDF files.

A focused tool for extracting specific patterns of text from machine-generated
PDFs using configurable search patterns and directional rules.
"""

__version__ = "20250803.0"
__author__ = "RedBearAK"
__email__ = "64876997+RedBearAK@users.noreply.github.com"
__description__ = "A Python package for excel_recipe_processor"


from simple_pdf_scraper.processors.base import PDFProcessor
from simple_pdf_scraper.output.tsv_writer import TSVWriter
from simple_pdf_scraper.extractors.pattern_extractor import PatternExtractor


__all__ = ['PDFProcessor', 'PatternExtractor', 'TSVWriter']

