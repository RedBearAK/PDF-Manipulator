"""
Smart filename generation for multi-argument page selections.
File: pdf_manipulator/core/smart_filenames.py
"""

import re
from pathlib import Path
from typing import Any
from datetime import datetime

from pdf_manipulator.core.smart_filename_patterns import (
    simple_numeric_range_rgx,
    extended_numeric_range_rgx,
    problematic_filename_chars_rgx,
    whitespace_to_underscore_rgx,
    multiple_underscores_rgx,
    datetime_timestamp_rgx,
    datetime_date_only_rgx,
    unix_timestamp_rgx,
    pages_extraction_rgx,
    extracted_extraction_rgx,
    groups_extraction_rgx
)


def generate_smart_description(arguments: list, total_pages: int, max_length: int = 50) -> str:
    """
    Generate concise description for multi-argument selections.
    
    Args:
        arguments: List of page selection arguments
        total_pages: Total number of pages found
        max_length: Maximum description length
        
    Returns:
        Smart, concise description string
    """
    if not arguments:
        return "empty"
    
    if len(arguments) == 1:
        return _describe_single_argument(arguments[0])
    
    if len(arguments) <= 3:
        # For small lists, show individual descriptions
        descriptions = [_describe_single_argument(arg) for arg in arguments]
        combined = ", ".join(descriptions)
        if len(combined) <= max_length:
            return combined
    
    # For complex multi-argument cases, use smart categorization
    return _categorize_arguments(arguments, total_pages)


def _describe_single_argument(argument: str) -> str:
    """Describe a single page selection argument."""
    arg = argument.strip()
    
    # Simple numeric ranges
    if simple_numeric_range_rgx.match(arg):
        return f"pages{arg}"
    
    # Contains patterns
    if arg.startswith('contains:'):
        content = arg[9:].strip('"\'')
        if len(content) > 15:
            content = content[:12] + "..."
        return f"contains_{_sanitize_for_filename(content)}"
    
    # Regex patterns
    if arg.startswith('regex:'):
        return "regex_pattern"
    
    # Boolean expressions (simplified)
    if '&' in arg or '|' in arg:
        return "boolean_expr"
    
    # File selectors
    if arg.startswith('file:'):
        filename = arg[5:].replace('.txt', '')
        return _sanitize_for_filename(filename)
    
    # Special keywords
    special_keywords = {
        'all': 'all_pages',
        'odd': 'odd_pages', 
        'even': 'even_pages',
        'first': 'first_pages',
        'last': 'last_pages'
    }
    
    for keyword, desc in special_keywords.items():
        if keyword in arg.lower():
            return desc
    
    # Default fallback
    return _sanitize_for_filename(arg)[:10]


def _categorize_arguments(arguments: list, total_pages: int) -> str:
    """Categorize multiple arguments into a smart description."""
    # Count argument types
    categories = {
        'patterns': 0,
        'booleans': 0, 
        'ranges': 0,
        'keywords': 0,
        'files': 0
    }
    
    for arg in arguments:
        arg_lower = arg.lower().strip()
        
        if 'contains:' in arg or 'regex:' in arg:
            categories['patterns'] += 1
        elif '&' in arg or '|' in arg:
            categories['booleans'] += 1
        elif extended_numeric_range_rgx.match(arg):
            categories['ranges'] += 1
        elif arg.startswith('file:'):
            categories['files'] += 1
        elif any(keyword in arg_lower for keyword in ['all', 'odd', 'even', 'first', 'last']):
            categories['keywords'] += 1
        else:
            categories['patterns'] += 1  # Default assumption
    
    # Build description parts
    parts = []
    if categories['files'] > 0:
        parts.append(f"{categories['files']}files")
    if categories['patterns'] > 0:
        parts.append(f"{categories['patterns']}patterns")
    if categories['booleans'] > 0:
        parts.append(f"{categories['booleans']}booleans")
    if categories['ranges'] > 0:
        parts.append(f"{categories['ranges']}ranges")
    if categories['keywords'] > 0:
        parts.append(f"{categories['keywords']}keywords")
    
    if not parts:
        return f"mixed_{len(arguments)}args"
    
    # Combine parts intelligently
    if len(parts) == 1:
        return f"{parts[0]}_{total_pages}pg"
    elif len(parts) == 2:
        return f"{'-'.join(parts)}_{total_pages}pg"
    else:
        return f"mixed_{len(arguments)}args_{'-'.join(parts[:2])}_{total_pages}pg"


def _sanitize_for_filename(text: str) -> str:
    """Sanitize text for use in filenames."""
    # Remove problematic characters
    sanitized = problematic_filename_chars_rgx.sub('_', text)
    
    # Replace spaces with underscores
    sanitized = whitespace_to_underscore_rgx.sub('_', sanitized)
    
    # Remove multiple consecutive underscores
    sanitized = multiple_underscores_rgx.sub('_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized


def generate_extraction_filename(pdf_path: Path, 
                                page_description: str,
                                extraction_mode: str = 'single',
                                timestamp: bool = True,
                                custom_prefix: str = None) -> Path:
    """
    Generate a smart filename for extraction operations.
    
    Args:
        pdf_path: Source PDF file path
        page_description: Description of pages being extracted
        extraction_mode: 'single', 'separate', or 'grouped'
        timestamp: Whether to include timestamp
        custom_prefix: Optional custom prefix instead of timestamp
        
    Returns:
        Generated output file path
    """
    stem = pdf_path.stem
    
    # # Clean up existing problematic patterns
    # stem = _clean_existing_filename(stem)
    
    # Prepare description
    clean_desc = _sanitize_for_filename(page_description)
    
    # Prepare prefix
    if custom_prefix:
        prefix = _sanitize_for_filename(custom_prefix)
    elif timestamp:
        now = datetime.now()
        prefix = now.strftime("%Y%m%d_%H%M%S")
    else:
        prefix = None
    
    # Build filename parts
    parts = []
    if prefix:
        parts.append(prefix)
    
    parts.append(stem)
    
    # Add extraction mode context
    if extraction_mode == 'separate':
        parts.append('pages')
    elif extraction_mode == 'grouped': 
        parts.append('groups')
    else:
        parts.append('extracted')
    
    # Add description (but keep total length reasonable)
    if clean_desc and clean_desc != 'all':
        parts.append(clean_desc)
    
    # Combine parts with underscores
    filename_base = '_'.join(parts)
    
    # Ensure reasonable length (Windows has 255 char limit, leave room for path)
    if len(filename_base) > 80:
        # Truncate description part but keep other parts
        if len(parts) > 3:
            # Keep prefix, stem, mode, truncate description
            truncated_desc = clean_desc[:20] + "..."
            filename_base = '_'.join(parts[:-1] + [truncated_desc])
        else:
            filename_base = filename_base[:80]
    
    return pdf_path.parent / f"{filename_base}.pdf"


# def _clean_existing_filename(filename_stem: str) -> str:
#     """Clean up problematic patterns in existing filenames."""
#     # Remove existing timestamps
#     stem = unix_timestamp_rgx.sub('', filename_stem)
#     stem = datetime_timestamp_rgx.sub('', stem) # With or without "_" between
#     stem = datetime_date_only_rgx.sub('', stem) # Handle date-only timestamps
    
#     # Remove existing extraction patterns
#     stem = pages_extraction_rgx.sub('', stem)
#     stem = extracted_extraction_rgx.sub('', stem)
#     stem = groups_extraction_rgx.sub('', stem)
    
#     # Remove trailing separators
#     stem = stem.strip('_-')
    
#     return stem if stem else 'document'


def suggest_batch_naming_scheme(pdf_paths: list[Path], 
                                common_operation: str) -> dict[str, Any]:
    """
    Suggest a naming scheme for batch operations.
    
    Args:
        pdf_paths: List of PDF file paths being processed
        common_operation: Description of the common operation
        
    Returns:
        Dictionary with naming suggestions
    """
    # Find common patterns in filenames
    stems = [path.stem for path in pdf_paths]
    
    # Find common prefix
    common_prefix = ""
    if len(stems) > 1:
        min_length = min(len(s) for s in stems)
        for i in range(min_length):
            if all(s[i] == stems[0][i] for s in stems):
                common_prefix += stems[0][i]
            else:
                break
        common_prefix = common_prefix.rstrip('_-')
    
    # Find common suffix (before existing operation markers)
    # cleaned_stems = [_clean_existing_filename(stem) for stem in stems]
    common_suffix = ""
    if len(stems) > 1:
        min_length = min(len(s) for s in stems)
        for i in range(1, min_length + 1):
            if all(s[-i] == stems[0][-i] for s in stems):
                common_suffix = stems[0][-i] + common_suffix
            else:
                break
        common_suffix = common_suffix.lstrip('_-')
    
    return {
        'common_prefix': common_prefix,
        'common_suffix': common_suffix,
        'suggested_base': common_prefix or common_suffix or 'batch',
        'operation_desc': _sanitize_for_filename(common_operation),
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'count': len(pdf_paths)
    }


# End of file #
