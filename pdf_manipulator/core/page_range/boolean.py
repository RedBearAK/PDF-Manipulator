
from pdf_manipulator.core.page_range.patterns import (
    looks_like_pattern,
    looks_like_range_pattern,
    parse_pattern_expression, 
    parse_range_pattern,
    parse_single_expression
)


#################################################################################################
# Public API functions


def looks_like_boolean_expression(range_str: str) -> bool:
    """Check if string looks like a boolean expression."""
    return any([
        ' & ' in range_str,
        ' | ' in range_str, 
        range_str.startswith('!'),
        ' & !' in range_str
    ])


def parse_boolean_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """
    Parse boolean expressions with AND (&), OR (,), and NOT (!) logic.
    
    Examples:
    - contains:'Invoice' & contains:'Total'        (AND)
    - contains:'Bill', contains:'Invoice'          (OR) 
    - all & !contains:'DRAFT'                      (NOT)
    """
    
    # Handle NOT operations first (highest precedence)
    if '!' in expr:
        return _parse_not_expression(expr, pdf_path, total_pages)
    
    # Handle AND operations (medium precedence)
    if ' & ' in expr:
        return _parse_and_expression(expr, pdf_path, total_pages)
    
    # Handle OR operations (lowest precedence)
    if ' | ' in expr:
        return _parse_or_expression(expr, pdf_path, total_pages)
    
    # Single expression - shouldn't reach here normally
    return _evaluate_single_expression(expr, pdf_path, total_pages)


#################################################################################################
# Private helper functions (used inside module only)


def _evaluate_single_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """Evaluate a single expression (no boolean operators)."""
    
    expr = expr.strip()
    
    # Handle 'all' keyword
    if expr.lower() == 'all':
        return list(range(1, total_pages + 1))
    
    # Handle existing range patterns
    if looks_like_range_pattern(expr):
        return parse_range_pattern(expr, pdf_path, total_pages)
    
    # Handle existing single patterns
    if looks_like_pattern(expr):
        return parse_pattern_expression(expr, pdf_path, total_pages)
    
    # Handle single expression (number, range, etc.)
    return parse_single_expression(expr, pdf_path, total_pages)


def _parse_not_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """Parse NOT expressions: 'all & !contains:DRAFT'"""
    
    # Split on & to find the positive and negative parts
    if ' & !' in expr:
        positive_part, negative_part = expr.split(' & !', 1)
        
        # Get pages from positive expression
        positive_pages = set(_evaluate_single_expression(positive_part.strip(), pdf_path, total_pages))
        
        # Get pages from negative expression
        negative_pages = set(_evaluate_single_expression(negative_part.strip(), pdf_path, total_pages))
        
        # Return positive minus negative
        result_pages = positive_pages - negative_pages
        return sorted(list(result_pages))
    
    # Simple NOT: !contains:'text'
    elif expr.startswith('!'):
        all_pages = set(range(1, total_pages + 1))
        negative_pages = set(_evaluate_single_expression(expr[1:].strip(), pdf_path, total_pages))
        result_pages = all_pages - negative_pages
        return sorted(list(result_pages))
    
    else:
        raise ValueError(f"Invalid NOT expression: {expr}")


def _parse_and_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """Parse AND expressions: 'contains:Invoice & contains:Total'"""
    
    parts = [part.strip() for part in expr.split(' & ')]
    
    if len(parts) < 2:
        raise ValueError(f"AND expression must have at least 2 parts: {expr}")
    
    # Start with first expression's results
    result_pages = set(_evaluate_single_expression(parts[0], pdf_path, total_pages))
    
    # Intersect with each subsequent expression
    for part in parts[1:]:
        if part.startswith('!'):
            # Handle NOT within AND
            not_pages = set(_evaluate_single_expression(part[1:], pdf_path, total_pages))
            result_pages = result_pages - not_pages
        else:
            part_pages = set(_evaluate_single_expression(part, pdf_path, total_pages))
            result_pages = result_pages & part_pages
    
    return sorted(list(result_pages))


def _parse_or_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """Parse OR expressions: 'contains:Bill | contains:Invoice'"""
    
    parts = [part.strip() for part in expr.split(' | ')]
    
    result_pages = set()
    
    # Union all expressions
    for part in parts:
        part_pages = set(_evaluate_single_expression(part, pdf_path, total_pages))
        result_pages = result_pages | part_pages
    
    return sorted(list(result_pages))

