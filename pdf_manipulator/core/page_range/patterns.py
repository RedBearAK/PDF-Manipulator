"""
Fixed Pattern Detection for Comma-Separated Lists
File: pdf_manipulator/core/page_range/patterns.py

Add this fix to the looks_like_pattern function to prevent comma-separated 
lists from being misidentified as single patterns.
"""

def looks_like_pattern(range_str: str) -> bool:
    """
    Check if string looks like a pattern expression.
    
    FIXED: Don't treat comma-separated lists as single patterns.
    """
    # FIXED: Don't treat comma-separated lists as single patterns
    # If this looks like a comma-separated list, let comma parsing handle it
    if _looks_like_comma_separated_list_pattern(range_str):
        return False
    
    # Original pattern detection logic
    return any([
        range_str.startswith(('contains', 'regex', 'line-starts', 'type', 'size')),
        ':' in range_str and any(range_str.lower().startswith(p) for p in ['contains', 'regex', 'line-starts', 'type', 'size']),
    ])


def _looks_like_comma_separated_list_pattern(range_str: str) -> bool:
    """
    Check if string looks like a comma-separated list that starts with a pattern.
    
    This prevents comma-separated lists from being misidentified as single patterns.
    """
    if ',' not in range_str:
        return False
    
    # Split by comma and check if we have multiple distinct expressions
    parts = [p.strip() for p in range_str.split(',')]
    
    # Need at least 2 parts to be a list
    if len(parts) < 2:
        return False
    
    # If first part looks like a pattern but we have more parts, it's probably a list
    first_part = parts[0]
    if _is_individual_pattern(first_part):
        # Check if other parts also look like valid individual expressions
        valid_expressions = 0
        for part in parts[1:]:  # Skip first part
            if _is_individual_expression_pattern(part):
                valid_expressions += 1
        
        # If we have multiple valid expressions, treat as comma-separated
        return valid_expressions >= 1
    
    return False


def _is_individual_pattern(expr: str) -> bool:
    """Check if expression looks like an individual pattern (not comma-separated)."""
    expr = expr.strip()
    
    # Pattern expressions (contains:, type:, etc.) without commas
    if ':' in expr and ',' not in expr:
        return any(expr.lower().startswith(p) for p in ['contains', 'type', 'size', 'regex', 'line-starts'])
    
    return False


def _is_individual_expression_pattern(expr: str) -> bool:
    """Check if expression looks like an individual expression for pattern context."""
    expr = expr.strip()
    
    # Numeric specifications
    if expr.isdigit():
        return True
    if '-' in expr and not expr.startswith('-') and not expr.endswith('-'):
        try:
            parts = expr.split('-', 1)
            int(parts[0])
            int(parts[1])
            return True
        except ValueError:
            pass
    
    # Special keywords
    if expr.lower() in ['all']:
        return True
    
    # Pattern expressions (contains:, type:, etc.)
    if ':' in expr and any(expr.lower().startswith(p) for p in ['contains', 'type', 'size', 'regex']):
        return True
    
    # Boolean expressions (but without commas)
    if ('&' in expr or '|' in expr or expr.startswith('!')) and ',' not in expr:
        return True
    
    # Range expressions (first, last, etc.)
    if any(expr.lower().startswith(w) for w in ['first', 'last']):
        return True
    
    return False


# End of file #
