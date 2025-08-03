"""
Unified Boolean Expression Processing
Replace: pdf_manipulator/core/page_range/boolean.py

Handles ALL boolean expressions (simple and advanced) with magazine processing pattern.
No circular dependencies - self-contained boolean logic.
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
        parentheses_found = '(' in range_str and ')' in range_str
        
        return len(operators_found) > 0 or parentheses_found
    
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
        
        # Look for "X to Y" patterns in tokens
        i = 0
        while i < len(tokens) - 2:
            if tokens[i + 1].lower() == 'to':
                # Found potential range pattern
                start_token = tokens[i]
                end_token = tokens[i + 2]
                range_pattern = f"{start_token} to {end_token}"
                
                if looks_like_range_pattern(range_pattern):
                    patterns.append(range_pattern)
                    i += 3  # Skip past this pattern
                else:
                    i += 1
            else:
                i += 1
        
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
        
        range_pattern = advanced_patterns[0]
        
        # Step 1: Load magazine (expand range pattern into page groups)
        magazine_groups = self._load_magazine(range_pattern)
        
        # Step 2: Create simplified expression without the range pattern
        simplified_expression = self._remove_range_pattern(expression, range_pattern)
        
        # Step 3: Process each group through the boolean filter
        result_groups = []
        individual_pages = set()
        
        for group in magazine_groups:
            filtered_pages, or_additions = self._process_group_through_filter(
                group, simplified_expression
            )
            
            # Preserve group if any pages survived filtering
            if filtered_pages:
                result_groups.append(PageGroup(
                    filtered_pages, 
                    len(filtered_pages) > 1,  # is_range if multiple pages
                    group.original_spec
                ))
            
            # Collect individual pages from OR conditions
            individual_pages.update(or_additions)
        
        # Step 4: Add individual pages that aren't already in groups
        for page in individual_pages:
            if not any(page in group.pages for group in result_groups):
                result_groups.append(PageGroup([page], False, f"page{page}"))
        
        # Step 5: Extract all pages for return
        all_pages = []
        for group in result_groups:
            all_pages.extend(group.pages)
        
        return sorted(list(set(all_pages))), result_groups
    
    def _load_magazine(self, range_pattern: str) -> list[PageGroup]:
        """Load magazine with page groups from range pattern expansion."""
        _, section_groups = parse_range_pattern_with_groups(
            range_pattern, self.pdf_path, self.total_pages
        )
        return section_groups
    
    def _remove_range_pattern(self, expression: str, range_pattern: str) -> str:
        """Remove range pattern from expression, leaving simplified boolean logic."""
        # Replace the range pattern with a placeholder that represents "current group"
        simplified = expression.replace(range_pattern, "GROUP_PAGES")
        
        # Clean up any resulting double operators or parentheses issues
        simplified = re.sub(r'\s*\(\s*GROUP_PAGES\s*\)\s*', ' GROUP_PAGES ', simplified)
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        
        return simplified
    
    def _process_group_through_filter(self, group: PageGroup, 
                                    simplified_expression: str) -> tuple[list[int], set[int]]:
        """Process a single page group through the boolean filter."""
        # Start with all pages in the group
        current_pages = set(group.pages)
        or_additions = set()
        
        # Parse the simplified expression
        if simplified_expression.strip() == "GROUP_PAGES":
            # Just the group itself, no additional filtering
            return list(current_pages), or_additions
        
        # Handle AND and OR operations
        current_pages, or_additions = self._apply_boolean_operations(
            current_pages, simplified_expression
        )
        
        return sorted(list(current_pages)), or_additions
    
    def _apply_boolean_operations(self, group_pages: set[int], 
                                expression: str) -> tuple[set[int], set[int]]:
        """Apply boolean operations to group pages."""
        or_additions = set()
        current_pages = group_pages.copy()
        
        # Handle basic AND operations (filters that remove pages)
        if '&' in expression:
            and_parts = [part.strip() for part in expression.split('&')]
            for part in and_parts:
                if part == "GROUP_PAGES":
                    continue  # Skip the group placeholder
                
                if part.startswith('!'):
                    # NOT operation - remove matching pages
                    not_pattern = part[1:].strip()
                    matching_pages = self._evaluate_simple_expression(not_pattern)
                    current_pages -= set(matching_pages)
                else:
                    # AND operation - keep only matching pages
                    matching_pages = self._evaluate_simple_expression(part)
                    current_pages &= set(matching_pages)
        
        # Handle OR operations (adds individual pages)
        if '|' in expression:
            or_parts = [part.strip() for part in expression.split('|')]
            for part in or_parts:
                if part == "GROUP_PAGES":
                    continue  # Skip the group placeholder
                
                matching_pages = self._evaluate_simple_expression(part)
                or_additions.update(matching_pages)
        
        return current_pages, or_additions
    
    def _evaluate_simple_expression(self, expr: str) -> list[int]:
        """Evaluate a single expression (no boolean operators)."""
        expr = expr.strip()
        
        # Handle 'all' keyword
        if expr.lower() == 'all':
            return list(range(1, self.total_pages + 1))
        
        # Handle existing range patterns
        if looks_like_range_pattern(expr):
            return parse_range_pattern(expr, self.pdf_path, self.total_pages)
        
        # Handle existing single patterns
        if looks_like_pattern(expr):
            return parse_pattern_expression(expr, self.pdf_path, self.total_pages)
        
        # Handle single expression (number, range, etc.)
        return parse_single_expression(expr, self.pdf_path, self.total_pages)
    
    #################################################################################################
    # Self-contained boolean processing logic (no external dependencies)
    
    def _find_boolean_operators(self, text: str) -> list[tuple[str, int]]:
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
                    if (i == 0 or text[i-1] != ' ') and (i+3 >= len(text) or text[i+3] != ' '):
                        operators.append(('&', i))
                        i += 3
                        continue
                elif text[i:i+3] == ' | ':
                    if (i == 0 or text[i-1] != ' ') and (i+3 >= len(text) or text[i+3] != ' '):
                        operators.append(('|', i))
                        i += 3
                        continue
                elif text[i:i+4] == ' & !':
                    if (i == 0 or text[i-1] != ' ') and (i+4 >= len(text) or text[i+4] != ' '):
                        operators.append(('&!', i))
                        i += 4
                        continue
                elif char == '!' and (i == 0 or text[i-1].isspace()):
                    operators.append(('!', i))
            
            i += 1
        
        return operators
    
    def _tokenize_expression(self, expr: str) -> list[str]:
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
        
        return [token for token in tokens if token]
    
    def _parse_expression_tokens(self, tokens: list[str]) -> list[int]:
        """Parse tokenized expression with precedence: () > ! > & > |"""
        if not tokens:
            return []
        
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
                
                if isinstance(right_operand, list):
                    right_pages = right_operand
                else:
                    right_pages = self._evaluate_simple_expression(right_operand)
                
                # AND with NOT: left & !right
                and_not_result = list(set(left_operand) - set(right_pages))
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
    
    def _create_consecutive_groups(self, pages: list[int], original_spec: str) -> list[PageGroup]:
        """Create consecutive run groups from pages."""
        if not pages:
            return []
        
        sorted_pages = sorted(set(pages))
        groups = []
        current_run = [sorted_pages[0]]
        
        for i in range(1, len(sorted_pages)):
            if sorted_pages[i] == sorted_pages[i-1] + 1:
                current_run.append(sorted_pages[i])
            else:
                groups.append(self._create_group_from_run(current_run))
                current_run = [sorted_pages[i]]
        
        groups.append(self._create_group_from_run(current_run))
        return groups
    
    def _create_group_from_run(self, run: list[int]) -> PageGroup:
        """Create PageGroup from consecutive run."""
        if len(run) == 1:
            return PageGroup(run, False, str(run[0]))
        else:
            return PageGroup(run, True, f"{run[0]}-{run[-1]}")


#################################################################################################
# Public API Functions

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
    
    This is the detection function that determines if escalation is needed.
    """
    # Create temporary supervisor for pattern detection
    supervisor = UnifiedBooleanSupervisor(Path("dummy"), 1)
    tokens = supervisor._tokenize_expression(expression)
    
    i = 0
    while i < len(tokens) - 2:
        if tokens[i + 1].lower() == 'to':
            range_pattern = f"{tokens[i]} to {tokens[i + 2]}"
            if looks_like_range_pattern(range_pattern):
                return True
            i += 3
        else:
            i += 1
    
    return False


def evaluate_boolean_expression_with_groups(expression: str, pdf_path: Path, 
                                            total_pages: int) -> tuple[list[int], list[PageGroup]]:
    """
    Main entry point for all boolean expression evaluation with group preservation.
    """
    supervisor = UnifiedBooleanSupervisor(pdf_path, total_pages)
    return supervisor.evaluate(expression)
