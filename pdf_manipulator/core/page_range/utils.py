"""Utility functions for page range parsing."""

import re


def create_pattern_description(range_str: str) -> str:
    """Create filename-safe description from pattern."""
    if len(range_str) > 15:
        return "pattern-match"
    safe = re.sub(r'[^\w\-]', '-', range_str)
    return safe[:15]


def create_boolean_description(range_str: str) -> str:
    """Create filename-safe description from boolean expression."""
    if len(range_str) > 20:
        return "boolean-match"
    
    # Replace operators with words
    safe = range_str.replace(' & ', '-and-')
    safe = safe.replace(' | ', '-or-')
    safe = safe.replace('!', 'not-')
    
    # Remove other special characters
    safe = re.sub(r'[^\w\-]', '-', safe)
    return safe[:20]


def sanitize_filename(text: str, max_length: int = 20) -> str:
    """Remove invalid filename characters and truncate."""
    safe = re.sub(r'[^\w\-]', '-', text)
    return safe[:max_length]
