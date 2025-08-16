"""
Template-based filename generation with variable substitution.
File: pdf_manipulator/renamer/template_engine.py

Handles filename templates like "{company}_{invoice}_{amount}_pages{range}.pdf"
with fallback values and built-in variables.
"""

import re

from pathlib import Path
from rich.console import Console

from pdf_manipulator.renamer.sanitizer import sanitize_filename


console = Console()


class TemplateError(Exception):
    """Exception for template processing errors."""
    pass


class TemplateEngine:
    """
    Process filename templates with variable substitution and fallbacks.
    
    Template Syntax:
    - Variables: {variable_name}
    - Fallbacks: {variable_name|fallback_value}
    - Built-ins: {range}, {original_name}, {page_count}
    
    Examples:
    - "{company}_{invoice}.pdf" -> "ACME-Corp_INV-001.pdf"
    - "{vendor|Unknown}_{amount|NO-AMT}.pdf" -> "ACME-Corp_1250-00.pdf"
    - "{invoice}_pages{range}.pdf" -> "INV-001_pages01-03.pdf"
    """
    
    # Regex for template variables with optional fallbacks
    VARIABLE_PATTERN = re.compile(r'\{([^}|]+)(\|([^}]*))?\}')
    
    def __init__(self):
        pass
    
    def parse_template(self, template: str) -> list[tuple[str, str]]:
        """
        Parse template string and extract variables with fallbacks.
        
        Args:
            template: Template string like "{company|Unknown}_{invoice}.pdf"
            
        Returns:
            List of (variable_name, fallback_value) tuples
            
        Raises:
            TemplateError: For invalid template syntax
        """
        if not template or not isinstance(template, str):
            raise TemplateError("Template must be a non-empty string")
        
        variables = []
        matches = self.VARIABLE_PATTERN.findall(template)
        
        for match in matches:
            var_name = match[0].strip()
            fallback = match[2] if match[2] is not None else ""
            
            if not var_name:
                raise TemplateError("Variable name cannot be empty")
            
            # Validate variable name (basic identifier rules)
            if not var_name.replace('_', 'a').isalnum():
                raise TemplateError(f"Invalid variable name: '{var_name}'")
            
            variables.append((var_name, fallback))
        
        return variables
    
    def get_required_variables(self, template: str) -> set[str]:
        """
        Get set of all variable names required by template.
        
        Args:
            template: Template string
            
        Returns:
            Set of variable names needed for substitution
        """
        variables = self.parse_template(template)
        return {var_name for var_name, _ in variables}
    
    def validate_template(self, template: str) -> tuple[bool, str]:
        """
        Validate template syntax and structure.
        
        Args:
            template: Template string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check basic parsing
            variables = self.parse_template(template)
            
            # Check for balanced braces
            open_braces = template.count('{')
            close_braces = template.count('}')
            if open_braces != close_braces:
                return False, f"Unbalanced braces: {open_braces} open, {close_braces} close"
            
            # Check for nested braces
            if '{{' in template or '}}' in template:
                return False, "Nested braces not supported"
            
            # Check that all braces are part of valid variables
            remaining = template
            for var_name, fallback in variables:
                if fallback:
                    pattern = f"{{{var_name}|{fallback}}}"
                else:
                    pattern = f"{{{var_name}}}"
                remaining = remaining.replace(pattern, '', 1)
            
            # Check for orphaned braces
            if '{' in remaining or '}' in remaining:
                return False, "Invalid brace syntax found"
            
            # Check for reasonable filename length (rough estimate)
            if len(template) > 200:
                return False, "Template too long (max ~200 characters)"
            
            return True, ""
            
        except TemplateError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def substitute_variables(self, template: str, variables: dict[str, str], 
                            built_ins: dict[str, str] = None) -> str:
        """
        Substitute variables in template with actual values.
        
        Args:
            template: Template string with variables
            variables: Dictionary of variable values
            built_ins: Dictionary of built-in variable values
            
        Returns:
            String with variables substituted
            
        Raises:
            TemplateError: For substitution errors
        """
        if built_ins is None:
            built_ins = {}
        
        # Combine user variables with built-ins (user variables take precedence)
        all_variables = {**built_ins, **variables}
        
        result = template
        parsed_vars = self.parse_template(template)
        
        for var_name, fallback in parsed_vars:
            # Determine value to use
            if var_name in all_variables and all_variables[var_name] is not None:
                value = str(all_variables[var_name])
            elif fallback:
                value = fallback
            else:
                # No value and no fallback - use placeholder
                value = f"NO-{var_name.upper()}"
            
            # Sanitize value for filename use
            clean_value = sanitize_filename(value, max_length=40)
            
            # Replace in template
            if fallback:
                pattern = f"{{{var_name}|{fallback}}}"
            else:
                pattern = f"{{{var_name}}}"
            
            result = result.replace(pattern, clean_value, 1)
        
        return result
    
    def generate_filename(self, template: str, variables: dict[str, str], 
                         original_path: Path, page_range: str, 
                         page_count: int = None) -> str:
        """
        Generate complete filename from template and variables.
        
        Args:
            template: Filename template
            variables: Extracted variable values  
            original_path: Original PDF file path
            page_range: Page range description (e.g., "01-03", "05", "03,07,12")
            page_count: Number of pages being extracted
            
        Returns:
            Generated filename
        """
        # Create built-in variables
        built_ins = {
            'original_name': original_path.stem,
            'range': page_range,
        }
        
        if page_count is not None:
            built_ins['page_count'] = str(page_count)
        
        # Substitute variables
        filename = self.substitute_variables(template, variables, built_ins)
        
        # Ensure .pdf extension if not present
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        return filename
    
    def preview_substitution(self, template: str, variables: dict[str, str], 
                            built_ins: dict[str, str] = None) -> dict:
        """
        Preview template substitution without generating final filename.
        
        Useful for dry-run mode and debugging.
        
        Args:
            template: Template string
            variables: Variable values
            built_ins: Built-in variable values
            
        Returns:
            Dictionary with substitution details
        """
        if built_ins is None:
            built_ins = {}
        
        all_variables = {**built_ins, **variables}
        parsed_vars = self.parse_template(template)
        
        substitutions = []
        result = template
        
        for var_name, fallback in parsed_vars:
            substitution_info = {
                'variable': var_name,
                'fallback': fallback or None,
                'found_value': all_variables.get(var_name),
                'used_fallback': False,
                'final_value': None
            }
            
            # Determine what value will be used
            if var_name in all_variables and all_variables[var_name] is not None:
                raw_value = str(all_variables[var_name])
                substitution_info['used_fallback'] = False
            elif fallback:
                raw_value = fallback
                substitution_info['used_fallback'] = True
            else:
                raw_value = f"NO-{var_name.upper()}"
                substitution_info['used_fallback'] = True
            
            # Show sanitized value
            clean_value = sanitize_filename(raw_value, max_length=40)
            substitution_info['final_value'] = clean_value
            
            substitutions.append(substitution_info)
            
            # Apply substitution to result
            if fallback:
                pattern = f"{{{var_name}|{fallback}}}"
            else:
                pattern = f"{{{var_name}}}"
            
            result = result.replace(pattern, clean_value, 1)
        
        return {
            'template': template,
            'result': result,
            'substitutions': substitutions
        }


def create_default_template(has_patterns: bool = False) -> str:
    """
    Create a reasonable default template based on available information.
    
    Args:
        has_patterns: Whether content extraction patterns are being used
        
    Returns:
        Default template string
    """
    if has_patterns:
        return "{original_name}_extracted_pages{range}.pdf"
    else:
        return "{original_name}_pages{range}.pdf"


def validate_template_against_variables(template: str, available_vars: set[str]) -> tuple[bool, str]:
    """
    Validate that template variables are available for substitution.
    
    Args:
        template: Template string
        available_vars: Set of available variable names
        
    Returns:
        Tuple of (is_valid, warning_message)
    """
    engine = TemplateEngine()
    
    try:
        required_vars = engine.get_required_variables(template)
        parsed_vars = engine.parse_template(template)
        
        missing_vars = []
        fallback_vars = []
        
        for var_name, fallback in parsed_vars:
            if var_name not in available_vars:
                if fallback:
                    fallback_vars.append(var_name)
                else:
                    missing_vars.append(var_name)
        
        if missing_vars:
            return False, f"Missing variables (no fallback): {', '.join(missing_vars)}"
        
        if fallback_vars:
            return True, f"Variables will use fallbacks: {', '.join(fallback_vars)}"
        
        return True, ""
        
    except TemplateError as e:
        return False, f"Template error: {e}"


# End of file #
