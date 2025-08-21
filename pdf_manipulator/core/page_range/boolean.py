"""
Corrected Boolean Expression Processing - No Comma Detection
File: pdf_manipulator/core/page_range/boolean.py

FIXED: Removed comma detection logic since comma parsing now happens at top level.
"""

import re

from pathlib import Path

from pdf_manipulator.core.page_range.page_group import PageGroup


#################################################################################################
# Public API functions

def looks_like_boolean_expression(range_str: str) -> bool:
    """
    Check if string looks like a boolean expression.
    
    FIXED: No comma detection - that happens at parser level now.
    """
    # Check for boolean operators outside quotes
    operators = [' & ', ' | ', '!']
    has_operators = any(op in range_str for op in operators)
    
    if not has_operators:
        # Check for parentheses (also indicates boolean)
        return _has_unquoted_parentheses(range_str)
    
    # Has operators - now validate that operators are not all inside quotes
    return not _all_operators_are_quoted(range_str)


def evaluate_boolean_expression_with_groups(expression: str, pdf_path: Path, 
                                            total_pages: int) -> tuple[list[int], list[PageGroup]]:
    """
    Main entry point for all boolean expression evaluation with group preservation.
    
    Returns:
        Tuple of (all_pages, page_groups) where groups preserve structure
    """
    supervisor = UnifiedBooleanSupervisor(pdf_path, total_pages)
    return supervisor.evaluate(expression)


def parse_boolean_expression(expr: str, pdf_path: Path, total_pages: int) -> list[int]:
    """
    Parse boolean expressions using the unified supervisor.
    
    This handles both simple and advanced expressions with proper group preservation.
    """
    supervisor = UnifiedBooleanSupervisor(pdf_path, total_pages)
    pages, groups = supervisor.evaluate(expr)
    return pages


def has_advanced_patterns(expression: str) -> bool:
    """
    Check if boolean expression contains advanced range patterns.
    """
    supervisor = UnifiedBooleanSupervisor(Path("dummy"), 1)
    patterns = supervisor._extract_advanced_patterns(expression)
    return len(patterns) > 0


#################################################################################################
# Private helper functions

def _has_unquoted_parentheses(text: str) -> bool:
    """Check if text contains parentheses outside quoted strings."""
    in_quote = False
    quote_char = None
    i = 0
    
    while i < len(text):
        char = text[i]
        
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif char in ['(', ')'] and not in_quote:
            return True
        
        i += 1
    
    return False


def _all_operators_are_quoted(text: str) -> bool:
    """Check if ALL boolean operators are inside quoted strings."""
    operators = [' & ', ' | ', '!']
    
    for operator in operators:
        if operator not in text:
            continue
        if _operator_outside_quotes(text, operator):
            return False
    
    return True


def _operator_outside_quotes(text: str, operator: str) -> bool:
    """Check if operator appears outside quoted strings."""
    in_quote = False
    quote_char = None
    i = 0
    
    while i <= len(text) - len(operator):
        char = text[i]
        
        if char == '\\' and i + 1 < len(text):
            i += 2
            continue
        
        if char in ['"', "'"] and not in_quote:
            in_quote = True
            quote_char = char
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif not in_quote:
            if text[i:i+len(operator)] == operator:
                return True
        
        i += 1
    
    return False


#################################################################################################
# UnifiedBooleanSupervisor class

class UnifiedBooleanSupervisor:
    """
    Unified coordinator for ALL boolean expressions - simple and advanced.
    
    Architecture:
    - Simple boolean: Direct processing with precedence rules
    - Advanced (with range patterns): Magazine processing pattern
    - No circular dependencies: Self-contained boolean logic
    
    FIXED: Complete implementation with proper tokenization and boolean logic.
    """
    
    def __init__(self, pdf_path: Path, total_pages: int):
        self.pdf_path = pdf_path
        self.total_pages = total_pages
    
    def evaluate(self, expression: str) -> tuple[list[int], list[PageGroup]]:
        """
        Evaluate ANY boolean expression (simple or advanced).
        
        Returns:
            Tuple of (all_pages, page_groups) where groups preserve structure
        """
        # Check if this is a boolean expression at all
        if not looks_like_boolean_expression(expression):
            # Not a boolean expression - delegate to simple pattern parsing
            pages = self._evaluate_simple_expression(expression)
            groups = self._create_consecutive_groups(pages, expression)
            return pages, groups
        
        # Detect advanced patterns within boolean expression
        advanced_patterns = self._extract_advanced_patterns(expression)
        
        if advanced_patterns:
            # Advanced processing with magazine pattern
            return self._process_with_magazine_pattern(expression, advanced_patterns)
        else:
            # Simple boolean processing with standard precedence
            return self._process_simple_boolean(expression)
    
    def _extract_advanced_patterns(self, expression: str) -> list[str]:
        """Extract any advanced range patterns from the expression."""
        # Look for "X to Y" patterns within the boolean expression
        from pdf_manipulator.core.page_range.patterns import looks_like_range_pattern
        
        patterns = []
        
        # Split by boolean operators to get individual components
        # Then check each component for range patterns
        components = self._split_boolean_components(expression)
        
        for component in components:
            component = component.strip()
            if component and looks_like_range_pattern(component):
                patterns.append(component)
        
        return patterns
    
    def _split_boolean_components(self, expression: str) -> list[str]:
        """Split boolean expression into individual components."""
        # This is a simplified splitter - could be made more sophisticated
        components = []
        current = ""
        in_quote = False
        quote_char = None
        i = 0
        
        while i < len(expression):
            char = expression[i]
            
            if char == '\\' and i + 1 < len(expression):
                current += char + expression[i + 1]
                i += 2
                continue
            
            if char in ['"', "'"] and not in_quote:
                in_quote = True
                quote_char = char
                current += char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
                current += char
            elif not in_quote and char in ['&', '|']:
                # Found operator outside quotes
                if current.strip():
                    components.append(current.strip())
                current = ""
                # Skip the operator and any spaces
                while i + 1 < len(expression) and expression[i + 1] in [' ', '&', '|']:
                    i += 1
            else:
                current += char
            
            i += 1
        
        if current.strip():
            components.append(current.strip())
        
        return components
    
    def _process_with_magazine_pattern(self, expression: str, patterns: list[str]) -> tuple[list[int], list[PageGroup]]:
        """Process expressions with advanced range patterns."""
        # This is a simplified implementation
        # For now, just evaluate as simple boolean
        return self._process_simple_boolean(expression)
    
    def _process_simple_boolean(self, expression: str) -> tuple[list[int], list[PageGroup]]:
        """
        Process simple boolean expressions with proper precedence.
        
        FIXED: Complete implementation with tokenization and precedence handling.
        """
        try:
            # Tokenize the expression
            tokens = self._tokenize_expression(expression)
            
            # Validate parentheses balance
            valid, error_msg = self._validate_parentheses_balance(tokens)
            if not valid:
                raise ValueError(f"Parentheses error: {error_msg}")
            
            # Resolve parentheses recursively
            tokens = self._resolve_parentheses(tokens)
            
            # Evaluate the expression with operator precedence
            result_pages = self._evaluate_with_precedence(tokens)
            
            # Create groups from result
            groups = self._create_consecutive_groups(result_pages, expression)
            
            return result_pages, groups
            
        except Exception as e:
            raise ValueError(f"Failed to parse boolean expression '{expression}': {e}")
    
    def _tokenize_expression(self, expr: str) -> list[str]:
        """
        Tokenize boolean expression into operators and operands.
        
        FIXED: Parentheses are now separate tokens.
        """
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
            elif not in_quote:
                # FIXED: Handle parentheses as separate tokens
                if char == '(':
                    # Save any accumulated token
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    # Add opening parenthesis as separate token
                    tokens.append('(')
                elif char == ')':
                    # Save any accumulated token
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    # Add closing parenthesis as separate token
                    tokens.append(')')
                # Handle operators with exact spacing
                elif expr[i:i+4] == ' & !':
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
        
        # Add final token if any
        if current_token.strip():
            tokens.append(current_token.strip())
        
        return tokens
    
    def _validate_parentheses_balance(self, tokens: list[str]) -> tuple[bool, str]:
        """Validate that parentheses are balanced."""
        stack = []
        for i, token in enumerate(tokens):
            if token == '(':
                stack.append(i)
            elif token == ')':
                if not stack:
                    return False, f"Unmatched closing parenthesis at position {i}"
                stack.pop()
        
        if stack:
            return False, f"Unmatched opening parenthesis at position {stack[0]}"
        
        return True, ""
    
    def _resolve_parentheses(self, tokens: list[str]) -> list[str]:
        """
        Resolve parenthetical expressions recursively.
        
        FIXED: Can now find separate '(' and ')' tokens.
        """
        while '(' in tokens:
            # Find innermost parentheses
            start_idx = -1
            for i, token in enumerate(tokens):
                if token == '(':
                    start_idx = i
                elif token == ')' and start_idx != -1:
                    end_idx = i
                    
                    # Extract sub-expression
                    sub_tokens = tokens[start_idx + 1:end_idx]
                    
                    # Recursively evaluate sub-expression
                    sub_result = self._evaluate_with_precedence(sub_tokens)
                    
                    # Replace parenthetical group with result
                    tokens = tokens[:start_idx] + [sub_result] + tokens[end_idx + 1:]
                    break
        
        return tokens
    
    def _evaluate_with_precedence(self, tokens: list[str]) -> list[int]:
        """
        Evaluate tokens with proper operator precedence.
        
        Precedence: NOT (!) > AND (&) > OR (|)
        """
        if not tokens:
            return []
        
        # If single token (from resolved parentheses), return it
        if len(tokens) == 1:
            token = tokens[0]
            if isinstance(token, list):
                return token
            return self._evaluate_single_token(token)
        
        # Process NOT operators first (highest precedence)
        tokens = self._process_not_operators(tokens)
        
        # Process AND operators next
        tokens = self._process_and_operators(tokens)
        
        # Process OR operators last (lowest precedence)
        tokens = self._process_or_operators(tokens)
        
        # Should have single result
        if len(tokens) == 1:
            result = tokens[0]
            if isinstance(result, list):
                return result
            return self._evaluate_single_token(result)
        
        raise ValueError(f"Could not resolve expression to single result: {tokens}")
    
    def _process_not_operators(self, tokens: list[str]) -> list[str]:
        """Process NOT operators with highest precedence."""
        result = []
        i = 0
        
        while i < len(tokens):
            if tokens[i] == '!' and i + 1 < len(tokens):
                # Apply NOT to next operand
                operand = tokens[i + 1]
                if isinstance(operand, list):
                    operand_pages = operand
                else:
                    operand_pages = self._evaluate_single_token(operand)
                
                # NOT operation: all pages except operand pages
                all_pages = set(range(1, self.total_pages + 1))
                not_pages = list(all_pages - set(operand_pages))
                
                result.append(not_pages)
                i += 2
            elif tokens[i] == '&!' and i + 1 < len(tokens):
                # Handle combined AND NOT
                operand = tokens[i + 1]
                if isinstance(operand, list):
                    operand_pages = operand
                else:
                    operand_pages = self._evaluate_single_token(operand)
                
                # NOT operation: all pages except operand pages
                all_pages = set(range(1, self.total_pages + 1))
                not_pages = list(all_pages - set(operand_pages))
                
                # Insert AND operator and NOT result
                result.append('&')
                result.append(not_pages)
                i += 2
            else:
                result.append(tokens[i])
                i += 1
        
        return result
    
    def _process_and_operators(self, tokens: list[str]) -> list[str]:
        """Process AND operators."""
        while '&' in tokens:
            for i in range(len(tokens)):
                if tokens[i] == '&':
                    if i == 0 or i >= len(tokens) - 1:
                        raise ValueError("AND operator missing operand")
                    
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    
                    # Evaluate operands
                    if isinstance(left, list):
                        left_pages = left
                    else:
                        left_pages = self._evaluate_single_token(left)
                    
                    if isinstance(right, list):
                        right_pages = right
                    else:
                        right_pages = self._evaluate_single_token(right)
                    
                    # AND operation: intersection
                    and_result = list(set(left_pages) & set(right_pages))
                    
                    # Replace the three tokens with result
                    tokens = tokens[:i-1] + [and_result] + tokens[i+2:]
                    break
        
        return tokens
    
    def _process_or_operators(self, tokens: list[str]) -> list[str]:
        """Process OR operators."""
        while '|' in tokens:
            for i in range(len(tokens)):
                if tokens[i] == '|':
                    if i == 0 or i >= len(tokens) - 1:
                        raise ValueError("OR operator missing operand")
                    
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    
                    # Evaluate operands
                    if isinstance(left, list):
                        left_pages = left
                    else:
                        left_pages = self._evaluate_single_token(left)
                    
                    if isinstance(right, list):
                        right_pages = right
                    else:
                        right_pages = self._evaluate_single_token(right)
                    
                    # OR operation: union
                    or_result = list(set(left_pages) | set(right_pages))
                    
                    # Replace the three tokens with result
                    tokens = tokens[:i-1] + [or_result] + tokens[i+2:]
                    break
        
        return tokens
    
    def _evaluate_single_token(self, token: str) -> list[int]:
        """Evaluate a single token (pattern or expression)."""
        try:
            from pdf_manipulator.core.page_range.patterns import parse_pattern_expression, parse_single_expression, looks_like_pattern
            
            if looks_like_pattern(token):
                return parse_pattern_expression(token, self.pdf_path, self.total_pages)
            else:
                return parse_single_expression(token, self.pdf_path, self.total_pages)
        except Exception as e:
            raise ValueError(f"Failed to evaluate token '{token}': {e}")
    
    def _evaluate_simple_expression(self, expression: str) -> list[int]:
        """Evaluate a simple (non-boolean) expression."""
        from pdf_manipulator.core.page_range.patterns import parse_pattern_expression, parse_single_expression
        
        if isinstance(expression, list):
            return expression
        
        # Handle single patterns
        try:
            from pdf_manipulator.core.page_range.patterns import looks_like_pattern
            
            if looks_like_pattern(expression):
                return parse_pattern_expression(expression, self.pdf_path, self.total_pages)
            else:
                # Try as single expression (page numbers, keywords, etc.)
                return parse_single_expression(expression, self.pdf_path, self.total_pages)
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression '{expression}': {e}")
    
    def _create_consecutive_groups(self, pages: list[int], description: str) -> list[PageGroup]:
        """Create consecutive groups from page list."""
        if not pages:
            return []
        
        sorted_pages = sorted(pages)
        groups = []
        current_group = [sorted_pages[0]]
        
        for i in range(1, len(sorted_pages)):
            if sorted_pages[i] == sorted_pages[i-1] + 1:
                current_group.append(sorted_pages[i])
            else:
                # Create group for current consecutive sequence
                groups.append(PageGroup(
                    pages=current_group,
                    is_range=len(current_group) > 1,
                    original_spec=description
                ))
                current_group = [sorted_pages[i]]
        
        # Add the last group
        groups.append(PageGroup(
            pages=current_group,
            is_range=len(current_group) > 1,
            original_spec=description
        ))
        
        return groups


# End of file #
