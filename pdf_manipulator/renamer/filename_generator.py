"""
Filename generation with conflict resolution and fallback handling.
File: pdf_manipulator/renamer/filename_generator.py
"""

from pathlib import Path
from rich.console import Console

from pdf_manipulator.renamer.template_engine import TemplateEngine
from pdf_manipulator.renamer.pattern_processor import PatternProcessor


console = Console()


class FilenameGenerator:
    """
    Generate intelligent filenames using template substitution and pattern extraction.
    
    Handles:
    - Template-based filename generation
    - Pattern extraction from PDF content
    - File conflict resolution
    - Graceful fallback when extraction fails
    """
    
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.pattern_processor = PatternProcessor()
    
    def generate_smart_filename(self, original_path: Path, page_range_desc: str,
                               patterns: list[str] = None, template: str = None,
                               source_page: int = 1, dry_run: bool = False) -> tuple[Path, dict]:
        """
        Generate filename using pattern extraction and template substitution.
        
        Args:
            original_path: Path to original PDF file
            page_range_desc: Description of page range (e.g., "01-03", "page05")
            patterns: List of compact pattern strings
            template: Filename template string
            source_page: Page number to extract patterns from
            dry_run: Whether this is a dry run (affects extraction)
            
        Returns:
            Tuple of (generated_path, extraction_results)
        """
        extraction_results = {
            'variables_extracted': {},
            'patterns_processed': [],
            'extraction_errors': [],
            'template_used': template,
            'fallback_used': False
        }
        
        # If no patterns or template provided, use simple naming
        if not patterns or not template:
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            extraction_results['fallback_used'] = True
            return self._resolve_conflicts(simple_path), extraction_results
        
        try:
            # Parse and validate patterns
            parsed_patterns = self.pattern_processor.validate_pattern_list(patterns)
            extraction_results['patterns_processed'] = [
                {
                    'pattern': pattern,
                    'variable': var_name,
                    'keyword': keyword
                }
                for pattern, (var_name, keyword, _) in zip(patterns, parsed_patterns)
            ]
            
            # Extract content from PDF (skip in dry-run to avoid processing time)
            if not dry_run:
                variables = self.pattern_processor.extract_content_from_pdf(
                    original_path, parsed_patterns, source_page
                )
            else:
                # In dry-run, simulate extraction results
                variables = self._simulate_extraction_results(parsed_patterns)
            
            extraction_results['variables_extracted'] = variables
            
            # Count total pages being extracted (rough estimate from range description)
            page_count = self._estimate_page_count(page_range_desc)
            
            # Generate filename using template
            filename = self.template_engine.generate_filename(
                template, variables, original_path, page_range_desc, page_count
            )
            
            generated_path = original_path.parent / filename
            return self._resolve_conflicts(generated_path), extraction_results
            
        except Exception as e:
            # Fallback to simple naming on any error
            console.print(f"[yellow]Pattern extraction failed ({e}), using simple naming[/yellow]")
            extraction_results['extraction_errors'].append(str(e))
            extraction_results['fallback_used'] = True
            
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            return self._resolve_conflicts(simple_path), extraction_results
    
    def _simulate_extraction_results(self, parsed_patterns: list) -> dict[str, str]:
        """Simulate extraction results for dry-run mode."""
        simulated = {}
        for var_name, keyword, extraction_spec in parsed_patterns:
            # Create plausible dummy values based on keyword
            if 'invoice' in keyword.lower():
                simulated[var_name] = "INV-2024-001"
            elif 'company' in keyword.lower() or 'vendor' in keyword.lower():
                simulated[var_name] = "ACME-Corp"
            elif 'amount' in keyword.lower() or 'total' in keyword.lower():
                simulated[var_name] = "1250-00"
            elif 'date' in keyword.lower():
                simulated[var_name] = "2024-01-15"
            elif 'po' in keyword.lower():
                simulated[var_name] = "PO-98765"
            else:
                simulated[var_name] = f"SAMPLE-{var_name.upper()}"
        
        return simulated
    
    def _estimate_page_count(self, page_range_desc: str) -> int:
        """Estimate number of pages from range description."""
        # Simple heuristics based on common range formats
        if '-' in page_range_desc:
            # Range like "01-03" or "05-10"
            try:
                parts = page_range_desc.split('-')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return int(parts[1]) - int(parts[0]) + 1
            except:
                pass
        
        if ',' in page_range_desc:
            # Multiple pages like "01,03,07"
            try:
                parts = page_range_desc.split(',')
                return len([p for p in parts if p.strip().isdigit()])
            except:
                pass
        
        # Default to 1 page
        return 1
    
    def _resolve_conflicts(self, proposed_path: Path) -> Path:
        """
        Resolve filename conflicts by appending _copy_01, _copy_02, etc.
        
        Uses the same logic as existing operations.py
        """
        if not proposed_path.exists():
            return proposed_path
        
        stem = proposed_path.stem
        suffix = proposed_path.suffix
        parent = proposed_path.parent
        
        counter = 1
        while True:
            new_name = f"{stem}_copy_{counter:02d}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def preview_filename_generation(self, original_path: Path, page_range_desc: str,
                                   patterns: list[str] = None, template: str = None,
                                   source_page: int = 1) -> dict:
        """
        Preview filename generation for dry-run mode.
        
        Shows what would be extracted and what the final filename would be.
        """
        preview = {
            'original_file': original_path.name,
            'page_range': page_range_desc,
            'source_page': source_page,
            'patterns': patterns or [],
            'template': template,
            'extraction_preview': {},
            'filename_preview': None,
            'would_conflict': False,
            'final_filename': None
        }
        
        if not patterns or not template:
            # Simple naming
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            final_path = self._resolve_conflicts(simple_path)
            
            preview['filename_preview'] = simple_filename
            preview['would_conflict'] = final_path != simple_path
            preview['final_filename'] = final_path.name
            return preview
        
        try:
            # Parse patterns and show what would be extracted
            parsed_patterns = self.pattern_processor.validate_pattern_list(patterns)
            
            # Simulate extraction
            simulated_vars = self._simulate_extraction_results(parsed_patterns)
            
            for pattern, (var_name, keyword, extraction_spec) in zip(patterns, parsed_patterns):
                preview['extraction_preview'][var_name] = {
                    'pattern': pattern,
                    'keyword': keyword,
                    'simulated_value': simulated_vars.get(var_name, 'NOT-FOUND')
                }
            
            # Preview template substitution
            template_preview = self.template_engine.preview_substitution(
                template, simulated_vars, {
                    'original_name': original_path.stem,
                    'range': page_range_desc,
                    'page_count': str(self._estimate_page_count(page_range_desc))
                }
            )
            
            preview['template_substitution'] = template_preview
            preview['filename_preview'] = template_preview['result']
            
            # Check for conflicts
            proposed_path = original_path.parent / template_preview['result']
            final_path = self._resolve_conflicts(proposed_path)
            preview['would_conflict'] = final_path != proposed_path
            preview['final_filename'] = final_path.name
            
        except Exception as e:
            preview['error'] = str(e)
            preview['fallback_used'] = True
            
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            preview['filename_preview'] = simple_filename
            preview['final_filename'] = simple_filename
        
        return preview


# End of file #
