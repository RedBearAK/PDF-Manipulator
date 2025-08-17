"""
Phase 4 Trimming System - Core Logic Implementation
File: pdf_manipulator/scraper/extractors/trimming.py

Start/end trimming operations for precise character-level extraction.
"""

import re

from pdf_manipulator.scraper.extractors.extractor_regex_patterns import (
    TRIMMER_OPERATION_RGX,
    NUMBER_DETECTION_RGX
)

from typing import List, Tuple, Union


class TrimmingError(Exception):
    """Exception for trimming operation errors."""
    pass


def parse_trimmer_block(trimmer_string: str) -> List[Tuple[str, int]]:
    """
    Parse trimmer block into list of (type, count) operations.
    
    Args:
        trimmer_string: e.g., "wd1ch5nb2" 
        
    Returns:
        [('wd', 1), ('ch', 5), ('nb', 2)]
        
    Raises:
        TrimmingError: For invalid trimmer syntax
    """
    if not trimmer_string:
        return []
    
    trimmers = []
    pattern = re.compile(r'(wd|ln|nb|ch)(\d{1,3})')
    
    matches = list(pattern.finditer(trimmer_string))
    if not matches:
        raise TrimmingError(f"No valid trimmers found in: '{trimmer_string}'")
    
    # Check if entire string was matched
    matched_length = sum(len(match.group(0)) for match in matches)
    if matched_length != len(trimmer_string):
        raise TrimmingError(f"Invalid characters in trimmer block: '{trimmer_string}'")
    
    for match in matches:
        trimmer_type = match.group(1)
        count = int(match.group(2))
        
        if count == 0:
            raise TrimmingError(f"Trimmer count cannot be zero: {trimmer_type}0")
        
        trimmers.append((trimmer_type, count))
    
    return trimmers


def apply_single_trimmer(content: str, trimmer_type: str, count: int, from_start: bool) -> str:
    """
    Apply a single trimming operation.
    
    Args:
        content: Content to trim
        trimmer_type: 'ch', 'wd', 'ln', or 'nb'
        count: Number of units to trim
        from_start: True for start trimming, False for end trimming
        
    Returns:
        Trimmed content string
        
    Raises:
        TrimmingError: For invalid trimmer types
    """
    if not content:
        return ""
    
    if trimmer_type == 'ch':
        return _trim_characters(content, count, from_start)
    elif trimmer_type == 'wd':
        return _trim_words(content, count, from_start)
    elif trimmer_type == 'ln':
        return _trim_lines(content, count, from_start)
    elif trimmer_type == 'nb':
        return _trim_numbers(content, count, from_start)
    else:
        raise TrimmingError(f"Unknown trimmer type: '{trimmer_type}'")


def _trim_characters(content: str, count: int, from_start: bool) -> str:
    """Trim N characters from start or end."""
    if count >= len(content):
        return ""
    
    if from_start:
        return content[count:]
    else:
        return content[:-count]


def _trim_words(content: str, count: int, from_start: bool) -> str:
    """Trim N words from start or end."""
    words = content.split()
    
    if count >= len(words):
        return ""
    
    if from_start:
        remaining_words = words[count:]
    else:
        remaining_words = words[:-count]
    
    return ' '.join(remaining_words)


def _trim_lines(content: str, count: int, from_start: bool) -> str:
    """Trim N lines from start or end."""
    lines = content.split('\n')
    
    if count >= len(lines):
        return ""
    
    if from_start:
        remaining_lines = lines[count:]
    else:
        remaining_lines = lines[:-count]
    
    return '\n'.join(remaining_lines)


def _trim_numbers(content: str, count: int, from_start: bool) -> str:
    """
    Trim N numbers from start or end.
    
    Numbers are identified as sequences of digits with optional decimal separators.
    When trimming from end, everything from the Nth-from-last number to the end is removed.
    When trimming from start, everything from start through the Nth number is removed.
    """
    if from_start:
        return _trim_numbers_from_start(content, count, NUMBER_DETECTION_RGX)
    else:
        return _trim_numbers_from_end(content, count, NUMBER_DETECTION_RGX)


def _trim_numbers_from_start(content: str, count: int, number_pattern) -> str:
    """Trim N numbers from the start, removing everything up through the Nth number."""
    matches = list(number_pattern.finditer(content))
    
    if count > len(matches):
        return ""  # Not enough numbers to trim
    
    if count == 0:
        return content
    
    # Find position after the Nth number
    nth_match = matches[count - 1]
    trim_to_position = nth_match.end()
    
    return content[trim_to_position:]


def _trim_numbers_from_end(content: str, count: int, number_pattern) -> str:
    """Trim N numbers from the end, removing the Nth-from-last number and everything after it."""
    matches = list(number_pattern.finditer(content))
    
    if count > len(matches):
        return ""  # Not enough numbers to trim
    
    if count == 0:
        return content
    
    # Find position at start of the Nth-from-last number
    # For count=1, we want the last number: matches[-1]
    # For count=2, we want the second-to-last: matches[-2]
    target_match = matches[-count]
    trim_from_position = target_match.start()
    
    return content[:trim_from_position]


def apply_trimmers(content: str, start_trimmers: List[Tuple[str, int]], 
                  end_trimmers: List[Tuple[str, int]]) -> str:
    """
    Apply start and end trimming operations to content.
    
    Args:
        content: Extracted content string
        start_trimmers: List of (type, count) for start trimming
        end_trimmers: List of (type, count) for end trimming
        
    Returns:
        Trimmed content string
        
    Examples:
        >>> apply_trimmers("CompanyNameACME", [('ch', 11)], [('ch', 4)])
        'ACME'
        
        >>> apply_trimmers("OLD REF 2024 001 TEMP", [('wd', 1), ('ch', 4)], [('wd', 1)])
        '2024 001'
    """
    result = content
    
    # Apply start trimmers in sequence
    for trimmer_type, count in start_trimmers:
        result = apply_single_trimmer(result, trimmer_type, count, from_start=True)
        if not result:  # Early exit if trimmed to nothing
            return ""
    
    # Apply end trimmers in sequence
    for trimmer_type, count in end_trimmers:
        result = apply_single_trimmer(result, trimmer_type, count, from_start=False)
        if not result:  # Early exit if trimmed to nothing
            return ""
    
    return result


def validate_trimming_feasibility(content: str, start_trimmers: List[Tuple[str, int]], 
                                end_trimmers: List[Tuple[str, int]]) -> List[str]:
    """
    Check if trimming operations are feasible without over-trimming.
    
    Args:
        content: Content to be trimmed
        start_trimmers: Start trimming operations
        end_trimmers: End trimming operations
        
    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []
    
    if not content:
        if start_trimmers or end_trimmers:
            warnings.append("Cannot trim empty content")
        return warnings
    
    # Quick check for character over-trimming
    start_chars = sum(count for t_type, count in start_trimmers if t_type == 'ch')
    end_chars = sum(count for t_type, count in end_trimmers if t_type == 'ch')
    
    if start_chars + end_chars >= len(content):
        warnings.append(
            f"Character trimming ({start_chars} start + {end_chars} end = "
            f"{start_chars + end_chars}) exceeds content length ({len(content)})"
        )
    
    # Check word over-trimming
    words = content.split()
    start_words = sum(count for t_type, count in start_trimmers if t_type == 'wd')
    end_words = sum(count for t_type, count in end_trimmers if t_type == 'wd')
    
    if start_words + end_words >= len(words):
        warnings.append(
            f"Word trimming ({start_words} start + {end_words} end = "
            f"{start_words + end_words}) exceeds word count ({len(words)})"
        )
    
    # Check line over-trimming
    lines = content.split('\n')
    start_lines = sum(count for t_type, count in start_trimmers if t_type == 'ln')
    end_lines = sum(count for t_type, count in end_trimmers if t_type == 'ln')
    
    if start_lines + end_lines >= len(lines):
        warnings.append(
            f"Line trimming ({start_lines} start + {end_lines} end = "
            f"{start_lines + end_lines}) exceeds line count ({len(lines)})"
        )
    
    return warnings


# End of file #
