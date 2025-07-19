"""Page range parsing functionality."""

import re
from dataclasses import dataclass


@dataclass
class PageGroup:
    pages: list[int]
    is_range: bool
    original_spec: str


def parse_page_range(range_str: str, total_pages: int) -> tuple[set[int], str, list[PageGroup]]:
    """
    Parse page range string and return set of page numbers (1-indexed), description, and groupings.

    Supports:
    - Single page: "5"
    - Range: "3-7" or "3:7" or "3..7"
    - Open-ended: "3-" (page 3 to end) or "-7" (start to page 7)
    - First N: "first 3" or "first-3"
    - Last N: "last 2" or "last-2"
    - Multiple: "1-3,7,9-11"
    - Slicing: "::2" (odd pages), "2::2" (even pages), "5:10:2" (every 2nd from 5 to 10)

    Returns: (set of page numbers, description for filename, list of page groups)
    """
    pages = set()
    descriptions = []
    groups = []  # Track the original groupings

    # Remove quotes and extra spaces
    range_str = range_str.strip().strip('"\'')

    # Handle comma-separated ranges
    parts = [p.strip() for p in range_str.split(',')]

    for part in parts:
        try:
            group_pages = []  # Pages in this specific group
            
            # Check for slicing syntax (contains :: or single : with 3 parts)
            if '::' in part or (part.count(':') == 2):
                # Parse slicing: start:stop:step
                slice_parts = part.split(':')
                start = int(slice_parts[0]) if slice_parts[0] else 1
                stop = int(slice_parts[1]) if slice_parts[1] else total_pages
                step = int(slice_parts[2]) if len(slice_parts) > 2 and slice_parts[2] else 1

                # Make stop inclusive for user-friendliness
                for p in range(start, stop + 1, step):
                    if 1 <= p <= total_pages:
                        pages.add(p)
                        group_pages.append(p)

                groups.append(PageGroup(group_pages, True, part))  # Step syntax is treated as range

                if not slice_parts[0] and not slice_parts[1]:
                    if step == 2:
                        descriptions.append("odd" if start == 1 else "even")
                    else:
                        descriptions.append(f"every-{step}")
                else:
                    descriptions.append(f"{start}-{stop}-step{step}")

            # Check for "first N" syntax
            elif part.lower().startswith('first'):
                match = re.match(r'first[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(1, min(n + 1, total_pages + 1)):
                        pages.add(p)
                        group_pages.append(p)
                    groups.append(PageGroup(group_pages, True, part))  # "first N" is treated as range
                    descriptions.append(f"first{n}")

            # Check for "last N" syntax
            elif part.lower().startswith('last'):
                match = re.match(r'last[\s-]?(\d+)', part, re.IGNORECASE)
                if match:
                    n = int(match.group(1))
                    for p in range(max(1, total_pages - n + 1), total_pages + 1):
                        pages.add(p)
                        group_pages.append(p)
                    groups.append(PageGroup(group_pages, True, part))  # "last N" is treated as range
                    descriptions.append(f"last{n}")

            # Check for range syntax
            elif any(sep in part for sep in ['-', ':', '..']):
                # Find the separator
                sep = next(s for s in ['-', ':', '..'] if s in part)
                if sep == '..':
                    start_str, end_str = part.split('..')
                else:
                    # Be careful with negative numbers
                    parts_split = part.split(sep, 1)
                    start_str = parts_split[0]
                    end_str = parts_split[1] if len(parts_split) > 1 else ''

                # Parse start and end
                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else total_pages

                if start > end:
                    raise ValueError(f"Invalid range: {start} > {end}")

                for p in range(start, end + 1):
                    if 1 <= p <= total_pages:
                        pages.add(p)
                        group_pages.append(p)

                groups.append(PageGroup(group_pages, True, part))  # Range syntax is treated as range
                descriptions.append(f"{start}-{end}")

            # Single page number
            else:
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    pages.add(page_num)
                    group_pages.append(page_num)
                    groups.append(PageGroup(group_pages, False, part))  # Single page
                    descriptions.append(str(page_num))
                else:
                    raise ValueError(f"Page {page_num} out of range (1-{total_pages})")

        except ValueError as e:
            raise ValueError(f"Invalid page range '{part}': {str(e)}")

    if not pages:
        raise ValueError("No valid pages in range")

    # Create description for filename
    if len(descriptions) == 1:
        desc = descriptions[0]
    else:
        # Simplify if multiple parts
        desc = ",".join(descriptions)
        if len(desc) > 20:  # Keep filename reasonable
            desc = f"{min(pages)}-{max(pages)}-selected"

    # Format description
    if ',' in desc:
        desc = f"pages{desc}"
    elif any(d in desc for d in ['odd', 'even', 'every', 'first', 'last']):
        desc = desc  # Keep as is
    elif '-' in desc and not desc.startswith('pages'):
        desc = f"pages{desc}"
    else:
        desc = f"page{desc}"

    return pages, desc, groups
