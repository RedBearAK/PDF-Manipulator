"""
Run all tests for Simple PDF Scraper.

Master test runner that executes all test modules and provides
a combined score and summary.
"""

import sys

from pathlib import Path

# Add both current directory (for test modules) and parent directory (for package) to path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent

sys.path.insert(0, str(current_dir))  # For importing test modules
sys.path.insert(0, str(parent_dir))   # For importing simple_pdf_scraper package

import test_processors
import test_extractors
import test_integration


def run_all_tests():
    """Run all test modules and provide combined results."""
    print("Simple PDF Scraper - Test Suite")
    print("=" * 60)
    print()
    
    test_modules = [
        ("Processors", test_processors),
        ("Extractors", test_extractors), 
        ("Integration", test_integration)
    ]
    
    all_results = []
    total_passed = 0
    total_tests = 0
    
    for module_name, test_module in test_modules:
        print(f"Running {module_name} Tests...")
        success, results = test_module.run_tests()
        
        module_passed = sum(1 for _, passed, _ in results if passed)
        module_total = len(results)
        
        total_passed += module_passed
        total_tests += module_total
        
        all_results.extend([(module_name, name, passed, msg) for name, passed, msg in results])
        print()
    
    # Print summary
    print("=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    
    # Show failed tests
    failed_tests = [(module, name, msg) for module, name, passed, msg in all_results if not passed]
    if failed_tests:
        print("\nFAILED TESTS:")
        for module, name, msg in failed_tests:
            print(f"  {module}::{name} - {msg}")
    
    # Show overall stats
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\nOVERALL RESULTS:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_tests - total_passed}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    # Show module breakdown
    print(f"\nMODULE BREAKDOWN:")
    for module_name, test_module in test_modules:
        module_results = [(n, p, m) for mod, n, p, m in all_results if mod == module_name]
        module_passed = sum(1 for _, passed, _ in module_results if passed)
        module_total = len(module_results)
        module_rate = (module_passed / module_total * 100) if module_total > 0 else 0
        print(f"  {module_name:12}: {module_passed:2}/{module_total:2} ({module_rate:5.1f}%)")
    
    print("\n" + "=" * 60)
    
    # Return success if all tests passed
    return total_passed == total_tests


def main():
    """Main entry point."""
    success = run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
