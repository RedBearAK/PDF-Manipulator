"""
Regex patterns for smart filename generation.
File: pdf_manipulator/core/smart_filename_patterns.py

Contains all regex patterns used by smart_filenames.py to avoid
breaking the main module while editing in artifacts.
"""

import re


# Numeric range patterns
simple_numeric_range_rgx = re.compile(r'^\d+(-\d+)?$')
extended_numeric_range_rgx = re.compile(r'^\d+(-\d+|:\d+|..\d+)?$')

# Filename sanitization patterns  
problematic_filename_chars_rgx = re.compile(r'[<>:"/\\|?*]')
whitespace_to_underscore_rgx = re.compile(r'\s+')
multiple_underscores_rgx = re.compile(r'_+')

# Timestamp removal patterns
datetime_timestamp_rgx = re.compile(r'^\d{8}_?\d{6}_?')
datetime_date_only_rgx = re.compile(r'^\d{8}_?')
unix_timestamp_rgx = re.compile(r'^\d{10}_?')

# Existing extraction pattern removal
pages_extraction_rgx = re.compile(r'_pages.*$')
extracted_extraction_rgx = re.compile(r'_extracted.*$') 
groups_extraction_rgx = re.compile(r'_groups.*$')


# End of file #
