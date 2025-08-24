#!/usr/bin/env python3
"""
Debug script to identify why deduplication imports are failing.
File: tests/debug_imports.py
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"🔍 Debugging imports from: {project_root}")
print(f"📂 Python path includes: {project_root}")

def test_deduplication_import():
    """Test importing the deduplication module step by step."""
    print("\n=== Testing Deduplication Import ===")
    
    # Test 1: Basic module import
    try:
        import pdf_manipulator
        print("✓ pdf_manipulator package imports successfully")
    except ImportError as e:
        print(f"✗ pdf_manipulator package import failed: {e}")
        return False
    
    # Test 2: Core package import  
    try:
        import pdf_manipulator.core
        print("✓ pdf_manipulator.core package imports successfully")
    except ImportError as e:
        print(f"✗ pdf_manipulator.core package import failed: {e}")
        return False
    
    # Test 3: Deduplication module import
    try:
        import pdf_manipulator.core.deduplication
        print("✓ pdf_manipulator.core.deduplication module imports successfully")
    except ImportError as e:
        print(f"✗ pdf_manipulator.core.deduplication module import failed: {e}")
        print(f"   Expected file location: {project_root}/pdf_manipulator/core/deduplication.py")
        
        # Check if file exists
        dedup_file = project_root / "pdf_manipulator" / "core" / "deduplication.py"
        if dedup_file.exists():
            print(f"   ✓ File exists at: {dedup_file}")
        else:
            print(f"   ✗ File missing at: {dedup_file}")
        return False
    
    # Test 4: Specific function imports
    try:
        from pdf_manipulator.core.deduplication import detect_duplicates, apply_deduplication_strategy
        print("✓ deduplication functions import successfully")
        print(f"   detect_duplicates: {detect_duplicates}")
        print(f"   apply_deduplication_strategy: {apply_deduplication_strategy}")
    except ImportError as e:
        print(f"✗ deduplication functions import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ deduplication functions import failed with unexpected error: {e}")
        return False
    
    return True


def test_operations_import():
    """Test importing operations module and its functions."""
    print("\n=== Testing Operations Import ===")
    
    try:
        from pdf_manipulator.core.operations import (
            extract_pages, 
            extract_pages_grouped,
            get_ordered_pages_from_groups
        )
        print("✓ operations functions import successfully")
    except ImportError as e:
        print(f"✗ operations functions import failed: {e}")
        return False
    
    # Test the missing function that should trigger an error
    try:
        from pdf_manipulator.core.operations import extract_pages_separate
        print("✓ extract_pages_separate imports successfully")
    except ImportError as e:
        print(f"✗ extract_pages_separate import failed: {e}")
        print("   This is expected - function is missing!")
        return False
    
    return True


def test_dependencies():
    """Test if there are any dependency issues causing import failures."""
    print("\n=== Testing Dependencies ===")
    
    # Test rich (used by deduplication module)
    try:
        from rich.console import Console
        print("✓ rich.console imports successfully")
    except ImportError as e:
        print(f"✗ rich.console import failed: {e}")
        return False
    
    # Test pypdf (used by operations)
    try:
        from pypdf import PdfReader, PdfWriter
        print("✓ pypdf imports successfully")
    except ImportError as e:
        print(f"✗ pypdf import failed: {e}")
        return False
    
    return True


def run_all_import_tests():
    """Run all import debugging tests."""
    print("🧪 Import Debugging for PDF Manipulator")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    if test_dependencies():
        tests_passed += 1
    
    if test_deduplication_import():
        tests_passed += 1
        
    if test_operations_import():
        tests_passed += 1
    
    print(f"\n📊 Import Tests: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All imports working! The issue must be elsewhere.")
    else:
        print("⚠️  Import issues detected. Check the failed imports above.")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    success = run_all_import_tests()
    sys.exit(0 if success else 1)


# End of file #
