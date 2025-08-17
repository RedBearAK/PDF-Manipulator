"""
Enhanced filename generation with Phase 3 multi-page/multi-match pattern extraction support.
File: pdf_manipulator/renamer/filename_generator.py

PHASE 3 ENHANCEMENTS:
- Real dry-run functionality with actual pattern extraction
- Enhanced pattern extraction with multi-page and multi-match support
- Comprehensive preview and warning systems
- Intelligent fallback handling for pattern extraction failures
- Integration with enhanced PatternProcessor and TemplateEngine
"""

from pathlib import Path
from rich.console import Console

from pdf_manipulator.renamer.template_engine import TemplateEngine
from pdf_manipulator.renamer.pattern_processor import PatternProcessor, CompactPatternError


console = Console()


class FilenameGenerator:
    """
    Generate intelligent filenames using enhanced template substitution and pattern extraction.
    
    PHASE 3 CAPABILITIES:
    - Multi-page pattern extraction with pg specifications
    - Multi-match selection with mt specifications  
    - Real dry-run extraction for accurate previews
    - Comprehensive error handling and user feedback
    - Graceful fallback when pattern extraction fails
    """
    
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.pattern_processor = PatternProcessor()
    
    def generate_smart_filename(self, original_path: Path, page_range_desc: str,
                               patterns: list[str] = None, template: str = None,
                               source_page: int = 1, dry_run: bool = False) -> tuple[Path, dict]:
        """
        Generate filename using Phase 3 enhanced pattern extraction and template substitution.
        
        Args:
            original_path: Path to original PDF file
            page_range_desc: Description of page range (e.g., "01-03", "page05")
            patterns: List of enhanced compact pattern strings
            template: Filename template string
            source_page: Fallback page number for patterns without pg specification
            dry_run: Whether to perform real extraction for preview
            
        Returns:
            Tuple of (generated_path, extraction_results)
        """
        extraction_results = {
            'variables_extracted': {},
            'patterns_processed': [],
            'extraction_errors': [],
            'template_used': template,
            'fallback_used': False,
            'template_result': None,
            'dry_run': dry_run
        }
        
        # If no patterns or template provided, use simple naming
        if not patterns or not template:
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            extraction_results['fallback_used'] = True
            extraction_results['template_result'] = simple_filename
            return self._resolve_conflicts(simple_path), extraction_results
        
        try:
            # Parse and validate all patterns
            parsed_patterns = self.pattern_processor.validate_pattern_list(patterns)
            extraction_results['patterns_processed'] = [
                f"{var}={keyword}:{spec}" for var, keyword, spec in parsed_patterns
            ]
            
            # Extract content using enhanced pattern processor
            extraction_results['variables_extracted'] = self._extract_all_patterns(
                original_path, parsed_patterns, source_page, dry_run
            )
            
            # Check if any extractions succeeded
            successful_extractions = {
                var: result for var, result in extraction_results['variables_extracted'].items()
                if result.get('success') and result.get('selected_match') != "No_Match"
            }
            
            if not successful_extractions and not dry_run:
                # All extractions failed - use fallback naming with warning
                extraction_results['fallback_used'] = True
                extraction_results['extraction_errors'].append("All pattern extractions failed")
                simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
                simple_path = original_path.parent / simple_filename
                extraction_results['template_result'] = simple_filename
                return self._resolve_conflicts(simple_path), extraction_results
            
            # Build variables dictionary for template engine
            template_variables = self._build_template_variables(
                extraction_results['variables_extracted'], 
                original_path, 
                page_range_desc,
                dry_run
            )
            
            # Apply template substitution
            try:
                filename = self.template_engine.apply_template(template, template_variables)
                extraction_results['template_result'] = filename
                
                # Ensure .pdf extension
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                
                output_path = original_path.parent / filename
                return self._resolve_conflicts(output_path), extraction_results
                
            except Exception as e:
                # Template application failed - use fallback
                extraction_results['fallback_used'] = True
                extraction_results['extraction_errors'].append(f"Template application failed: {e}")
                simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
                simple_path = original_path.parent / simple_filename
                extraction_results['template_result'] = simple_filename
                return self._resolve_conflicts(simple_path), extraction_results
        
        except CompactPatternError as e:
            # Pattern parsing failed - use fallback
            extraction_results['fallback_used'] = True
            extraction_results['extraction_errors'].append(f"Pattern parsing failed: {e}")
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            extraction_results['template_result'] = simple_filename
            return self._resolve_conflicts(simple_path), extraction_results
        
        except Exception as e:
            # Unexpected error - use fallback
            extraction_results['fallback_used'] = True
            extraction_results['extraction_errors'].append(f"Unexpected error: {e}")
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            simple_path = original_path.parent / simple_filename
            extraction_results['template_result'] = simple_filename
            return self._resolve_conflicts(simple_path), extraction_results
    
    def _extract_all_patterns(self, pdf_path: Path, parsed_patterns: list, 
                             source_page: int, dry_run: bool) -> dict:
        """
        Extract content for all patterns using enhanced Phase 3 extraction.
        
        Args:
            pdf_path: Path to PDF file
            parsed_patterns: List of (variable_name, keyword, extraction_spec) tuples
            source_page: Fallback page for patterns without pg specification
            dry_run: Whether this is a dry-run extraction
            
        Returns:
            Dictionary mapping variable names to extraction results
        """
        results = {}
        
        for variable_name, keyword, extraction_spec in parsed_patterns:
            try:
                # Phase 3: Use enhanced extraction with multi-page/multi-match support
                result = self.pattern_processor.extract_from_pdf(
                    pdf_path, variable_name, keyword, extraction_spec, source_page
                )
                results[variable_name] = result
                
            except Exception as e:
                # Individual pattern extraction failed
                results[variable_name] = {
                    'variable_name': variable_name,
                    'keyword': keyword,
                    'success': False,
                    'selected_match': f"Error: {str(e)}",
                    'warnings': [f"Extraction failed: {str(e)}"],
                    'debug_info': {'exception': str(e)}
                }
        
        return results
    
    def _build_template_variables(self, extraction_results: dict, original_path: Path, 
                                 page_range_desc: str, dry_run: bool) -> dict:
        """
        Build variables dictionary for template engine from extraction results.
        
        Args:
            extraction_results: Results from pattern extraction
            original_path: Original PDF file path
            page_range_desc: Description of page range
            dry_run: Whether this is a dry-run
            
        Returns:
            Dictionary of template variables
        """
        variables = {
            'original_name': original_path.stem,
            'range': page_range_desc,
            'page_count': self._estimate_page_count(page_range_desc)
        }
        
        # Add extracted variables
        for var_name, result in extraction_results.items():
            if result.get('success') and result.get('selected_match') != "No_Match":
                variables[var_name] = result['selected_match']
            else:
                # Use fallback value or indicate missing
                if dry_run:
                    # For dry-run, show what would be extracted
                    variables[var_name] = f"PREVIEW_{var_name.upper()}"
                else:
                    # For real extraction, use fallback or missing indicator
                    variables[var_name] = f"NO_{var_name.upper()}"
        
        return variables
    
    def show_extraction_preview(self, extraction_results: dict):
        """
        Show detailed extraction preview for dry-run mode.
        
        Args:
            extraction_results: Results from pattern extraction
        """
        console.print(f"\n[cyan]Pattern extraction preview:[/cyan]")
        
        variables_extracted = extraction_results.get('variables_extracted', {})
        if not variables_extracted:
            console.print("  [dim]No patterns to extract[/dim]")
            return
        
        for var_name, result in variables_extracted.items():
            if result.get('success'):
                match_text = result.get('selected_match', 'N/A')
                keyword = result.get('keyword', 'N/A')
                
                # Show extraction details
                debug_info = result.get('debug_info', {})
                if isinstance(match_text, list):
                    # Multiple matches
                    console.print(f"  ✓ {var_name}: [yellow]{len(match_text)} matches found[/yellow] "
                                 f"(from '{keyword}')")
                    for i, match in enumerate(match_text[:3], 1):  # Show first 3
                        console.print(f"    {i}. \"{match}\"")
                    if len(match_text) > 3:
                        console.print(f"    ... and {len(match_text) - 3} more")
                else:
                    # Single match
                    pages_info = ""
                    if 'selected_from_page' in debug_info:
                        pages_info = f" (page {debug_info['selected_from_page']})"
                    elif 'pages_searched' in result and result['pages_searched']:
                        pages_info = f" (searched pages {', '.join(map(str, result['pages_searched']))})"
                    
                    console.print(f"  ✓ {var_name}: \"{match_text}\"{pages_info}")
                
                # Show warnings if any
                warnings = result.get('warnings', [])
                for warning in warnings:
                    console.print(f"    [yellow]⚠ {warning}[/yellow]")
                    
            else:
                error_msg = result.get('selected_match', 'Unknown error')
                keyword = result.get('keyword', 'N/A')
                console.print(f"  ✗ {var_name}: [red]{error_msg}[/red] (pattern '{keyword}')")
        
        # Show template result
        template_result = extraction_results.get('template_result', 'N/A')
        console.print(f"\n[cyan]Template result:[/cyan] {template_result}")
        
        # Show fallback status
        if extraction_results.get('fallback_used'):
            console.print(f"[yellow]Note: Using fallback naming due to extraction issues[/yellow]")
    
    def show_extraction_warnings(self, extraction_results: dict):
        """
        Show warnings for actual extraction operations.
        
        Args:
            extraction_results: Results from pattern extraction
        """
        warnings = []
        variables_extracted = extraction_results.get('variables_extracted', {})
        
        # Collect all warnings
        for var_name, result in variables_extracted.items():
            if not result.get('success'):
                error_msg = result.get('selected_match', 'Unknown error')
                warnings.append(f"{var_name}: {error_msg}")
            elif result.get('warnings'):
                for warning in result['warnings']:
                    warnings.append(f"{var_name}: {warning}")
        
        # Add general extraction errors
        for error in extraction_results.get('extraction_errors', []):
            warnings.append(error)
        
        # Show warnings if any
        if warnings:
            console.print(f"\n[yellow]Pattern extraction warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  ⚠ {warning}")
        
        # Show fallback notification
        if extraction_results.get('fallback_used'):
            console.print(f"[yellow]Using fallback naming due to pattern extraction issues[/yellow]")
    
    def show_batch_summary(self, processed_files: list, extraction_failures: list):
        """
        Show summary of batch operation with failure details.
        
        Args:
            processed_files: List of successfully processed files
            extraction_failures: List of files with extraction issues
        """
        console.print(f"\n[green]Processed {len(processed_files)} files successfully[/green]")
        
        if extraction_failures:
            console.print(f"\n[yellow]Pattern extraction issues in {len(extraction_failures)} files:[/yellow]")
            for failure in extraction_failures[:10]:  # Limit to first 10 to avoid spam
                console.print(f"  {failure['file']}: {failure['issue']}")
            
            if len(extraction_failures) > 10:
                console.print(f"  ... and {len(extraction_failures) - 10} more files with issues")
            
            console.print(f"\n[cyan]Files with extraction issues used fallback naming[/cyan]")
    
    def preview_filename_generation(self, original_path: Path, page_range_desc: str,
                                   patterns: list[str] = None, template: str = None,
                                   source_page: int = 1) -> dict:
        """
        Preview filename generation for demonstration purposes.
        
        Args:
            original_path: Path to original PDF file
            page_range_desc: Description of page range
            patterns: List of pattern strings
            template: Filename template
            source_page: Source page for extraction
            
        Returns:
            Dictionary with preview information
        """
        if not patterns or not template:
            simple_filename = f"{original_path.stem}_pages{page_range_desc}.pdf"
            return {
                'filename_preview': simple_filename,
                'extraction_preview': {},
                'would_conflict': original_path.parent / simple_filename in Path().iterdir(),
                'final_filename': simple_filename
            }
        
        # Simulate extraction for preview
        extraction_preview = {}
        try:
            parsed_patterns = self.pattern_processor.validate_pattern_list(patterns)
            
            for var_name, keyword, extraction_spec in parsed_patterns:
                # Create realistic simulated values
                simulated_value = self._generate_simulated_value(keyword, var_name)
                extraction_preview[var_name] = {
                    'keyword': keyword,
                    'simulated_value': simulated_value,
                    'extraction_spec': str(extraction_spec)
                }
        
        except Exception as e:
            return {
                'filename_preview': f"ERROR: {e}",
                'extraction_preview': {},
                'would_conflict': False,
                'final_filename': f"ERROR: {e}"
            }
        
        # Apply template with simulated values
        template_variables = {
            'original_name': original_path.stem,
            'range': page_range_desc,
            'page_count': self._estimate_page_count(page_range_desc)
        }
        
        for var_name, preview_info in extraction_preview.items():
            template_variables[var_name] = preview_info['simulated_value']
        
        try:
            filename_preview = self.template_engine.apply_template(template, template_variables)
            if not filename_preview.lower().endswith('.pdf'):
                filename_preview += '.pdf'
        except Exception as e:
            filename_preview = f"TEMPLATE_ERROR: {e}"
        
        # Check for conflicts
        proposed_path = original_path.parent / filename_preview
        would_conflict = proposed_path.exists()
        final_filename = self._resolve_conflicts(proposed_path).name if would_conflict else filename_preview
        
        return {
            'filename_preview': filename_preview,
            'extraction_preview': extraction_preview,
            'would_conflict': would_conflict,
            'final_filename': final_filename
        }
    
    def _generate_simulated_value(self, keyword: str, var_name: str) -> str:
        """
        Generate realistic simulated values for preview mode.
        
        Args:
            keyword: The search keyword
            var_name: Variable name
            
        Returns:
            Simulated value string
        """
        keyword_lower = keyword.lower()
        
        # Pattern matching for common business document fields
        if any(term in keyword_lower for term in ['invoice', 'inv']):
            return "INV-2024-001"
        elif any(term in keyword_lower for term in ['company', 'vendor', 'supplier']):
            return "ACME-Corp"
        elif any(term in keyword_lower for term in ['amount', 'total', 'sum']):
            return "1250-00"
        elif any(term in keyword_lower for term in ['date']):
            return "2024-01-15"
        elif any(term in keyword_lower for term in ['po', 'purchase']):
            return "PO-98765"
        elif any(term in keyword_lower for term in ['reference', 'ref']):
            return "REF-ABC123"
        elif any(term in keyword_lower for term in ['account', 'acct']):
            return "ACCT-456789"
        elif any(term in keyword_lower for term in ['order']):
            return "ORD-789456"
        else:
            # Generic fallback based on variable name
            return f"SAMPLE-{var_name.upper()}"
    
    def _estimate_page_count(self, page_range_desc: str) -> int:
        """
        Estimate number of pages from range description.
        
        Args:
            page_range_desc: Description like "01-03", "page05", etc.
            
        Returns:
            Estimated page count
        """
        # Handle common range formats
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
        
        # Single page or unknown format
        return 1
    
    def _resolve_conflicts(self, proposed_path: Path) -> Path:
        """
        Resolve filename conflicts by appending _copy_01, _copy_02, etc.
        
        Args:
            proposed_path: Proposed output path
            
        Returns:
            Unique path that doesn't conflict with existing files
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


# End of file #
