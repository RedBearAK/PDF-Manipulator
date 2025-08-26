"""
File conflict exception for PDF operations.
File: pdf_manipulator/core/exceptions.py
"""


class FileConflictError(FileExistsError):
    """
    Raised when a file conflict cannot be resolved.
    
    This exception is raised when:
    - A conflict resolution strategy fails
    - User chooses to skip/cancel when asked about conflicts
    - Auto-resolution cannot generate a safe filename
    
    Inherits from FileExistsError as it represents a more specific
    type of "file already exists" condition with resolution context.
    """
    
    def __init__(self, filepath, strategy=None, message=None):
        """
        Initialize file conflict error.
        
        Args:
            filepath: Path or str of the conflicting file
            strategy: The conflict resolution strategy that failed
            message: Custom error message
        """
        self.filepath = filepath
        self.strategy = strategy
        
        if message:
            super().__init__(message)
        else:
            base_msg = f"File conflict: {filepath}"
            if strategy:
                base_msg += f" (strategy: {strategy})"
            super().__init__(base_msg)


# End of file #
