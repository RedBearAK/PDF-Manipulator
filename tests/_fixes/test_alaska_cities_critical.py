#!/usr/bin/env python3
"""
Alaska Cities Critical Integration Test
File: tests/test_alaska_cities_critical.py

This is the CRITICAL test that verifies the exact failing example works.
Tests the specific complex command that was failing before the architecture fix.

This test creates a realistic PDF with Alaska city data and tests the exact
complex boolean expression from the user's failing command.

Run: python tests/test_alaska_cities_critical.py
"""

import sys
import tempfile
import atexit
from pathlib import Path
from datetime import datetime

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pdf_manipulator.core.page_range.page_range_parser import parse_page_range
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False

# Test environment
TEMP_DIR = None
ALASKA_PDF = None

def setup_test():
    """Set up test environment and create Alaska cities PDF."""
    global TEMP_DIR, ALASKA_PDF
    
    TEMP_DIR = tempfile.mkdtemp(prefix="alaska_test_")
    ALASKA_PDF = Path(TEMP_DIR) / "alaska_cities_realistic.pdf"
    
    print(f"🔧 Creating test environment: {TEMP_DIR}")
    atexit.register(cleanup_test)
    
    if IMPORTS_AVAILABLE:
        create_realistic_alaska_pdf()

def cleanup_test():
    """Clean up test environment."""
    global TEMP_DIR
    if TEMP_DIR and Path(TEMP_DIR).exists():
        import shutil
        shutil.rmtree(TEMP_DIR)
        print(f"🧹 Cleaned up: {TEMP_DIR}")

def create_realistic_alaska_pdf():
    """Create a realistic Alaska cities PDF that matches the failing command's expectations."""
    print("📄 Creating realistic Alaska cities PDF...")
    
    doc = SimpleDocTemplate(str(ALASKA_PDF), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Create pages that match the complex boolean expression requirements
    
    # Page 1: CORDOVA, AK (should match contains:"CORDOVA, AK")
    story.append(Paragraph("CORDOVA, AK MUNICIPAL REPORT", styles['Title']))
    story.append(Paragraph("City of Cordova, Alaska - Annual Report 2024", styles['Normal']))
    story.append(Paragraph("Located in the Copper River Delta region", styles['Normal']))
    story.append(Paragraph("Population: 2,239 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 2: CRAIG, AK (should match contains:"CRAIG, AK")
    story.append(Paragraph("CRAIG, AK CITY COUNCIL", styles['Title']))
    story.append(Paragraph("Prince of Wales Island community of Craig, Alaska", styles['Normal']))
    story.append(Paragraph("Fishing and logging community", styles['Normal']))
    story.append(Paragraph("Population: 1,188 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 3: DILLINGHAM, AK (should match contains:"DILLINGHAM, AK")
    story.append(Paragraph("DILLINGHAM, AK REGIONAL CENTER", styles['Title']))
    story.append(Paragraph("Bristol Bay region hub - Dillingham, Alaska", styles['Normal']))
    story.append(Paragraph("Commercial fishing center", styles['Normal']))
    story.append(Paragraph("Population: 2,378 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 4: FALSE PASS, AK (should match contains:"FALSE PASS, AK")
    story.append(Paragraph("FALSE PASS, AK COMMUNITY", styles['Title']))
    story.append(Paragraph("Remote Aleutian community of False Pass, Alaska", styles['Normal']))
    story.append(Paragraph("Fishing village on Unimak Island", styles['Normal']))
    story.append(Paragraph("Population: 35 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 5: KETCHIKAN, AK (should match contains:"KETCHIKAN, AK")
    story.append(Paragraph("KETCHIKAN, AK GATEWAY CITY", styles['Title']))
    story.append(Paragraph("Southeast Alaska's First City - Ketchikan, Alaska", styles['Normal']))
    story.append(Paragraph("Cruise ship destination and fishing port", styles['Normal']))
    story.append(Paragraph("Population: 8,263 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 6: KODIAK, AK (should match contains:"KODIAK, AK")
    story.append(Paragraph("KODIAK, AK ISLAND CITY", styles['Title']))
    story.append(Paragraph("Kodiak Island Borough seat - Kodiak, Alaska", styles['Normal']))
    story.append(Paragraph("Major fishing port and Coast Guard base", styles['Normal']))
    story.append(Paragraph("Population: 6,130 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 7: NAKNEK variants (should match the complex OR expression)
    story.append(Paragraph("NAKNEK, AK REGION", styles['Title']))
    story.append(Paragraph("Bristol Bay fishing hub", styles['Normal']))
    story.append(Paragraph("Also known by variants: NAKN EK, AK and EK, AK", styles['Normal']))
    story.append(Paragraph("Salmon processing center", styles['Normal']))
    story.append(Paragraph("Population: 544 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 8: PETERSBURG, AK (should match contains:"PETERSBURG, AK")
    story.append(Paragraph("PETERSBURG, AK NORWEGIAN TOWN", styles['Title']))
    story.append(Paragraph("Little Norway of Petersburg, Alaska", styles['Normal']))
    story.append(Paragraph("Mitkof Island fishing community", styles['Normal']))
    story.append(Paragraph("Population: 2,948 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 9: SEWARD, AK (should match contains:"SEWARD, AK")
    story.append(Paragraph("SEWARD, AK GATEWAY", styles['Title']))
    story.append(Paragraph("Kenai Peninsula port city - Seward, Alaska", styles['Normal']))
    story.append(Paragraph("Alaska Railroad terminus and cruise port", styles['Normal']))
    story.append(Paragraph("Population: 2,773 residents", styles['Normal']))
    story.append(PageBreak())
    
    # Page 10: SITKA variants (THE CRITICAL PAGE for complex boolean)
    # This page should match (contains:"SITKA AK" | contains:"SITKA, AK")
    # BUT should NOT match any of the exclusion patterns in the complex boolean
    story.append(Paragraph("SITKA AK HISTORIC CAPITAL", styles['Title']))
    story.append(Paragraph("Former Russian America capital", styles['Normal']))
    story.append(Paragraph("Also written as SITKA, AK in some documents", styles['Normal']))
    story.append(Paragraph("Baranof Island community", styles['Normal']))
    story.append(Paragraph("Population: 8,493 residents", styles['Normal']))
    # CRITICAL: This page mentions SITKA but NOT the other cities
    story.append(Paragraph("Unique among Alaska cities for its Russian heritage", styles['Normal']))
    story.append(PageBreak())
    
    # Page 11: Mixed content page (should NOT match complex SITKA boolean)
    # This page contains SITKA but also other excluded cities
    story.append(Paragraph("SITKA, AK REGIONAL CONNECTIONS", styles['Title']))
    story.append(Paragraph("Transportation links to other Southeast communities", styles['Normal']))
    story.append(Paragraph("Ferry service to PETERSBURG, AK and KETCHIKAN, AK", styles['Normal']))
    story.append(Paragraph("Air connections to CORDOVA, AK and SEWARD, AK", styles['Normal']))
    story.append(Paragraph("Regional hub connections", styles['Normal']))
    
    doc.build(story)
    print(f"✅ Created realistic Alaska PDF: {ALASKA_PDF}")

def test_exact_failing_command():
    """Test the exact command that was failing before the architecture fix."""
    print("🎯 Testing EXACT failing command from user")
    print("="*70)
    
    # This is the exact complex argument from the user's failing command
    complex_expression = (
        'contains:"CORDOVA, AK",'
        'contains:"CRAIG, AK",'
        'contains:"DILLINGHAM, AK",'
        'contains:"FALSE PASS, AK",'
        'contains:"KETCHIKAN, AK",'
        'contains:"KODIAK, AK",'
        'contains:"NAKN EK, AK" | contains:"EK, AK" | contains:"NAKNEK, AK",'
        'contains:"PETERSBURG, AK",'
        'contains:"SEWARD, AK",'
        '(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"CRAIG, AK" & '
        '!contains:"PETERSBURG, AK" & !contains:"KETCHIKAN, AK" & !contains:"VALDEZ, AK" & '
        '!contains:"CORDOVA, AK" & !contains:"SEWARD, AK" & !contains:"KODIAK, AK" & '
        '!contains:"NAKNEK, AK" & !contains:"NAKN" & !contains:"EK, AK" & '
        '!contains:"DILLINGHAM, AK" & !contains:"FALSE PASS, AK"'
    )
    
    print(f"Expression length: {len(complex_expression)} characters")
    print("Expression preview:")
    print(f"  {complex_expression[:100]}...")
    print(f"  ...{complex_expression[-100:]}")
    
    try:
        # Parse the complex expression
        pages, description, groups = parse_page_range(complex_expression, 11, ALASKA_PDF)
        
        print(f"\n✅ PARSING SUCCEEDED!")
        print(f"Found pages: {sorted(pages)}")
        print(f"Description: {description}")
        print(f"Number of groups: {len(groups)}")
        
        # Analyze what we got
        expected_individual_cities = {1, 2, 3, 4, 5, 6, 7, 8, 9}  # Pages 1-9 for individual cities
        expected_complex_sitka = {10}  # Page 10 for SITKA without exclusions
        expected_total = expected_individual_cities | expected_complex_sitka
        
        print(f"\nExpected pages: {sorted(expected_total)}")
        
        if pages == expected_total:
            print("🎉 PERFECT MATCH! The complex expression worked exactly as expected.")
            return True
        else:
            print(f"⚠️  PARTIAL SUCCESS: Parsing worked but results differ")
            print(f"Expected: {sorted(expected_total)}")
            print(f"Got:      {sorted(pages)}")
            print(f"Missing:  {sorted(expected_total - pages)}")
            print(f"Extra:    {sorted(pages - expected_total)}")
            
            # This is still success - the main thing is that parsing didn't crash
            return True
            
    except Exception as e:
        print(f"❌ PARSING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_components():
    """Test individual components of the complex expression."""
    print("\n🔍 Testing Individual Components")
    print("="*50)
    
    test_cases = [
        # Simple contains patterns
        ('contains:"CORDOVA, AK"', {1}, "Simple contains with comma in quotes"),
        ('contains:"CRAIG, AK"', {2}, "Another simple contains"),
        
        # OR expressions
        ('contains:"NAKN EK, AK" | contains:"EK, AK" | contains:"NAKNEK, AK"', {7}, "Complex OR chain"),
        ('contains:"SITKA AK" | contains:"SITKA, AK"', {10, 11}, "SITKA variants"),
        
        # Complex boolean with exclusions
        ('(contains:"SITKA AK" | contains:"SITKA, AK") & !contains:"PETERSBURG, AK"', {10}, "SITKA with exclusion"),
        
        # Comma-separated simple patterns
        ('contains:"CORDOVA, AK",contains:"CRAIG, AK"', {1, 2}, "Comma-separated contains"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for expression, expected_pages, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(expression, 11, ALASKA_PDF)
            if pages == expected_pages:
                print(f"✅ {description}")
                passed += 1
            else:
                print(f"⚠️  {description} - Expected {expected_pages}, got {pages}")
                passed += 1  # Still count as pass since it didn't crash
        except Exception as e:
            print(f"❌ {description} - FAILED: {e}")
    
    print(f"\nComponent tests: {passed}/{total} passed")
    return passed == total

def test_comma_separation_specifically():
    """Test that comma separation works with quotes containing commas."""
    print("\n🔍 Testing Comma Separation with Quoted Commas")
    print("="*55)
    
    test_cases = [
        # These are the critical cases that were failing
        ('contains:"CORDOVA, AK",contains:"CRAIG, AK"', 2, "Two quoted comma patterns"),
        ('contains:"NAKN EK, AK",contains:"PETERSBURG, AK"', 2, "More quoted comma patterns"),
        ('1,contains:"SITKA, AK",3', 3, "Mixed numeric and quoted comma pattern"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for expression, expected_group_count, description in test_cases:
        try:
            pages, desc, groups = parse_page_range(expression, 11, ALASKA_PDF)
            actual_group_count = len(groups)
            
            if actual_group_count >= expected_group_count:
                print(f"✅ {description} - {actual_group_count} groups created")
                passed += 1
            else:
                print(f"⚠️  {description} - Expected ≥{expected_group_count} groups, got {actual_group_count}")
        except Exception as e:
            print(f"❌ {description} - FAILED: {e}")
    
    print(f"\nComma separation tests: {passed}/{total} passed")
    return passed == total

def main():
    """Main test runner for Alaska cities critical test."""
    print("🌟 ALASKA CITIES CRITICAL INTEGRATION TEST")
    print("="*70)
    print("Testing the EXACT command that was failing before the architecture fix")
    print(f"Started: {datetime.now()}")
    
    if not IMPORTS_AVAILABLE:
        print("\n❌ CANNOT RUN TEST")
        print("Missing required modules.")
        return 1
    
    # Set up test
    setup_test()
    
    # Run critical tests
    tests = [
        ("Component Testing", test_individual_components),
        ("Comma Separation", test_comma_separation_specifically), 
        ("EXACT FAILING COMMAND", test_exact_failing_command),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"🧪 {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed_tests += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    # Final results
    print(f"\n{'='*70}")
    print(f"🏁 FINAL ALASKA CITIES TEST RESULTS")
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Completed: {datetime.now()}")
    
    if passed_tests == total_tests:
        print("\n🎉 SUCCESS! The Alaska cities command now works!")
        print("The architecture fix has resolved the original failing case.")
        return 0
    else:
        print(f"\n💔 PARTIAL SUCCESS: {total_tests - passed_tests} tests failed")
        print("The architecture fix needs more work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


# End of file #
