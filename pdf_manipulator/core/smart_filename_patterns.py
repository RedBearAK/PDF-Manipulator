# Populate with the regex patterns from the smart filename module,
# assigned to variables with "_rgx" suffixes, for the smart filename 
# module to import, to avoid breaking the main module while editing
# in artifacts.




# All of these need to be set up here as variables and cleaned 
# out of the smart filename module:

#     # Simple numeric ranges
#     if re.match(r'^\d+(-\d+)?$', arg):
#         return f"pages{arg}"

#         elif re.match(r'^\d+(-\d+|:\d+|..\d+)?$', arg):


# def _sanitize_for_filename(text: str) -> str:
#     """Sanitize text for use in filenames."""
#     # Remove problematic characters
#     sanitized = re.sub(r'[<>:"/\\|?*]', '_', text)
    
#     # Replace spaces with underscores
#     sanitized = re.sub(r'\s+', '_', sanitized)
    
#     # Remove multiple consecutive underscores
#     sanitized = re.sub(r'_+', '_', sanitized)
    
#     # Remove leading/trailing underscores
#     sanitized = sanitized.strip('_')
    
#     return sanitized


# def _clean_existing_filename(filename_stem: str) -> str:
#     """Clean up problematic patterns in existing filenames."""
#     # Remove existing timestamps
#     stem = re.sub(r'^\d{8}_?\d{6}_?', '', filename_stem)
#     stem = re.sub(r'^\d{10}_?', '', stem)  # Unix timestamps
    
#     # Remove existing extraction patterns
#     stem = re.sub(r'_pages[^_]*$', '', stem)
#     stem = re.sub(r'_extracted[^_]*$', '', stem)
#     stem = re.sub(r'_groups[^_]*$', '', stem)
    
#     # Clean up OCR artifacts
#     stem = re.sub(r'_OCRd?$', '', stem, flags=re.IGNORECASE)
    
#     # Remove trailing separators
#     stem = stem.strip('_-')
    
#     return stem if stem else 'document'
