"""
Regex patterns for the extractors subsection.  
File: pdf_manipulator/scraper/extractors/extractor_regex_patterns.py

Fixed patterns for trimming operations and content extraction.
"""

import re

# Trimmer operation parsing
TRIMMER_OPERATION_RGX = re.compile(r'(wd|ln|nb|ch)(\d{1,3})')

# Number detection for trimming
NUMBER_DETECTION_RGX = re.compile(r'\d+(?:[.,]\d+)*')

# Signed numbers for other uses
SIGNED_NUMBER_RGX = re.compile(r'-?\d+(?:[.,]\d+)*')

# Content extraction patterns
WORD_BOUNDARY_RGX = re.compile(r'\S+')
LINE_SPLIT_RGX = re.compile(r'\r?\n')
SPACE_REMOVAL_RGX = re.compile(r'\s')

# End of file #
