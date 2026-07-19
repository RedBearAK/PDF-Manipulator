"""
Redirect stub for the retired standalone scraper CLI.
File: pdf_manipulator/scraper/__main__.py

The standalone scraper CLI (with the old colon-based pattern syntax) was
fully merged into the main pdf-manipulator CLI. This stub points anyone
running the old entry point at the merged modes instead of crashing.
"""

import sys


def main():
    """Print redirect guidance and exit with an error code."""
    print("The standalone scraper CLI has been merged into pdf-manipulator.")
    print()
    print("Use the main CLI with Phase 4 compact pattern syntax instead:")
    print('  pdf-manipulator file.pdf --dump-text [--output raw.txt]')
    print('  pdf-manipulator file.pdf --scrape-text \\')
    print('      --scrape-pattern="invoice=Invoice Number:wd1" \\')
    print('      --output data.tsv')
    print()
    print("Pattern syntax reference: pdf-manipulator --help")
    return 1


if __name__ == '__main__':
    sys.exit(main())


# End of file #
