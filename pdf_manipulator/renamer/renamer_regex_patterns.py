"""
Regex patterns for the renamer subsection.
File: pdf_manipulator/renamer/renamer_regex_patterns.py

Fixed patterns with proper validation for Phase 4 trimming.
"""

import re

# Main compact pattern with mandatory trimmer operations after ^ and $
COMPACT_PATTERN_RGX = re.compile(
    r'^([udlr]\d{1,2})?([udlr]\d{1,2})?(wd|ln|nb)(\d{1,2})([_\-]*)'
    r'(\^(?:(?:wd|ln|nb|ch)\d{1,3})+)?'
    r'(\$(?:(?:wd|ln|nb|ch)\d{1,3})+)?'
    r'(pg(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?'
    r'(mt(?:\d{1,3}-\d{1,3}|\d{1,3}-|-\d{1,3}|\d{1,3}|0))?$'
)

# Validation for stray trimmer characters
STRAY_START_TRIMMER_RGX = re.compile(r'\^(?:wd|ln|nb|ch)\d{1,3}')
STRAY_END_TRIMMER_RGX = re.compile(r'\$(?:wd|ln|nb|ch)\d{1,3}')

# Python identifier validation
PYTHON_IDENTIFIER_RGX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Filename sanitization patterns
FILENAME_UNSAFE_CHARS_RGX = re.compile(r'[<>:"/\\|?*]')
FILE_EXTENSION_RGX = re.compile(r'\.([a-zA-Z0-9]+)$')
WHITESPACE_NORMALIZE_RGX = re.compile(r'\s+')

# End of file #
