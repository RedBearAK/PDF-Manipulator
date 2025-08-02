"""
Page content analysis for type detection and size calculation.
Create: pdf_manipulator/core/page_analysis.py
"""

import tempfile

from pypdf import PdfReader, PdfWriter
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console

from pdf_manipulator.core.warning_suppression import suppress_pdf_warnings


console = Console()


@dataclass
class PageAnalysis:
    """Analysis results for a single page."""
    page_number: int
    page_type: str  # 'text', 'image', 'mixed', 'empty'
    size_bytes: int
    size_kb: float
    size_mb: float
    text_length: int
    image_count: int
    has_meaningful_text: bool
    confidence: float  # 0.0 to 1.0 confidence in type classification


class PageAnalyzer:
    """Analyzes PDF pages for content type and size."""
    
    # Classification thresholds
    MIN_TEXT_LENGTH = 50  # Minimum chars for meaningful text
    MIN_TEXT_RATIO = 0.3  # Minimum text/image ratio for 'mixed'
    CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence for classification
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.reader = None
        self.page_cache: dict[int, PageAnalysis] = {}
    
    def __enter__(self):
        """Context manager entry."""
        with suppress_pdf_warnings():
            self.reader = PdfReader(self.pdf_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.reader = None
        self.page_cache.clear()
    
    def analyze_page(self, page_number: int) -> PageAnalysis:
        """
        Analyze a single page for type and size.
        
        Args:
            page_number: 1-indexed page number
            
        Returns:
            PageAnalysis object with classification results
        """
        if not self.reader:
            raise RuntimeError("PageAnalyzer must be used as context manager")
        
        # Check cache first
        if page_number in self.page_cache:
            return self.page_cache[page_number]
        
        if page_number < 1 or page_number > len(self.reader.pages):
            raise ValueError(f"Page {page_number} out of range (1-{len(self.reader.pages)})")
        
        page = self.reader.pages[page_number - 1]  # Convert to 0-indexed
        
        # Extract text and count images
        text_content = self._extract_page_text(page)
        image_count = self._count_page_images(page)
        
        # Calculate page size
        size_bytes = self._calculate_page_size(page_number)
        
        # Classify page type
        page_type, confidence = self._classify_page_type(text_content, image_count)
        
        # Create analysis result
        analysis = PageAnalysis(
            page_number=page_number,
            page_type=page_type,
            size_bytes=size_bytes,
            size_kb=size_bytes / 1024,
            size_mb=size_bytes / (1024 * 1024),
            text_length=len(text_content),
            image_count=image_count,
            has_meaningful_text=len(text_content.strip()) >= self.MIN_TEXT_LENGTH,
            confidence=confidence
        )
        
        # Cache the result
        self.page_cache[page_number] = analysis
        return analysis
    
    def analyze_all_pages(self) -> list[PageAnalysis]:
        """Analyze all pages in the PDF."""
        if not self.reader:
            raise RuntimeError("PageAnalyzer must be used as context manager")
        
        results = []
        total_pages = len(self.reader.pages)
        
        for page_num in range(1, total_pages + 1):
            analysis = self.analyze_page(page_num)
            results.append(analysis)
        
        return results
    
    def get_pages_by_type(self, page_type: str) -> list[int]:
        """Get list of page numbers matching the specified type."""
        if not self.reader:
            raise RuntimeError("PageAnalyzer must be used as context manager")
        
        matching_pages = []
        total_pages = len(self.reader.pages)
        
        for page_num in range(1, total_pages + 1):
            analysis = self.analyze_page(page_num)
            if analysis.page_type == page_type:
                matching_pages.append(page_num)
        
        return matching_pages
    
    def get_pages_by_size(self, size_condition: str) -> list[int]:
        """
        Get list of page numbers matching size condition.
        
        Args:
            size_condition: e.g., '<500KB', '>1MB', '>=2MB', '<=100KB'
            
        Returns:
            List of matching page numbers
        """
        if not self.reader:
            raise RuntimeError("PageAnalyzer must be used as context manager")
        
        # Parse size condition
        operator, target_bytes = self._parse_size_condition(size_condition)
        
        matching_pages = []
        total_pages = len(self.reader.pages)
        
        for page_num in range(1, total_pages + 1):
            analysis = self.analyze_page(page_num)
            
            if self._compare_size(analysis.size_bytes, operator, target_bytes):
                matching_pages.append(page_num)
        
        return matching_pages
    
    def _extract_page_text(self, page) -> str:
        """Extract text from a page, handling errors gracefully."""
        try:
            with suppress_pdf_warnings():
                text = page.extract_text()
                return text if text else ""
        except Exception:
            return ""
    
    def _count_page_images(self, page) -> int:
        """Count images on a page."""
        try:
            if '/XObject' not in page.get('/Resources', {}):
                return 0
            
            xobjects = page['/Resources']['/XObject'].get_object()
            images = [x for x in xobjects if xobjects[x].get('/Subtype') == '/Image']
            return len(images)
        except Exception:
            return 0
    
    def _calculate_page_size(self, page_number: int) -> int:
        """
        Calculate the size of a single page by extracting it to a temporary file.
        
        Args:
            page_number: 1-indexed page number
            
        Returns:
            Size in bytes
        """
        try:
            # Create a temporary PDF with just this page
            writer = PdfWriter()
            page = self.reader.pages[page_number - 1]  # Convert to 0-indexed
            writer.add_page(page)
            
            # Write to temporary file to measure size
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                writer.write(tmp_file)
                tmp_path = Path(tmp_file.name)
            
            try:
                size_bytes = tmp_path.stat().st_size
                return size_bytes
            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            console.print(f"[dim]Warning: Could not calculate size for page {page_number}: {e}[/dim]")
            # Fallback: estimate based on total file size
            total_size = self.pdf_path.stat().st_size
            total_pages = len(self.reader.pages)
            return total_size // total_pages
    
    def _classify_page_type(self, text_content: str, image_count: int) -> tuple[str, float]:
        """
        Classify page type based on content analysis.
        
        Returns:
            Tuple of (page_type, confidence)
        """
        text_length = len(text_content.strip())
        has_meaningful_text = text_length >= self.MIN_TEXT_LENGTH
        
        # Empty page
        if not has_meaningful_text and image_count == 0:
            return 'empty', 0.95
        
        if text_length < 10 and image_count == 0:
            return 'empty', 0.90
        
        # Image-only page
        if not has_meaningful_text and image_count > 0:
            confidence = 0.90 if image_count >= 1 else 0.75
            return 'image', confidence
        
        # Text-only page
        if has_meaningful_text and image_count == 0:
            confidence = 0.95 if text_length > 200 else 0.85
            return 'text', confidence
        
        # Mixed content page
        if has_meaningful_text and image_count > 0:
            # Calculate text-to-image ratio for confidence
            text_score = min(text_length / 500, 1.0)  # Normalize to 0-1
            image_score = min(image_count / 5, 1.0)   # Normalize to 0-1
            
            balance = 1.0 - abs(text_score - image_score)  # Higher when balanced
            confidence = 0.75 + (balance * 0.20)  # 0.75 to 0.95
            
            return 'mixed', confidence
        
        # Fallback for edge cases
        if image_count > 0:
            return 'image', 0.60
        elif text_length > 0:
            return 'text', 0.60
        else:
            return 'empty', 0.60
    
    def _parse_size_condition(self, condition: str) -> tuple[str, int]:
        """
        Parse size condition into operator and target bytes.
        
        Args:
            condition: e.g., '<500KB', '>1MB', '>=2MB'
            
        Returns:
            Tuple of (operator, target_bytes)
        """
        import re
        
        # Match operator and value with unit
        match = re.match(r'([<>=]+)(\d+(?:\.\d+)?)(KB|MB|GB)?', condition.upper())
        if not match:
            raise ValueError(f"Invalid size condition: {condition}")
        
        operator = match.group(1)
        value = float(match.group(2))
        unit = match.group(3) or 'B'
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        target_bytes = int(value * multipliers[unit])
        
        return operator, target_bytes
    
    def _compare_size(self, actual_bytes: int, operator: str, target_bytes: int) -> bool:
        """Compare actual size with target using operator."""
        if operator == '<':
            return actual_bytes < target_bytes
        elif operator == '<=':
            return actual_bytes <= target_bytes
        elif operator == '>':
            return actual_bytes > target_bytes
        elif operator == '>=':
            return actual_bytes >= target_bytes
        elif operator == '==' or operator == '=':
            # Allow some tolerance for exact matches
            tolerance = max(target_bytes * 0.05, 1024)  # 5% or 1KB
            return abs(actual_bytes - target_bytes) <= tolerance
        else:
            raise ValueError(f"Unsupported operator: {operator}")


def analyze_pdf_pages(pdf_path: Path) -> list[PageAnalysis]:
    """
    Convenience function to analyze all pages in a PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of PageAnalysis objects
    """
    with PageAnalyzer(pdf_path) as analyzer:
        return analyzer.analyze_all_pages()


def get_pages_by_type(pdf_path: Path, page_type: str) -> list[int]:
    """
    Convenience function to get pages matching a specific type.
    
    Args:
        pdf_path: Path to PDF file
        page_type: 'text', 'image', 'mixed', or 'empty'
        
    Returns:
        List of page numbers (1-indexed)
    """
    with PageAnalyzer(pdf_path) as analyzer:
        return analyzer.get_pages_by_type(page_type)


def get_pages_by_size(pdf_path: Path, size_condition: str) -> list[int]:
    """
    Convenience function to get pages matching a size condition.
    
    Args:
        pdf_path: Path to PDF file
        size_condition: e.g., '<500KB', '>1MB'
        
    Returns:
        List of page numbers (1-indexed)
    """
    with PageAnalyzer(pdf_path) as analyzer:
        return analyzer.get_pages_by_size(size_condition)
