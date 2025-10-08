"""
Operation Context - Class-Based Centralized State Management
File: pdf_manipulator/core/operation_context.py

Class-based utility that eliminates parameter proliferation and provides
comprehensive caching for all parsing operations. No instances needed.

ARCHITECTURE:
- Class attributes hold all operation state AND comprehensive cached results
- Direct access: OperationContext.set_args(args), OperationContext.get_cached_parsing_results()
- Prevents instantiation with clear error message  
- Matches StageManager pattern from Excel-Recipe-Processor
- Universal caching that handles ALL parsing parameters
"""

import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParsedResults:
    """Immutable container for comprehensive parsed page range results."""
    pdf_path: Path
    page_range_arg: str
    selected_pages: set[int]
    range_description: str
    page_groups: list
    total_page_count: int
    filter_matches: Optional[str]
    group_start: Optional[str]
    group_end: Optional[str]
    cache_timestamp: datetime
    cache_key: str
    
    def __str__(self):
        return (f"ParsedResults({len(self.selected_pages)} pages, "
                f"{len(self.page_groups)} groups, {self.range_description})")


class OperationContext:
    """
    Centralized context for PDF manipulation operations.
    
    Class-based utility with no instances needed. Use directly:
        OperationContext.set_args(args)
        OperationContext.set_current_pdf(path, count)
        cached = OperationContext.get_cached_parsing_results()
    
    Eliminates parameter proliferation by providing direct access to:
    - Parsed command line arguments and enhanced arguments
    - Current PDF being processed  
    - Operation patterns, templates, and configuration
    - Comprehensive cached parsing results (ALL parameters)
    - All operation state and statistics
    """
    
    # =============================================================================
    # CORE OPERATION STATE
    # =============================================================================
    
    # Core arguments
    args = None                         # Original parsed arguments
    enhanced_args = None                # Processed enhanced arguments
    
    # Operation configuration
    patterns = None                     # Pattern extraction patterns
    template = None                     # Filename template  
    source_page = 1                     # Default source page for patterns
    
    # Current PDF context
    current_pdf_path = None             # Current PDF being processed
    current_page_count = None           # Total pages in current PDF
    
    # Operation modes and settings
    dry_run = False
    interactive = True
    batch_mode = False
    
    # Deduplication and conflict settings
    dedup_strategy = 'strict'
    conflict_strategy = 'ask'
    
    # Naming settings
    use_timestamp = False
    custom_prefix = None
    smart_names = False
    
    # State tracking
    operation_start_time = None
    pdfs_processed = 0
    
    # =============================================================================
    # SIMPLE PARSING RESULTS STORAGE
    # =============================================================================
    
    # Simple results storage - either None or contains the results for this operation
    parsed_results = None
    
    def __new__(cls, *args, **kwargs):
        """Prevent instantiation - use class methods directly."""
        raise RuntimeError(
            "OperationContext should not be instantiated. "
            "Use class methods directly: OperationContext.set_args(args)"
        )
    
    @classmethod
    def reset(cls):
        """Reset all state (mainly for testing)."""
        # Reset core state
        cls.args = None
        cls.enhanced_args = None
        cls.patterns = None
        cls.template = None
        cls.source_page = 1
        cls.current_pdf_path = None
        cls.current_page_count = None
        cls.dry_run = False
        cls.interactive = True
        cls.batch_mode = False
        cls.dedup_strategy = 'strict'
        cls.conflict_strategy = 'ask'
        cls.use_timestamp = False
        cls.custom_prefix = None
        cls.smart_names = False
        cls.operation_start_time = None
        cls.pdfs_processed = 0
        
        # Reset simple results storage
        cls.parsed_results = None
    
    # =============================================================================
    # CORE OPERATION CONTEXT METHODS  
    # =============================================================================
    
    @classmethod
    def set_args(cls, args: argparse.Namespace):
        """
        Set the parsed arguments and extract operation configuration.
        
        This is the main entry point - call this first with parsed CLI args.
        Automatically extracts and sets all relevant configuration.
        """
        # Guard clause
        if not isinstance(args, argparse.Namespace):
            raise ValueError("args must be an argparse.Namespace object")
        
        cls.args = args
        
        # Extract enhanced arguments (batch mode logic, etc.)
        cls.enhanced_args = cls._extract_enhanced_args(args)
        
        # Extract operation configuration from args
        cls.batch_mode = getattr(args, 'batch', False)
        cls.dry_run = getattr(args, 'dry_run', False) 
        cls.interactive = not cls.batch_mode  # Batch mode is never interactive
        
        # Pattern extraction settings
        cls.patterns = getattr(args, 'scrape_pattern', None)
        cls.template = getattr(args, 'filename_template', None)
        cls.source_page = getattr(args, 'pattern_source_page', 1)
        
        # Load patterns from file if specified
        patterns_file = getattr(args, 'scrape_patterns_file', None)
        if patterns_file:
            cls.patterns = cls._load_patterns_from_file(patterns_file)
        
        # Deduplication strategy
        cls.dedup_strategy = cls._determine_dedup_strategy(args)
        
        # Conflict resolution strategy  
        cls.conflict_strategy = cls._determine_conflict_strategy(args)
        
        # Naming options
        cls.use_timestamp = getattr(args, 'use_timestamp', False)
        cls.custom_prefix = getattr(args, 'custom_prefix', None)
        cls.smart_names = cls.patterns is not None and cls.template is not None
        
        # Initialize operation timing
        cls.operation_start_time = datetime.now()
    
    @classmethod
    def set_current_pdf(cls, pdf_path: Path, page_count: int):
        """
        Set the current PDF being processed.
        
        Args:
            pdf_path: Path to current PDF file
            page_count: Total pages in current PDF
        """
        # Guard clauses
        if not isinstance(pdf_path, Path):
            raise ValueError("pdf_path must be a Path object")
        if not isinstance(page_count, int) or page_count <= 0:
            raise ValueError("page_count must be a positive integer")
        
        cls.current_pdf_path = pdf_path
        cls.current_page_count = page_count

        # CRITICAL: Clear cached parsing results when switching PDFs
        cls.parsed_results = None
    
    @classmethod
    def get_page_range_arg(cls):
        """
        Get the page range argument for the current operation.
        
        Returns:
            The page range string (e.g., "1-5", "file:gxy_cities_sorted.txt")
        """
        if not cls.args:
            raise RuntimeError("Arguments not set. Call OperationContext.set_args() first.")
        
        return getattr(cls.args, 'extract_pages', None)
    
    @classmethod
    def get_current_pdf_info(cls):
        """
        Get current PDF information.
        
        Returns:
            Tuple of (pdf_path, page_count) or (None, None) if not set
        """
        return cls.current_pdf_path, cls.current_page_count
    
    @classmethod
    def increment_processed_count(cls):
        """Increment the count of PDFs processed."""
        cls.pdfs_processed += 1
    
    @classmethod
    def requires_pdf_context(cls, operation_name="operation"):
        """
        Ensure current PDF context is set, raise error if not.
        
        Args:
            operation_name: Name of operation for error message
        """
        if not cls.current_pdf_path or not cls.current_page_count:
            raise RuntimeError(
                f"Cannot perform {operation_name}: no current PDF context set. "
                f"Call OperationContext.set_current_pdf() first."
            )
    
    @classmethod
    def has_args(cls):
        """Check if arguments have been set."""
        return cls.args is not None
    
    # =============================================================================
    # SIMPLE PARSING RESULTS STORAGE
    # =============================================================================
    
    @classmethod
    def store_parsed_results(cls, selected_pages: set[int], range_description: str, 
                           page_groups: list):
        """
        Store parsing results for the current operation.
        
        Args:
            selected_pages: Set of selected page numbers
            range_description: Human-readable description  
            page_groups: List of PageGroup objects
        """
        cls.requires_pdf_context("store parsing results")
        
        if not cls.args:
            raise RuntimeError("Arguments not set. Call OperationContext.set_args() first.")
        
        # Create simple results object
        cls.parsed_results = ParsedResults(
            pdf_path=cls.current_pdf_path,
            page_range_arg=cls.get_page_range_arg(),
            selected_pages=selected_pages,
            range_description=range_description, 
            page_groups=page_groups,
            total_page_count=cls.current_page_count,
            filter_matches=getattr(cls.args, 'filter_matches', None),
            group_start=getattr(cls.args, 'group_start', None),
            group_end=getattr(cls.args, 'group_end', None),
            cache_timestamp=datetime.now(),
            cache_key="simple"  # Not used in simple mode
        )
    
    @classmethod  
    def get_cached_parsing_results(cls) -> Optional[ParsedResults]:
        """
        Get parsing results if they exist for current operation.
        
        Returns:
            ParsedResults if available, None otherwise
        """
        return cls.parsed_results
    
    @classmethod
    def has_parsed_results(cls) -> bool:
        """Check if parsing results are available."""
        return cls.parsed_results is not None
    
    @classmethod
    def clear_parsed_results(cls):
        """Clear stored parsing results."""
        cls.parsed_results = None
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    @classmethod
    def _extract_enhanced_args(cls, args: argparse.Namespace) -> dict:
        """Extract and process enhanced arguments with batch mode logic."""
        enhanced = {}
        
        # Batch mode processing
        enhanced['interactive'] = not getattr(args, 'batch', False)
        
        # Conflict strategy with batch mode conversion
        conflicts = getattr(args, 'conflicts', 'ask')
        if getattr(args, 'batch', False) and conflicts == 'ask':
            enhanced['conflict_strategy'] = 'rename'  # Convert ask to rename in batch mode
        else:
            enhanced['conflict_strategy'] = conflicts
            
        # Other enhanced settings
        enhanced['dry_run'] = getattr(args, 'dry_run', False)
        enhanced['use_timestamp'] = getattr(args, 'use_timestamp', False)
        
        return enhanced
    
    @classmethod
    def _determine_dedup_strategy(cls, args: argparse.Namespace) -> str:
        """Determine deduplication strategy from arguments."""
        if hasattr(args, 'dedup') and args.dedup:
            return args.dedup
        elif hasattr(args, 'respect_groups') and args.respect_groups:
            return 'groups' 
        elif hasattr(args, 'separate_files') and args.separate_files:
            return 'strict'
        else:
            return 'strict'
    
    @classmethod
    def _determine_conflict_strategy(cls, args: argparse.Namespace) -> str:
        """Determine conflict resolution strategy from arguments."""
        strategy = getattr(args, 'conflicts', 'ask')
        
        # Batch mode never uses 'ask' - convert to safer default
        if getattr(args, 'batch', False) and strategy == 'ask':
            return 'rename'
        
        return strategy
    
    @classmethod
    def _load_patterns_from_file(cls, patterns_file: str) -> list[str]:
        """Load patterns from file."""
        try:
            with open(patterns_file, 'r') as f:
                patterns = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        patterns.append(line)
                return patterns
        except Exception as e:
            raise ValueError(f"Error reading patterns file {patterns_file}: {e}")
    
    @classmethod
    def print_summary(cls):
        """Print a summary of the current operation context (for debugging)."""
        print("🔧 OperationContext Summary:")
        print(f"   Mode: {'Batch' if cls.batch_mode else 'Interactive'}")
        print(f"   Dry run: {cls.dry_run}")
        print(f"   Page range: {cls.get_page_range_arg() if cls.args else 'None'}")
        print(f"   Current PDF: {cls.current_pdf_path.name if cls.current_pdf_path else 'None'}")
        print(f"   Page count: {cls.current_page_count}")
        print(f"   Patterns: {len(cls.patterns) if cls.patterns else 0}")
        print(f"   Template: {cls.template}")
        print(f"   PDFs processed: {cls.pdfs_processed}")
        print(f"   Has parsed results: {cls.has_parsed_results()}")


# Convenience alias for shorter reference
OpCtx = OperationContext


# =============================================================================
# CONVENIENCE FUNCTIONS (simplified)
# =============================================================================

def get_cached_parsing_results() -> Optional[ParsedResults]:
    """Convenience function - get parsing results if they exist."""
    return OperationContext.get_cached_parsing_results()

def store_parsing_results(selected_pages: set[int], range_description: str, page_groups: list):
    """Convenience function - store parsing results using current context.""" 
    OperationContext.store_parsed_results(selected_pages, range_description, page_groups)

def get_parsed_pages():
    """
    Convenience function - get parsed pages from stored results or raise error.
    
    Returns:
        Tuple of (selected_pages, range_description, page_groups)
    """
    cached = get_cached_parsing_results()
    if cached:
        return cached.selected_pages, cached.range_description, cached.page_groups
    else:
        raise RuntimeError(
            "No parsing results stored yet. Parse the page range first using "
            "parse_page_range_from_args() and store the results."
        )


# End of file #
