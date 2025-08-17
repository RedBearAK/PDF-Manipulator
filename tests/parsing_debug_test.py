"""
Debug script to test the full parsing pipeline.
"""

from pdf_manipulator.renamer.pattern_processor import PatternProcessor, CompactPatternError

def debug_pattern_parsing():
    processor = PatternProcessor()
    
    failing_patterns = [
        "Invoice:r1wd1pg3-",
        "Invoice:r1wd1mt2-", 
        "Summary:d1wd5pg3-"
    ]
    
    for pattern in failing_patterns:
        print(f"\n=== Debugging pattern: '{pattern}' ===")
        
        try:
            # Extract just the compact spec part
            if ':' in pattern:
                keyword, compact_spec = pattern.rsplit(':', 1)
                print(f"Keyword: '{keyword}'")
                print(f"Compact spec: '{compact_spec}'")
                
                # Test the regex match directly
                match = processor.COMPACT_PATTERN.match(compact_spec)
                if match:
                    print(f"Regex groups: {match.groups()}")
                    
                    # Test the _parse_extraction_spec method
                    try:
                        result = processor._parse_extraction_spec(compact_spec)
                        print(f"Parsing result: {result}")
                        
                        # Test the full pattern parsing
                        var_name, keyword_parsed, extraction_spec = processor.parse_pattern_string(pattern)
                        print(f"✓ Full parsing successful:")
                        print(f"  Variable: {var_name}")
                        print(f"  Keyword: {keyword_parsed}")
                        print(f"  Spec: {extraction_spec}")
                        
                    except Exception as e:
                        print(f"✗ _parse_extraction_spec failed: {e}")
                        
                        # Let's debug the range parsing specifically
                        if match.group(6):  # pg specification
                            pg_spec = match.group(6)[2:]  # Remove 'pg' prefix
                            print(f"Testing pg spec: '{pg_spec}'")
                            try:
                                pg_result = processor._parse_range_spec(pg_spec, 'page')
                                print(f"PG parsing result: {pg_result}")
                            except Exception as pg_e:
                                print(f"PG parsing failed: {pg_e}")
                                
                        if match.group(7):  # mt specification
                            mt_spec = match.group(7)[2:]  # Remove 'mt' prefix
                            print(f"Testing mt spec: '{mt_spec}'")
                            try:
                                mt_result = processor._parse_range_spec(mt_spec, 'match')
                                print(f"MT parsing result: {mt_result}")
                            except Exception as mt_e:
                                print(f"MT parsing failed: {mt_e}")
                else:
                    print(f"✗ Regex did not match compact spec: '{compact_spec}'")
                    
        except Exception as e:
            print(f"✗ Full pattern parsing failed: {e}")
            print(f"Exception type: {type(e)}")
            
            # Let's see if it's a validation error
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_pattern_parsing()
