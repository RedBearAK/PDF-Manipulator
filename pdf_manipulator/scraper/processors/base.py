"""
Abstract base class for PDF processors.
"""

from abc import ABC, abstractmethod


class PDFProcessor(ABC):
    """
    Abstract base class for PDF text extraction backends.
    
    This allows for easy swapping of different PDF processing libraries
    based on performance, accuracy, or feature requirements.
    """
    
    @abstractmethod
    def extract_pages(self, pdf_path):
        """
        Extract text from all pages of a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            list[str]: List of text content from each page
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For any PDF processing errors
        """
        pass
    
    @abstractmethod
    def extract_page(self, pdf_path, page_number):
        """
        Extract text from a specific page of a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            page_number (int): Page number (1-based)
            
        Returns:
            str: Text content from the specified page
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            IndexError: If page number is out of range
            Exception: For any PDF processing errors
        """
        pass
    
    def get_page_count(self, pdf_path):
        """
        Get the number of pages in a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            int: Number of pages in the PDF
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For any PDF processing errors
        """
        # Default implementation - subclasses can override for efficiency
        pages = self.extract_pages(pdf_path)
        return len(pages)
    
    def validate_pdf(self, pdf_path):
        """
        Check if a file is a valid PDF that can be processed.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            bool: True if PDF can be processed, False otherwise
        """
        try:
            self.get_page_count(pdf_path)
            return True
        except Exception:
            return False
