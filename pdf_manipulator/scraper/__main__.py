"""
Entry point for running Simple PDF Scraper as a module.
"""

import sys

from pdf_manipulator.scraper.cli import main


if __name__ == "__main__":
    sys.exit(main())

