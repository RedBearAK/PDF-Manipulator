"""
Text sanitization utilities for filename generation.
File: pdf_manipulator/renamer/sanitizer.py
"""

import re


def sanitize_variable_name(text: str, max_length: int = 25) -> str:
    """
    Convert text to a valid template variable name.
    
    Examples:
        "Invoice Number" -> "invoice_number"
        "PO#" -> "po"
        "Company Name Ltd." -> "company_name_ltd"
        
    Args:
        text: Original text to convert
        max_length: Maximum length for variable name
        
    Returns:
        Sanitized variable name suitable for template substitution
    """
    if not text or not text.strip():
        return "unknown"
    
    # Convert to lowercase and replace spaces/punctuation with underscores
    clean = re.sub(r'[^\w\s]', '', text.lower())  # Remove punctuation
    clean = re.sub(r'\s+', '_', clean.strip())    # Spaces to underscores
    clean = re.sub(r'_+', '_', clean)             # Multiple underscores to single
    clean = clean.strip('_')                      # Remove leading/trailing underscores
    
    # Ensure it starts with a letter
    if clean and clean[0].isdigit():
        clean = 'var_' + clean
    
    # Truncate if needed (word-aware)
    if len(clean) > max_length:
        # Try to truncate at word boundaries
        parts = clean.split('_')
        truncated = ''
        for part in parts:
            if len(truncated + '_' + part) <= max_length:
                if truncated:
                    truncated += '_' + part
                else:
                    truncated = part
            else:
                break
        clean = truncated if truncated else clean[:max_length].rstrip('_')
    
    # Fallback for edge cases
    return clean if clean else "unknown"


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Convert text to filesystem-safe filename component.
    
    Examples:
        "ACME Corp & Co." -> "ACME-Corp-Co"
        "$1,250.00" -> "1250-00"
        "INV-2024/001" -> "INV-2024-001"
        
    Args:
        text: Original text to sanitize
        max_length: Maximum length for filename component
        
    Returns:
        Filesystem-safe text suitable for filenames
    """
    if not text or not text.strip():
        return "unknown"
    
    # Remove or replace problematic characters
    clean = str(text).strip()
    
    # Special handling for monetary amounts and numbers
    if re.match(r'[\$£€¥]?[\d,]+\.?\d*', clean):
        # Remove currency symbols and thousands separators
        clean = re.sub(r'[\$£€¥,]', '', clean)
        # Replace decimal points with dashes for filename safety
        clean = re.sub(r'\.', '-', clean)
    else:
        # General text handling
        # Replace filesystem-unsafe characters with dashes
        clean = re.sub(r'[<>:"/\\|?*]', '-', clean)
        
        # Replace other punctuation and spaces with dashes
        clean = re.sub(r'[^\w\.\-]', '-', clean)
    
    # Collapse multiple dashes
    clean = re.sub(r'-+', '-', clean)
    
    # Remove leading/trailing dashes and dots
    clean = clean.strip('-.')
    
    # Truncate if needed
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip('-.')
    
    # Fallback for edge cases
    return clean if clean else "unknown"


def auto_generate_variable_name(pattern_keyword: str) -> str:
    """
    Automatically generate variable name from pattern keyword.
    
    Used when user doesn't specify explicit variable names in patterns.
    
    Args:
        pattern_keyword: The keyword from the pattern (e.g., "Invoice Number")
        
    Returns:
        Auto-generated variable name (e.g., "invoice_number")
    """
    return sanitize_variable_name(pattern_keyword, max_length=20)


def validate_template_variable(var_name: str) -> tuple[bool, str]:
    """
    Validate that a variable name is suitable for template use.
    
    Args:
        var_name: Variable name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not var_name:
        return False, "Variable name cannot be empty"
    
    if not isinstance(var_name, str):
        return False, "Variable name must be a string"
    
    # Check for valid Python identifier (template variables follow these rules)
    if not var_name.isidentifier():
        return False, f"Invalid variable name: '{var_name}' (must be valid Python identifier)"
    
    # Check for reserved words that might cause confusion
    reserved = {'range', 'original_name', 'page_count', 'pages', 'file', 'path'}
    if var_name in reserved:
        return False, f"Variable name '{var_name}' is reserved"
    
    return True, ""


def sanitize_content_for_filename(content: str, content_type: str = "text") -> str:
    """
    Sanitize extracted content for use in filenames.
    
    Handles different content types appropriately.
    
    Args:
        content: Raw extracted content
        content_type: Type of content ('text', 'number', 'date', etc.)
        
    Returns:
        Sanitized content suitable for filename use
    """
    if not content or not content.strip():
        return "empty"
    
    clean = content.strip()
    
    # Special handling for different content types
    if content_type == "number":
        # Keep numbers readable but filesystem-safe
        clean = re.sub(r'[^\d\.\-]', '-', clean)
        clean = re.sub(r'-+', '-', clean).strip('-')
        
    elif content_type == "date":
        # Convert dates to filesystem-friendly format
        clean = re.sub(r'[/\\]', '-', clean)  # Slashes to dashes
        clean = re.sub(r'[,\s]+', '-', clean)  # Commas and spaces to dashes
        clean = re.sub(r'-+', '-', clean).strip('-')
        
    else:
        # General text sanitization
        clean = sanitize_filename(clean, max_length=30)
    
    return clean if clean else "content"


# End of file #
