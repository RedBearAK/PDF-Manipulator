"""
Robust boolean expression parser with quote awareness, strict spacing, and parentheses.
Replace: pdf_manipulator/core/page_range/boolean.py
"""

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
    """Check if string looks like a boolean expression with proper spacing and quote awareness."""
    
    # Find boolean operators outside quoted strings with exact spacing
    operators_found = _find_boolean_operators(range_str)
    parentheses_found = '(' in range_str and ')' in range_str
    
    return len(operators_found) > 0 or parentheses_found


def parse_boolean_expression(expr: str, pdf_path, total_pages) -> list[int]:
    """
    Parse boolean expressions with proper precedence, grouping, and quote awareness.
    
    Supported operators (in precedence order):
    1. () - Parentheses (highest precedence)
    2. ! - NOT  
    3. & - AND
    4. | - OR (lowest precedence)
    
    Examples:
    - contains:'Invoice' & contains:'Total'        (AND)
    - contains:'Bill' | contains:'Invoice'         (OR) 
    - all & !contains:'DRAFT'                      (NOT)
    - (type:text | type:mixed) & size:<500KB       (Grouping)
    """
    
    # Tokenize the expression respecting quotes and operators
    tokens = _tokenize_expression(expr)
    
    # Parse with precedence and grouping
    result_pages = _parse_expression_tokens(tokens, pdf_path, total_pages)
    
    return sorted(list(set(result_pages)))


#################################################################################################
# Private helper functions


def _find_boolean_operators(text: str) -> list[tuple[str, int]]:
    """Find boolean operators outside quoted strings with strict spacing validation."""
    
    operators = []
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle escapes (skip escaped characters)
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        # Handle quotes
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        
        # Check for operators when not in quotes
        elif not in_quote:
            # Must have exact spacing: " & ", " | ", " & !"
            if text[i:i+3] == ' & ':
                # Verify no extra spaces
                if (i == 0 or text[i-1] != ' ') and (i+3 >= len(text) or text[i+3] != ' '):
                    operators.append(('&', i))
                    i += 3
                    continue
            elif text[i:i+3] == ' | ':
                # Verify no extra spaces  
                if (i == 0 or text[i-1] != ' ') and (i+3 >= len(text) or text[i+3] != ' '):
                    operators.append(('|', i))
                    i += 3
                    continue
            elif text[i:i+4] == ' & !':
                # Verify no extra spaces
                if (i == 0 or text[i-1] != ' ') and (i+4 >= len(text) or text[i+4] != ' '):
                    operators.append(('&!', i))
                    i += 4
                    continue
            elif char == '!' and (i == 0 or text[i-1].isspace()):
                # Standalone NOT at beginning or after whitespace
                operators.append(('!', i))
        
        i += 1
    
    return operators


def _tokenize_expression(expr: str) -> list[str]:
    """Tokenize expression into operators, operands, and parentheses."""
    
    tokens = []
    current_token = ""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(expr):
        char = expr[i]
        
        # Handle escapes
        if char == '\\' and i + 1 < len(expr):
            current_token += char + expr[i + 1]
            i += 2
            continue
        
        # Handle quotes
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
            current_token += char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current_token += char
        
        # Handle tokens when not in quotes
        elif not in_quote:
            # Check for boolean operators with exact spacing
            if expr[i:i+4] == ' & !':
                if current_token.strip():
                    tokens.append(current_token.strip())
                tokens.append('&!')
                current_token = ""
                i += 4
                continue
            elif expr[i:i+3] == ' & ':
                if current_token.strip():
                    tokens.append(current_token.strip())
                tokens.append('&')
                current_token = ""
                i += 3
                continue
            elif expr[i:i+3] == ' | ':
                if current_token.strip():
                    tokens.append(current_token.strip())
                tokens.append('|')
                current_token = ""
                i += 3
                continue
            # Handle parentheses
            elif char in '()':
                if current_token.strip():
                    tokens.append(current_token.strip())
                tokens.append(char)
                current_token = ""
            # Handle standalone NOT
            elif char == '!' and (i == 0 or expr[i-1].isspace()):
                if current_token.strip():
                    tokens.append(current_token.strip())
                tokens.append('!')
                current_token = ""
            else:
                current_token += char
        else:
            current_token += char
        
        i += 1
    
    if current_token.strip():
        tokens.append(current_token.strip())
    
    return [token for token in tokens if token]  # Remove empty tokens


def _parse_expression_tokens(tokens: list[str], pdf_path, total_pages) -> list[int]:
    """Parse tokenized expression with precedence: () > ! > & > |"""
    
    if not tokens:
        return []
    
    # Handle parentheses first (highest precedence)
    tokens = _resolve_parentheses(tokens, pdf_path, total_pages)
    
    # Handle NOT operators (second highest precedence)
    tokens = _resolve_not_operators(tokens, pdf_path, total_pages)
    
    # Handle AND operators (third precedence)
    tokens = _resolve_and_operators(tokens, pdf_path, total_pages)
    
    # Handle OR operators (lowest precedence)
    tokens = _resolve_or_operators(tokens, pdf_path, total_pages)
    
    # Should be left with a single result
    if len(tokens) == 1 and isinstance(tokens[0], list):
        return tokens[0]
    else:
        raise ValueError(f"Failed to parse boolean expression: {tokens}")


def _resolve_parentheses(tokens: list, pdf_path, total_pages) -> list:
    """Resolve parenthetical expressions."""
    
    while '(' in tokens:
        # Find innermost parentheses
        start = -1
        for i, token in enumerate(tokens):
            if token == '(':
                start = i
            elif token == ')':
                if start == -1:
                    raise ValueError("Mismatched parentheses: ')' without '('")
                
                # Extract and evaluate the parenthetical expression
                sub_expr = tokens[start+1:i]
                sub_result = _parse_expression_tokens(sub_expr, pdf_path, total_pages)
                
                # Replace parenthetical expression with result
                tokens = tokens[:start] + [sub_result] + tokens[i+1:]
                break
        else:
            if start != -1:
                raise ValueError("Mismatched parentheses: '(' without ')'")
    
    return tokens


def _resolve_not_operators(tokens: list, pdf_path, total_pages) -> list:
    """Resolve NOT operators."""
    
    result = []
    i = 0
    
    while i < len(tokens):
        if tokens[i] == '!':
            if i + 1 >= len(tokens):
                raise ValueError("NOT operator '!' missing operand")
            
            operand = tokens[i + 1]
            if isinstance(operand, list):
                # NOT of a sub-expression result
                all_pages = set(range(1, total_pages + 1))
                not_result = list(all_pages - set(operand))
            else:
                # NOT of a single expression
                operand_pages = _evaluate_single_expression(operand, pdf_path, total_pages)
                all_pages = set(range(1, total_pages + 1))
                not_result = list(all_pages - set(operand_pages))
            
            result.append(not_result)
            i += 2  # Skip the operand
        elif tokens[i] == '&!':
            # Handle " & !" as a compound operator
            if not result:
                raise ValueError("'&!' operator missing left operand")
            if i + 1 >= len(tokens):
                raise ValueError("'&!' operator missing right operand")
            
            left_operand = result[-1]
            right_operand = tokens[i + 1]
            
            if isinstance(right_operand, list):
                right_pages = right_operand
            else:
                right_pages = _evaluate_single_expression(right_operand, pdf_path, total_pages)
            
            # AND with NOT: left & !right
            and_not_result = list(set(left_operand) - set(right_pages))
            result[-1] = and_not_result  # Replace last result
            i += 2  # Skip the operand
        else:
            result.append(tokens[i])
            i += 1
    
    return result


def _resolve_and_operators(tokens: list, pdf_path, total_pages) -> list:
    """Resolve AND operators."""
    
    result = []
    i = 0
    
    while i < len(tokens):
        if tokens[i] == '&':
            if not result:
                raise ValueError("AND operator '&' missing left operand")
            if i + 1 >= len(tokens):
                raise ValueError("AND operator '&' missing right operand")
            
            left_operand = result[-1]
            right_operand = tokens[i + 1]
            
            # Evaluate operands
            if isinstance(left_operand, list):
                left_pages = left_operand
            else:
                left_pages = _evaluate_single_expression(left_operand, pdf_path, total_pages)
            
            if isinstance(right_operand, list):
                right_pages = right_operand
            else:
                right_pages = _evaluate_single_expression(right_operand, pdf_path, total_pages)
            
            # AND operation
            and_result = list(set(left_pages) & set(right_pages))
            result[-1] = and_result  # Replace last result
            i += 2  # Skip the operand
        else:
            result.append(tokens[i])
            i += 1
    
    return result


def _resolve_or_operators(tokens: list, pdf_path, total_pages) -> list:
    """Resolve OR operators."""
    
    result = []
    i = 0
    
    while i < len(tokens):
        if tokens[i] == '|':
            if not result:
                raise ValueError("OR operator '|' missing left operand")
            if i + 1 >= len(tokens):
                raise ValueError("OR operator '|' missing right operand")
            
            left_operand = result[-1]
            right_operand = tokens[i + 1]
            
            # Evaluate operands
            if isinstance(left_operand, list):
                left_pages = left_operand
            else:
                left_pages = _evaluate_single_expression(left_operand, pdf_path, total_pages)
            
            if isinstance(right_operand, list):
                right_pages = right_operand
            else:
                right_pages = _evaluate_single_expression(right_operand, pdf_path, total_pages)
            
            # OR operation
            or_result = list(set(left_pages) | set(right_pages))
            result[-1] = or_result  # Replace last result
            i += 2  # Skip the operand
        else:
            result.append(tokens[i])
            i += 1
    
    return result


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
