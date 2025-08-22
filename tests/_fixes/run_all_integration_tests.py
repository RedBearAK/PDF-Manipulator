#!/usr/bin/env python3
"""
Comprehensive Test Runner for Page Range Parser Architecture Fix
File: tests/run_all_integration_tests.py

Runs all integration test suites in order and provides comprehensive reporting.
This is the master test suite that validates the entire architecture fix.

Usage:
    python tests/run_all_integration_tests.py                    # Run all tests
    python tests/run_all_integration_tests.py --quick           # Run essential tests only
    python tests/run_all_integration_tests.py --critical        # Run critical tests only
    python tests/run_all_integration_tests.py --verbose         # Detailed output

Test Suites:
1. Comprehensive Integration Tests  - Full functionality testing
2. Alaska Cities Critical Test      - The specific failing case  
3. Edge Cases and Stress Tests      - Robustness and performance
4. CLI Integration Tests            - Command-line interface testing
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestSuite:
    """Represents a test suite to run."""
    
    def __init__(self, name: str, script_path: str, description: str, critical: bool = False):
        self.name = name
        self.script_path = script_path
        self.description = description
        self.critical = critical
        self.result = None
        self.duration = None
        self.output = ""
        self.error = ""

class ComprehensiveTestRunner:
    """Runs all integration test suites and provides comprehensive reporting."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        self.suites = []
        self.setup_test_suites()
        
    def setup_test_suites(self):
        """Set up all test suites to run."""
        test_dir = Path(__file__).parent
        
        self.suites = [
            TestSuite(
                "Critical Alaska Cities Test",
                str(test_dir / "test_alaska_cities_critical.py"),
                "Tests the specific complex command that was failing",
                critical=True
            ),
            TestSuite(
                "Comprehensive Integration Tests", 
                str(test_dir / "test_comprehensive_integration.py"),
                "Full functionality testing with real PDFs",
                critical=True
            ),
            TestSuite(
                "Edge Cases and Stress Tests",
                str(test_dir / "test_edge_cases_stress.py"), 
                "Robustness, performance, and edge case testing",
                critical=False
            ),
            TestSuite(
                "CLI Integration Tests",
                str(test_dir / "test_cli_integration.py"),
                "Command-line interface integration testing", 
                critical=False
            ),
        ]
    
    def run_all_tests(self, quick: bool = False, critical_only: bool = False):
        """Run all test suites."""
        self.start_time = datetime.now()
        
        print("🚀 COMPREHENSIVE INTEGRATION TEST RUNNER")
        print("="*70)
        print("Testing the complete Page Range Parser architecture fix")
        print(f"Started: {self.start_time}")
        print()
        
        # Filter suites based on options
        suites_to_run = self.suites
        if critical_only:
            suites_to_run = [s for s in self.suites if s.critical]
            print("🎯 Running CRITICAL TESTS ONLY")
        elif quick:
            # For quick tests, run first two suites only
            suites_to_run = self.suites[:2] 
            print("⚡ Running QUICK TESTS")
        else:
            print("🔬 Running ALL INTEGRATION TESTS")
        
        print(f"Test suites to run: {len(suites_to_run)}")
        print()
        
        # Run each test suite
        for i, suite in enumerate(suites_to_run, 1):
            print(f"{'='*70}")
            print(f"🧪 TEST SUITE {i}/{len(suites_to_run)}: {suite.name}")
            print(f"📋 {suite.description}")
            print(f"🏃 Running: {suite.script_path}")
            print()
            
            suite_start = time.time()
            
            try:
                self.run_test_suite(suite)
            except KeyboardInterrupt:
                print("\n⏹️  Test run interrupted by user")
                suite.result = "INTERRUPTED"
                break
            except Exception as e:
                print(f"\n💥 Test suite runner crashed: {e}")
                suite.result = "CRASHED"
            
            suite.duration = time.time() - suite_start
            
            # Show immediate result
            self.show_suite_result(suite, i, len(suites_to_run))
            print()
        
        self.end_time = datetime.now()
        
        # Generate comprehensive report
        self.generate_final_report(suites_to_run)
        
        # Return overall success
        return self.calculate_overall_success(suites_to_run)
    
    def run_test_suite(self, suite: TestSuite):
        """Run a single test suite."""
        # Check if test script exists
        if not Path(suite.script_path).exists():
            suite.result = "MISSING"
            suite.error = f"Test script not found: {suite.script_path}"
            return
        
        try:
            # Run the test script
            process = subprocess.run(
                [sys.executable, suite.script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test suite
            )
            
            suite.output = process.stdout
            suite.error = process.stderr
            
            if process.returncode == 0:
                suite.result = "PASSED"
            else:
                suite.result = "FAILED"
                
        except subprocess.TimeoutExpired:
            suite.result = "TIMEOUT"
            suite.error = "Test suite timed out after 5 minutes"
            
        except Exception as e:
            suite.result = "ERROR"
            suite.error = str(e)
    
    def show_suite_result(self, suite: TestSuite, current: int, total: int):
        """Show the result of a test suite."""
        duration_str = f"{suite.duration:.1f}s" if suite.duration else "N/A"
        
        if suite.result == "PASSED":
            print(f"✅ {suite.name} PASSED ({duration_str})")
            if self.verbose and suite.output:
                print("📋 Output highlights:")
                # Show last few lines of output
                lines = suite.output.strip().split('\n')
                for line in lines[-5:]:
                    if line.strip():
                        print(f"   {line}")
        
        elif suite.result == "FAILED":
            print(f"❌ {suite.name} FAILED ({duration_str})")
            if suite.error:
                print("💔 Error details:")
                error_lines = suite.error.strip().split('\n')
                for line in error_lines[:10]:  # Show first 10 lines of error
                    if line.strip():
                        print(f"   {line}")
        
        elif suite.result == "TIMEOUT":
            print(f"⏰ {suite.name} TIMED OUT ({duration_str})")
            
        elif suite.result == "MISSING":
            print(f"📁 {suite.name} MISSING")
            print(f"   Script not found: {suite.script_path}")
            
        elif suite.result == "INTERRUPTED":
            print(f"⏹️  {suite.name} INTERRUPTED")
            
        else:
            print(f"💥 {suite.name} CRASHED ({duration_str})")
            if suite.error:
                print(f"   Error: {suite.error}")
    
    def generate_final_report(self, suites_run):
        """Generate comprehensive final report."""
        print("="*70)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("="*70)
        
        total_duration = self.end_time - self.start_time
        
        print(f"⏱️  Total runtime: {total_duration}")
        print(f"🧪 Test suites run: {len(suites_run)}")
        print()
        
        # Results summary
        results = {}
        for suite in suites_run:
            result = suite.result or "UNKNOWN"
            results[result] = results.get(result, 0) + 1
        
        print("📈 Results Summary:")
        for result, count in sorted(results.items()):
            icon = {
                "PASSED": "✅",
                "FAILED": "❌", 
                "TIMEOUT": "⏰",
                "MISSING": "📁",
                "INTERRUPTED": "⏹️",
                "CRASHED": "💥",
                "ERROR": "🚨"
            }.get(result, "❓")
            print(f"   {icon} {result}: {count}")
        
        print()
        
        # Detailed results
        print("📋 Detailed Results:")
        for i, suite in enumerate(suites_run, 1):
            duration_str = f"{suite.duration:.1f}s" if suite.duration else "N/A"
            critical_mark = " 🎯" if suite.critical else ""
            
            result_icon = {
                "PASSED": "✅",
                "FAILED": "❌",
                "TIMEOUT": "⏰", 
                "MISSING": "📁",
                "INTERRUPTED": "⏹️",
                "CRASHED": "💥",
                "ERROR": "🚨"
            }.get(suite.result, "❓")
            
            print(f"   {i}. {result_icon} {suite.name}{critical_mark}")
            print(f"      Duration: {duration_str}")
            print(f"      Description: {suite.description}")
            
            if suite.result == "FAILED" and suite.error:
                print(f"      Error: {suite.error[:100]}...")
            elif suite.result == "PASSED" and self.verbose:
                print(f"      Success ✨")
            
            print()
    
    def calculate_overall_success(self, suites_run) -> bool:
        """Calculate overall success based on results."""
        if not suites_run:
            return False
        
        # Critical tests must all pass
        critical_suites = [s for s in suites_run if s.critical]
        critical_passed = all(s.result == "PASSED" for s in critical_suites)
        
        # At least 75% of all tests should pass
        passed_count = sum(1 for s in suites_run if s.result == "PASSED")
        pass_rate = passed_count / len(suites_run)
        
        overall_success = critical_passed and pass_rate >= 0.75
        
        print("🎯 SUCCESS CRITERIA:")
        print(f"   Critical tests passed: {critical_passed} ({len([s for s in critical_suites if s.result == 'PASSED'])}/{len(critical_suites)})")
        print(f"   Overall pass rate: {pass_rate:.1%} ({passed_count}/{len(suites_run)}) - Need ≥75%")
        print()
        
        if overall_success:
            print("🎉 OVERALL SUCCESS!")
            print("The Page Range Parser architecture fix is working correctly!")
            print("✨ Key achievements:")
            print("   • Comma parsing happens first (architectural fix)")
            print("   • Boolean expressions work with complex nesting")
            print("   • Pattern matching works with quoted commas")
            print("   • Mixed comma-separated arguments work")
            print("   • The Alaska cities command now works!")
        else:
            print("💔 OVERALL FAILURE")
            if not critical_passed:
                print("❌ Critical tests failed - core functionality broken")
            if pass_rate < 0.75:
                print(f"❌ Pass rate too low: {pass_rate:.1%} (need ≥75%)")
            print("The architecture fix needs more work.")
        
        return overall_success
    
    def show_usage_examples(self):
        """Show examples of the fixed functionality."""
        if not self.calculate_overall_success(self.suites):
            return
            
        print("\n" + "="*70)
        print("💡 USAGE EXAMPLES - These should now work:")
        print("="*70)
        
        examples = [
            "# Simple comma-separated patterns:",
            'pdf-manipulator --extract-pages=\'contains:"CITY, STATE",contains:"OTHER, STATE"\' file.pdf',
            "",
            "# Complex boolean expressions:",
            'pdf-manipulator --extract-pages=\'contains:"A" | contains:"B"\' file.pdf',
            "",
            "# Mixed comma-separated with boolean:",
            'pdf-manipulator --extract-pages=\'1-5,contains:"Chapter" | contains:"Summary",10-15\' file.pdf',
            "",
            "# The original failing Alaska cities command:",
            'pdf-manipulator --extract-pages=\'\\',
            '  contains:"CORDOVA, AK",\\',
            '  contains:"CRAIG, AK",\\', 
            '  contains:"SITKA AK" | contains:"SITKA, AK",\\',
            '  (boolean expression with exclusions)\' file.pdf',
        ]
        
        for example in examples:
            if example.startswith("#"):
                print(f"\033[36m{example}\033[0m")  # Cyan for comments
            elif example == "":
                print()
            else:
                print(f"  {example}")


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive integration tests for Page Range Parser architecture fix"
    )
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Run essential tests only (faster)"
    )
    parser.add_argument(
        "--critical", 
        action="store_true", 
        help="Run critical tests only"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    # Run the comprehensive test suite
    runner = ComprehensiveTestRunner(verbose=args.verbose)
    success = runner.run_all_tests(
        quick=args.quick,
        critical_only=args.critical
    )
    
    # Show usage examples if successful
    if success:
        runner.show_usage_examples()
    
    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test run interrupted by user")
        sys.exit(2)


# End of file #
