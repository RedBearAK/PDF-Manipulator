"""
Embedded PDF scraper - Extract targeted text data from standardized PDF files.
File: pdf_manipulator/scraper/__init__.py

Formerly the standalone Simple PDF Scraper project, now fully merged into
pdf-manipulator. Extracts specific patterns of text from machine-generated
PDFs using configurable search patterns and directional rules.
"""


from pdf_manipulator.scraper.processors.base import PDFProcessor
from pdf_manipulator.scraper.output.tsv_writer import TSVWriter
from pdf_manipulator.scraper.extractors.pattern_extractor import PatternExtractor


__all__ = ['PDFProcessor', 'PatternExtractor', 'TSVWriter']

