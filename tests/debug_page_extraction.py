#!/usr/bin/env python3
"""
Debug script to check what each search pattern is finding.
File: debug_page_extraction.py

Run: python debug_page_extraction.py
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports  
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pdf_manipulator.core.page_range.patterns import split_comma_respecting_quotes
    from pdf_manipulator.core.page_range.file_selector import FileSelector
    from pdf_manipulator.core.page_range.page_range_parser import PageRangeParser
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import functions: {e}")
    IMPORTS_AVAILABLE = False


def debug_individual_searches():
    """Debug what each individual search pattern finds."""
    if not IMPORTS_AVAILABLE:
        print("Cannot run debug - imports not available")
        return
    
    # Your PDF path
    pdf_path = Path("/Users/mmf/Dropbox/Tech_Support/00_SBS_Test_Files/02-extracting/20250816143441_OCRd.pdf")
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    # Load and expand the file selector
    try:
        file_selector = FileSelector(base_path=pdf_path.parent)
        expanded = file_selector.expand_file_selectors("file:alaska_cities.txt")
        print(f"Expanded content:\n{expanded}\n")
        
        # Split into individual searches using quote-aware splitting
        parts = split_comma_respecting_quotes(expanded)
        print(f"Found {len(parts)} individual search patterns:")
        
        parser = PageRangeParser(total_pages=73, pdf_path=pdf_path)
        total_pages_found = set()
        
        for i, part in enumerate(parts, 1):
            part = part.strip()
            if not part:
                continue
                
            print(f"\n{i}. Pattern: '{part}'")
            
            try:
                pages_set, description, groups = parser.parse(part)
                pages_list = sorted(list(pages_set))
                
                print(f"   Found {len(pages_list)} pages: {pages_list}")
                print(f"   Groups: {len(groups)}")
                
                for j, group in enumerate(groups):
                    if hasattr(group, 'pages'):
                        group_pages = sorted(group.pages) if hasattr(group.pages, '__iter__') else [group.pages]
                        print(f"     Group {j+1}: {len(group_pages)} pages - {group_pages}")
                
                total_pages_found.update(pages_set)
                
            except Exception as e:
                print(f"   ERROR: {e}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Total unique pages found: {len(total_pages_found)}")
        print(f"All pages: {sorted(list(total_pages_found))}")
        
        if len(total_pages_found) != 57:
            print(f"⚠️  Mismatch! Debug showed {len(total_pages_found)} pages, but command showed 57")
        
    except Exception as e:
        print(f"Error during debugging: {e}")


def debug_display_logic():
    """Debug the display logic to see why '7 groups' shows only 7 single pages."""
    print("\n=== DEBUGGING DISPLAY LOGIC ===")
    print("The issue might be:")
    print("1. Boolean expressions are only finding 1 page each")
    print("2. Display code is not showing all groups properly") 
    print("3. Grouping logic is flattening multi-page groups")
    print("\nTo debug further, we'd need to see:")
    print("- What each boolean expression actually returns")
    print("- How the UI code formats the group display")


if __name__ == "__main__":
    print("=== DEBUGGING PAGE EXTRACTION ===")
    debug_individual_searches()
    debug_display_logic()
