"""
Template-based file naming system for PDF manipulator.
File: pdf_manipulator/renamer/__init__.py

Provides intelligent filename generation using extracted content patterns
and template substitution for PDF extraction operations.
"""

from pdf_manipulator.renamer.template_engine import TemplateEngine
from pdf_manipulator.renamer.pattern_processor import PatternProcessor
from pdf_manipulator.renamer.filename_generator import FilenameGenerator
from pdf_manipulator.renamer.sanitizer import sanitize_variable_name, sanitize_filename


__all__ = [
    'TemplateEngine',
    'PatternProcessor', 
    'FilenameGenerator',
    'sanitize_variable_name',
    'sanitize_filename'
]

# End of file #
