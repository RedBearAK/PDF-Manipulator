"""
Enhanced Boolean Expression Processing - Comma-Free Architecture
File: pdf_manipulator/core/page_range/boolean.py

FIXED: Removed comma detection logic since comma parsing now happens at top level.
Enhanced to handle complex nested boolean expressions with proper tokenization.

Architecture:
- Fixed tokenization: parentheses and operators as separate tokens
- Proper quote handling: operators inside quotes don't count as boolean operators
- Boolean precedence: parentheses → NOT → AND → OR
- Complex expression support: unlimited nesting and chaining
- Pattern integration: works with pattern matching functions
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.core.page_range.page_group import PageGroup

console = Console()


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
        
        # Handle escapes
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
        
        # Handle escapes
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
    
    FIXED: Complete implementation with proper tokenization and boolean logic.
    
    Features:
    - Fixed tokenization: parentheses and operators as separate tokens
    - Boolean precedence: parentheses → NOT → AND → OR
    - Complex nested expressions: unlimited depth and complexity
    - Quote-aware parsing: operators inside quotes ignored
    - Pattern integration: seamless work with pattern matching
    - Advanced patterns: handles range patterns within boolean expressions
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
    
    def _process_simple_boolean(self, expression: str) -> tuple[list[int], list[PageGroup]]:
        """Process simple boolean expressions without advanced range patterns."""
        try:
            # Tokenize the expression with fixed tokenization
            tokens = self._tokenize_expression(expression)
            
            # Validate parentheses balance
            self._validate_parentheses_balance(tokens)
            
            # Evaluate the expression with proper precedence
            result_pages = self._evaluate_boolean_tokens(tokens)
            
            # Create groups preserving the boolean structure
            groups = self._create_boolean_groups(result_pages, expression)
            
            return result_pages, groups
            
        except Exception as e:
            raise ValueError(f"Failed to parse boolean expression '{expression}': {e}")
    
    def _tokenize_expression(self, expr: str) -> list[str]:
        """
        Tokenize boolean expression with FIXED parentheses handling.
        
        CRITICAL FIX: Parentheses become separate tokens instead of being bundled.
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
                # CRITICAL FIX: Handle parentheses as separate tokens
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
                # Handle operators with proper spacing
                elif expr[i:i+3] == ' & ':
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    tokens.append('&')
                    i += 2  # Skip the ' & ' (we'll advance i again at end of loop)
                elif expr[i:i+3] == ' | ':
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    tokens.append('|')
                    i += 2  # Skip the ' | '
                elif char == '!' and (i == 0 or expr[i-1] in [' ', '(', '&', '|']):
                    # NOT operator at start of expression, after space, or after operator/parenthesis
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    tokens.append('!')
                else:
                    current_token += char
            else:
                # Inside quotes - just accumulate
                current_token += char
            
            i += 1
        
        # Add final token
        if current_token.strip():
            tokens.append(current_token.strip())
        
        return tokens
    
    def _validate_parentheses_balance(self, tokens: list[str]) -> None:
        """Validate that parentheses are properly balanced."""
        open_count = 0
        for token in tokens:
            if token == '(':
                open_count += 1
            elif token == ')':
                open_count -= 1
                if open_count < 0:
                    raise ValueError("Unbalanced parentheses: unexpected closing parenthesis")
        
        if open_count > 0:
            raise ValueError("Unbalanced parentheses: missing closing parenthesis")
    
    def _evaluate_boolean_tokens(self, tokens: list[str]) -> list[int]:
        """
        Evaluate boolean tokens with proper precedence.
        
        Precedence order: parentheses → NOT → AND → OR
        """
        # Make a copy to avoid modifying the original
        tokens = tokens.copy()
        
        # Step 1: Resolve parentheses first (highest precedence)
        tokens = self._resolve_parentheses(tokens)
        
        # Step 2: Resolve NOT operators (second highest precedence)
        tokens = self._resolve_not_operators(tokens)
        
        # Step 3: Resolve AND operators (third precedence)
        tokens = self._resolve_and_operators(tokens)
        
        # Step 4: Resolve OR operators (lowest precedence)
        tokens = self._resolve_or_operators(tokens)
        
        # Should have exactly one result
        if len(tokens) != 1:
            raise ValueError(f"Invalid boolean expression: unexpected tokens remaining: {tokens}")
        
        result = tokens[0]
        if isinstance(result, list):
            return result
        else:
            # Single pattern/token - evaluate it
            return self._evaluate_single_pattern(result)
    
    def _resolve_parentheses(self, tokens: list[str]) -> list[str]:
        """Resolve parentheses groups recursively."""
        while '(' in tokens and ')' in tokens:
            # Find the innermost parentheses group
            open_pos = -1
            for i, token in enumerate(tokens):
                if token == '(':
                    open_pos = i
                elif token == ')':
                    if open_pos == -1:
                        raise ValueError("Unbalanced parentheses: unexpected closing parenthesis")
                    
                    # Extract content between parentheses
                    sub_tokens = tokens[open_pos + 1:i]
                    
                    # Recursively evaluate the sub-expression
                    sub_result = self._evaluate_boolean_tokens(sub_tokens)
                    
                    # Replace the parentheses group with the result
                    tokens = tokens[:open_pos] + [sub_result] + tokens[i + 1:]
                    break
            else:
                # No closing parenthesis found
                raise ValueError("Unbalanced parentheses: missing closing parenthesis")
        
        return tokens
    
    def _resolve_not_operators(self, tokens: list[str]) -> list[str]:
        """Resolve NOT operators (right-associative)."""
        # Process NOT operators from right to left
        i = len(tokens) - 1
        while i >= 0:
            if tokens[i] == '!':
                if i >= len(tokens) - 1:
                    raise ValueError("NOT operator missing operand")
                
                operand = tokens[i + 1]
                
                # Evaluate operand if needed
                if isinstance(operand, list):
                    operand_pages = operand
                else:
                    operand_pages = self._evaluate_single_pattern(operand)
                
                # NOT operation: complement against all pages
                all_pages = set(range(1, self.total_pages + 1))
                not_result = list(all_pages - set(operand_pages))
                
                # Replace NOT operator and operand with result
                tokens = tokens[:i] + [not_result] + tokens[i + 2:]
            else:
                i -= 1
        
        return tokens
    
    def _resolve_and_operators(self, tokens: list[str]) -> list[str]:
        """Resolve AND operators (left-associative)."""
        while '&' in tokens:
            and_pos = tokens.index('&')
            
            if and_pos == 0 or and_pos >= len(tokens) - 1:
                raise ValueError("AND operator missing operand")
            
            left = tokens[and_pos - 1]
            right = tokens[and_pos + 1]
            
            # Evaluate operands if needed
            if isinstance(left, list):
                left_pages = left
            else:
                left_pages = self._evaluate_single_pattern(left)
            
            if isinstance(right, list):
                right_pages = right
            else:
                right_pages = self._evaluate_single_pattern(right)
            
            # AND operation: intersection
            and_result = list(set(left_pages) & set(right_pages))
            
            # Replace the three tokens with result
            tokens = tokens[:and_pos - 1] + [and_result] + tokens[and_pos + 2:]
        
        return tokens
    
    def _resolve_or_operators(self, tokens: list[str]) -> list[str]:
        """Resolve OR operators (left-associative)."""
        while '|' in tokens:
            or_pos = tokens.index('|')
            
            if or_pos == 0 or or_pos >= len(tokens) - 1:
                raise ValueError("OR operator missing operand")
            
            left = tokens[or_pos - 1]
            right = tokens[or_pos + 1]
            
            # Evaluate operands if needed
            if isinstance(left, list):
                left_pages = left
            else:
                left_pages = self._evaluate_single_pattern(left)
            
            if isinstance(right, list):
                right_pages = right
            else:
                right_pages = self._evaluate_single_pattern(right)
            
            # OR operation: union (automatically removes duplicates)
            or_result = list(set(left_pages) | set(right_pages))
            
            # Replace the three tokens with result
            tokens = tokens[:or_pos - 1] + [or_result] + tokens[or_pos + 2:]
        
        return tokens
    
    def _evaluate_single_pattern(self, pattern: str) -> list[int]:
        """Evaluate a single pattern and return matching page numbers."""
        from pdf_manipulator.core.page_range.patterns import parse_pattern_expression
        
        try:
            return parse_pattern_expression(pattern, self.pdf_path, self.total_pages)
        except Exception as e:
            raise ValueError(f"Failed to evaluate pattern '{pattern}': {e}")
    
    def _evaluate_simple_expression(self, expression: str) -> list[int]:
        """Evaluate a simple (non-boolean) expression."""
        # Handle special keywords
        if expression.lower().strip() == 'all':
            return list(range(1, self.total_pages + 1))
        
        # Try as a pattern
        try:
            return self._evaluate_single_pattern(expression)
        except Exception:
            # If pattern fails, try as numeric range
            # This would need numeric range parsing logic
            raise ValueError(f"Could not evaluate expression: '{expression}'")
    
    def _create_consecutive_groups(self, pages: list[int], expression: str) -> list[PageGroup]:
        """Create PageGroup objects for simple expressions."""
        if not pages:
            return []
        
        # Create a single group for the result
        group = PageGroup(pages, len(pages) > 1, expression)
        return [group]
    
    def _create_boolean_groups(self, pages: list[int], expression: str) -> list[PageGroup]:
        """Create PageGroup objects for boolean expressions."""
        if not pages:
            return []
        
        # For boolean expressions, create a single group marked as boolean
        group = PageGroup(pages, len(pages) > 1, expression)
        group.is_boolean = True
        return [group]
    
    def _extract_advanced_patterns(self, expression: str) -> list[str]:
        """Extract any advanced range patterns from the expression."""
        # Look for "X to Y" patterns within the boolean expression
        from pdf_manipulator.core.page_range.patterns import looks_like_range_pattern
        
        patterns = []
        
        # Split by boolean operators to get individual components
        components = self._split_boolean_components(expression)
        
        for component in components:
            component = component.strip()
            if component and looks_like_range_pattern(component):
                patterns.append(component)
        
        return patterns
    
    def _split_boolean_components(self, expression: str) -> list[str]:
        """Split boolean expression into individual components."""
        # Simple splitting for advanced pattern detection
        # This doesn't need to be as sophisticated as full tokenization
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
                # Found a top-level operator
                if current.strip():
                    components.append(current.strip())
                current = ""
                # Skip any surrounding spaces
                while i + 1 < len(expression) and expression[i + 1] == ' ':
                    i += 1
            else:
                current += char
            
            i += 1
        
        if current.strip():
            components.append(current.strip())
        
        return components
    
    def _process_with_magazine_pattern(self, expression: str, advanced_patterns: list[str]) -> tuple[list[int], list[PageGroup]]:
        """Process advanced boolean expressions containing range patterns."""
        # For now, delegate to simple processing
        # Advanced magazine pattern processing can be implemented later
        return self._process_simple_boolean(expression)


# End of file #
