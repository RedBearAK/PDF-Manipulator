"""Avoiding circular imports for page range parser and patterns modules"""

from dataclasses import dataclass


@dataclass
class PageGroup:
    pages: list[int]
    is_range: bool
    original_spec: str
