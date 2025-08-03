"""
Test Runner for PDF Manipulator
Run: python tests/run_tests.py

Runs all or specific test modules for the PDF manipulator page range functionality.
"""

import sys
import subprocess
from pathlib import Path


def run_test_module(module_name):
    """Run a specific test module and return success status."""
    try:
        print(f"\n{'='*60}")
        print(f"RUNNING: {module_name}")
        print('='*60)
        
        # Run the test module directly
        test_file = Path(__file__).parent / f"{module_name}.py"
        
        if not test_file.exists():
            print(f"ERROR: Test file {test_file} does not exist")
            return False
        
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True)
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR running {module_name}: {e}")
        return False


def main():
    """Main test runner."""
    
    # Available test modules
    test_modules = [
        ('test_basic_page_ranges', 'Basic Page Range Parsing'),
        ('test_pattern_matching', 'Pattern Matching'),
        ('test_simple_boolean', 'Simple Boolean Expressions'),
        ('test_range_patterns', 'Range Patterns ("X to Y")'),
        ('test_magazine_processing', 'Magazine Processing (Advanced Boolean)'),
    ]
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Run specific test module
        module_name = sys.argv[1]
        
        # Remove 'test_' prefix if provided
        if module_name.startswith('test_'):
            module_name = module_name[5:]
        
        # Add 'test_' prefix
        full_module_name = f'test_{module_name}'
        
        # Check if module exists
        available_modules = [name for name, desc in test_modules]
        if full_module_name not in available_modules:
            print(f"Unknown test module: {module_name}")
            print(f"Available modules: {', '.join([name[5:] for name in available_modules])}")
            return 1
        
        # Run single module
        success = run_test_module(full_module_name)
        return 0 if success else 1
    
    else:
        # Run all test modules
        print("PDF MANIPULATOR TEST SUITE")
        print("=" * 60)
        print("Running all test modules...\n")
        
        results = []
        for module_name, description in test_modules:
            success = run_test_module(module_name)
            results.append((module_name, description, success))
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        
        passed = 0
        total = len(results)
        
        for module_name, description, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {description}")
            if success:
                passed += 1
        
        print(f"\n{passed}/{total} test modules passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1


def show_help():
    """Show help information."""
    print("""
PDF Manipulator Test Runner

Usage:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py <module_name>      # Run specific test

Available test modules:
  basic_page_ranges     - Test basic page range parsing (numbers, ranges, slicing)
  pattern_matching      - Test content-based pattern selection
  simple_boolean        - Test basic boolean expressions (AND, OR, NOT)
  range_patterns        - Test range patterns ("X to Y")
  magazine_processing   - Test advanced boolean with range patterns

Examples:
  python tests/run_tests.py
  python tests/run_tests.py basic_page_ranges
  python tests/run_tests.py boolean
  python tests/run_tests.py magazine

You can also run individual tests directly:
  python tests/test_basic_page_ranges.py
  python tests/test_simple_boolean.py
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        sys.exit(0)
    
    sys.exit(main())
