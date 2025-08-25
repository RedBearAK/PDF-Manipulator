"""
Text patterns for pdfplumber processing.
File: simple_pdf_scraper/processors/pdfplumber_patterns.py

Contains regex patterns used by pdfplumber processor for text validation
and spacing decisions.
"""

import re


# Date pattern detection (MM/DD/YY or MM/DD/YYYY)
date_pattern_rgx = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')

# Time pattern detection (HH:MM:SS or HH:MM)
time_pattern_rgx = re.compile(r'\d{1,2}:\d{2}(:\d{2})?')

# Currency amount pattern ($X,XXX.XX)
currency_pattern_rgx = re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?')

# Numeric sequence that should stay together
numeric_sequence_rgx = re.compile(r'\d+(?:[.,]\d+)*')

# Common abbreviations that shouldn't be split
abbreviation_rgx = re.compile(r'[A-Z]+\.')

# Word boundary detection (letter to letter transitions)
word_boundary_rgx = re.compile(r'[a-z][A-Z]')

# End of file #
