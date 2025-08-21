"""
Fixed Boolean Expression Processing - API Compatible Version
File: pdf_manipulator/core/page_range/boolean.py

This preserves the existing API while fixing the parentheses tokenization issue.
The key functions that need to be exported are maintained:
- looks_like_boolean_expression()
- evaluate_boolean_expression_with_groups()
"""

import re

from pathlib import Path

from pdf_manipulator.core.page_range.page_group import PageGroup
from pdf_manipulator.core.page_range.patterns import (
    looks_like_range_pattern,
    looks_like_pattern,
    parse_range_pattern_with_groups,
    parse_pattern_expression,
    parse_single_expression,
    parse_range_pattern
)


class UnifiedBooleanSupervisor:
    """
    Unified coordinator for ALL boolean expressions - simple and advanced.
    
    Architecture:
    - Simple boolean: Direct processing with precedence rules
    - Advanced (with range patterns): Magazine processing pattern
    - No circular dependencies: Self-contained boolean logic
    
    FIXED: Parentheses tokenization now works correctly
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
        if not self._looks_like_boolean_expression(expression):
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

    def _looks_like_boolean_expression(self, range_str: str) -> bool:
        """Check if string looks like a boolean expression."""
        # Find boolean operators outside quoted strings with exact spacing
        operators_found = self._find_boolean_operators(range_str)
        
        # Check for parentheses outside quoted strings
        parentheses_found = self._contains_unquoted_parentheses(range_str)
        
        return len(operators_found) > 0 or parentheses_found

    def _contains_unquoted_parentheses(self, text: str) -> bool:
        """Check if text contains parentheses outside quoted strings."""
        in_quote = False
        quote_char = None
        has_open = False
        has_close = False
        
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
            elif not in_quote:
                # Check for parentheses when not in quotes
                if char == '(':
                    has_open = True
                elif char == ')':
                    has_close = True
                    
            i += 1
        
        return has_open and has_close

    def _process_simple_boolean(self, expression: str) -> tuple[list[int], list[PageGroup]]:
        """Process simple boolean expressions (no range patterns)."""
        
        # Tokenize the expression respecting quotes and operators
        tokens = self._tokenize_expression(expression)
        
        # Parse with precedence and grouping using our own logic
        result_pages = self._parse_expression_tokens(tokens)
        
        # Convert to groups (consecutive runs)
        groups = self._create_consecutive_groups(result_pages, expression)
        
        return sorted(list(set(result_pages))), groups
    
    def _extract_advanced_patterns(self, expression: str) -> list[str]:
        """Extract advanced range patterns from boolean expression."""
        tokens = self._tokenize_expression(expression)
        patterns = []
        
        # Check each token for range patterns (handles parenthesized patterns)
        for token in tokens:
            if looks_like_range_pattern(token):
                patterns.append(token)
        
        return patterns
    
    def _process_with_magazine_pattern(self, expression: str, 
                                advanced_patterns: list[str]) -> tuple[list[int], list[PageGroup]]:
        """Process expression using magazine pattern."""
        
        # For now, handle single advanced pattern (Rule 1: only one range criteria)
        if len(advanced_patterns) > 1:
            raise ValueError(
                "Only one range pattern allowed per boolean expression. "
                f"Found {len(advanced_patterns)}: {advanced_patterns}"
            )
        
        # Extract the range pattern
        range_pattern = advanced_patterns[0]
        
        # Parse the range pattern to get logical groups
        _, groups = parse_range_pattern_with_groups(range_pattern, self.pdf_path, self.total_pages)
        
        # Extract all pages from groups
        all_range_pages = []
        for group in groups:
            all_range_pages.extend(group.pages)
        
        # Replace range pattern with dummy in expression
        simplified_expression = expression.replace(range_pattern, "RANGE_PAGES")
        
        # Parse simplified boolean expression
        tokens = self._tokenize_expression(simplified_expression)
        
        # Replace RANGE_PAGES tokens with actual page numbers
        for i, token in enumerate(tokens):
            if token == "RANGE_PAGES":
                tokens[i] = all_range_pages
        
        # Parse with our logic
        result_pages = self._parse_expression_tokens(tokens)
        
        # Return both pages and original groups
        return sorted(list(set(result_pages))), groups

    def _find_boolean_operators(self, text: str) -> list[tuple[str, int]]:
        """Find boolean operators with proper spacing outside quoted strings."""
        operators = []
        i = 0
        in_quote = False
        quote_char = None
        
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
            elif not in_quote:
                # Check for operators with exact spacing
                if text[i:i+4] == ' & !':
                    operators.append(('&!', i))
                    i += 4
                    continue
                elif text[i:i+3] == ' & ':
                    operators.append(('&', i))
                    i += 3
                    continue
                elif text[i:i+3] == ' | ':
                    operators.append(('|', i))
                    i += 3
                    continue
                elif char == '!' and self._is_valid_not_position(text, i):
                    operators.append(('!', i))
            
            i += 1
        
        return operators
    
    def _is_valid_not_position(self, text: str, pos: int) -> bool:
        """Check if ! at given position is a valid standalone NOT operator with proper context."""
        # Must be at start
        if pos == 0:
            return True
        
        # Check what comes before the !
        prev_char = text[pos-1]
        
        # Valid after opening parenthesis
        if prev_char == '(':
            return True
            
        # Valid after proper boolean operators (must have exact spacing)
        if pos >= 3 and text[pos-3:pos] == ' & ':
            return True
        if pos >= 3 and text[pos-3:pos] == ' | ':
            return True
            
        return False

    def _tokenize_expression(self, expr: str) -> list[str]:
        """
        FIXED: Tokenize expression with separate parenthesis tokens.
        
        This fixes the core issue where parentheses were being captured as
        atomic tokens instead of separate tokens that _resolve_parentheses expects.
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
                # Inside quotes - accumulate everything as part of current token
                current_token += char
            
            i += 1
        
        # Add final token if any
        if current_token.strip():
            tokens.append(current_token.strip())
        
        return [token for token in tokens if token]
    
    def _parse_expression_tokens(self, tokens: list[str]) -> list[int]:
        """Parse tokenized expression with precedence: () > ! > & > |"""
        if not tokens:
            return []
        
        # Validate first token isn't a binary operator
        if tokens[0] in ['&', '|', '&!']:
            op_name = {'&': 'AND', '|': 'OR', '&!': 'AND NOT'}[tokens[0]]
            raise ValueError(f"{op_name} operator '{tokens[0]}' missing left operand")
        
        # Validate parentheses are balanced
        paren_count = 0
        for token in tokens:
            if token == '(':
                paren_count += 1
            elif token == ')':
                paren_count -= 1
            if paren_count < 0:
                raise ValueError("Mismatched parentheses: ')' without '('")
        if paren_count > 0:
            raise ValueError("Mismatched parentheses: '(' without ')'")
        
        # Handle parentheses first (highest precedence)
        tokens = self._resolve_parentheses(tokens)
        
        # Handle NOT operators (second highest precedence)
        tokens = self._resolve_not_operators(tokens)
        
        # Handle AND operators (third precedence)
        tokens = self._resolve_and_operators(tokens)
        
        # Handle OR operators (lowest precedence)
        tokens = self._resolve_or_operators(tokens)
        
        # Should be left with a single result
        if len(tokens) == 1 and isinstance(tokens[0], list):
            return tokens[0]
        else:
            raise ValueError(f"Failed to parse boolean expression: {tokens}")
    
    def _resolve_parentheses(self, tokens: list) -> list:
        """
        FIXED: Resolve parenthetical expressions with separate ( and ) tokens.
        
        Now works correctly with the new tokenization strategy.
        """
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
                    sub_result = self._parse_expression_tokens(sub_expr)
                    
                    # Replace parenthetical expression with result
                    tokens = tokens[:start] + [sub_result] + tokens[i+1:]
                    break
            else:
                if start != -1:
                    raise ValueError("Mismatched parentheses: '(' without ')'")
        
        return tokens
    
    def _resolve_not_operators(self, tokens: list) -> list:
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
                    all_pages = set(range(1, self.total_pages + 1))
                    not_result = list(all_pages - set(operand))
                else:
                    # NOT of a single expression
                    operand_pages = self._evaluate_simple_expression(operand)
                    all_pages = set(range(1, self.total_pages + 1))
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
                
                # Evaluate left operand if it's still a string
                if isinstance(left_operand, list):
                    left_pages = left_operand
                else:
                    left_pages = self._evaluate_simple_expression(left_operand)
                
                if isinstance(right_operand, list):
                    right_pages = right_operand
                else:
                    right_pages = self._evaluate_simple_expression(right_operand)
                
                # AND with NOT: left & !right
                and_not_result = list(set(left_pages) - set(right_pages))
                result[-1] = and_not_result  # Replace last result
                i += 2  # Skip the operand
            else:
                result.append(tokens[i])
                i += 1
        
        return result

    def _resolve_and_operators(self, tokens: list) -> list:
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
                    left_pages = self._evaluate_simple_expression(left_operand)
                
                if isinstance(right_operand, list):
                    right_pages = right_operand
                else:
                    right_pages = self._evaluate_simple_expression(right_operand)
                
                # AND operation
                and_result = list(set(left_pages) & set(right_pages))
                result[-1] = and_result  # Replace last result
                i += 2  # Skip the operand
            else:
                result.append(tokens[i])
                i += 1
        
        return result
    
    def _resolve_or_operators(self, tokens: list) -> list:
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
                    left_pages = self._evaluate_simple_expression(left_operand)
                
                if isinstance(right_operand, list):
                    right_pages = right_operand
                else:
                    right_pages = self._evaluate_simple_expression(right_operand)
                
                # OR operation
                or_result = list(set(left_pages) | set(right_pages))
                result[-1] = or_result  # Replace last result
                i += 2  # Skip the operand
            else:
                result.append(tokens[i])
                i += 1
        
        return result

    def _evaluate_simple_expression(self, expression: str) -> list[int]:
        """Evaluate a simple expression (no boolean operators)."""
        if isinstance(expression, list):
            return expression
        
        # Handle single patterns
        try:
            if looks_like_pattern(expression):
                return parse_pattern_expression(expression, self.pdf_path)
            else:
                # Try as single expression (page numbers, keywords, etc.)
                return parse_single_expression(expression, self.total_pages)
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression '{expression}': {e}")
    
    def _create_consecutive_groups(self, pages: list[int], description: str) -> list[PageGroup]:
        """Create consecutive groups from page list."""
        if not pages:
            return []
        
        # Sort pages to find consecutive runs
        sorted_pages = sorted(pages)
        groups = []
        current_group = [sorted_pages[0]]
        
        for i in range(1, len(sorted_pages)):
            if sorted_pages[i] == sorted_pages[i-1] + 1:
                # Consecutive page
                current_group.append(sorted_pages[i])
            else:
                # Gap found - create group for current run
                groups.append(PageGroup(
                    pages=current_group.copy(),
                    description=f"{description} (pages {current_group[0]}-{current_group[-1]})" 
                               if len(current_group) > 1 
                               else f"{description} (page {current_group[0]})"
                ))
                current_group = [sorted_pages[i]]
        
        # Add final group
        groups.append(PageGroup(
            pages=current_group.copy(),
            description=f"{description} (pages {current_group[0]}-{current_group[-1]})" 
                       if len(current_group) > 1 
                       else f"{description} (page {current_group[0]})"
        ))
        
        return groups


# ============================================================================
# PUBLIC API FUNCTIONS - These maintain the existing interface
# ============================================================================

def looks_like_boolean_expression(range_str: str) -> bool:
    """Check if string looks like a boolean expression."""
    # Create temporary supervisor for detection
    supervisor = UnifiedBooleanSupervisor(Path("dummy"), 1)
    return supervisor._looks_like_boolean_expression(range_str)


def parse_boolean_expression(expr: str, pdf_path, total_pages) -> list[int]:
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
    
    This is just a wrapper around the real detection logic.
    """
    supervisor = UnifiedBooleanSupervisor(Path("dummy"), 1)
    patterns = supervisor._extract_advanced_patterns(expression)
    return len(patterns) > 0


def evaluate_boolean_expression_with_groups(expression: str, pdf_path: Path, 
                                            total_pages: int) -> tuple[list[int], list[PageGroup]]:
    """
    Main entry point for all boolean expression evaluation with group preservation.
    
    This is the function that the existing code expects to import.
    """
    supervisor = UnifiedBooleanSupervisor(pdf_path, total_pages)
    return supervisor.evaluate(expression)


# End of file #
