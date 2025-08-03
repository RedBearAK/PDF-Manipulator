"""Utilities for creating test PDFs with known content."""

from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf(filename: str, content_spec: dict = None) -> Path:
    """Create a test PDF with known content for pattern testing."""
    
    # Default content
    if content_spec is None:
        content_spec = {
            1: "Chapter 1\nThis is the first chapter with text content.",
            2: "Chapter 2\nThis has mixed content with some text.",  
            3: "Summary\nThis is the summary section.",
            4: "",  # Empty page
        }
    
    pdf_path = Path(filename)
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    
    for page_num, text in content_spec.items():
        if text:  # Non-empty page
            lines = text.split('\n')
            y_pos = 750
            for line in lines:
                c.drawString(100, y_pos, line)
                y_pos -= 20
        c.showPage()
    
    c.save()
    return pdf_path

def cleanup_test_pdfs():
    """Remove all test PDFs."""
    for pdf_file in Path('.').glob('test_*.pdf'):
        pdf_file.unlink(missing_ok=True)
