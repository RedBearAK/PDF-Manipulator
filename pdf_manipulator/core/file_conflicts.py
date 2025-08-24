"""
File conflict resolution system for PDF extraction operations.
File: pdf_manipulator/core/file_conflicts.py
"""

import re
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


class ConflictResolutionStrategy:
    """Enumeration of conflict resolution strategies."""
    ASK         = "ask"         # Ask user for each conflict
    OVERWRITE   = "overwrite"   # Overwrite existing files
    SKIP        = "skip"        # Skip conflicting files
    RENAME      = "rename"      # Auto-rename with suffix
    FAIL        = "fail"        # Stop on first conflict


def check_file_conflicts(output_paths: list[Path]) -> list[Path]:
    """
    Check which output paths already exist.
    
    Args:
        output_paths: List of planned output file paths
        
    Returns:
        List of paths that already exist (conflicts)
    """
    conflicts = []
    for path in output_paths:
        if path.exists():
            conflicts.append(path)
    return conflicts


def resolve_file_conflicts(output_paths: list[Path], 
                            strategy: str = ConflictResolutionStrategy.ASK,
                            interactive: bool = True) -> tuple[list[Path], list[Path]]:
    """
    Resolve file conflicts according to specified strategy.
    
    Args:
        output_paths: List of planned output file paths
        strategy: Conflict resolution strategy
        interactive: Whether to allow interactive prompts
        
    Returns:
        Tuple of (resolved_paths, skipped_paths)
        
    Raises:
        ValueError: If strategy is 'fail' and conflicts exist
    """
    conflicts = check_file_conflicts(output_paths)
    
    if not conflicts:
        return output_paths, []
    
    if strategy == ConflictResolutionStrategy.FAIL:
        conflict_names = [p.name for p in conflicts]
        raise ValueError(f"File conflicts detected: {', '.join(conflict_names)}. "
                        "Use conflict resolution options to handle existing files.")
    
    resolved_paths = []
    skipped_paths = []
    
    for path in output_paths:
        if path not in conflicts:
            # No conflict - keep as is
            resolved_paths.append(path)
            continue
        
        # Handle conflict based on strategy
        if strategy == ConflictResolutionStrategy.OVERWRITE:
            console.print(f"[yellow]Overwriting existing file: {path.name}[/yellow]")
            resolved_paths.append(path)
            
        elif strategy == ConflictResolutionStrategy.SKIP:
            console.print(f"[dim]Skipping existing file: {path.name}[/dim]")
            skipped_paths.append(path)
            
        elif strategy == ConflictResolutionStrategy.RENAME:
            new_path = generate_unique_filename(path)
            console.print(f"[cyan]Renaming to avoid conflict: {path.name} → {new_path.name}[/cyan]")
            resolved_paths.append(new_path)
            
        elif strategy == ConflictResolutionStrategy.ASK and interactive:
            new_path = ask_user_conflict_resolution(path)
            if new_path:
                resolved_paths.append(new_path)
            else:
                skipped_paths.append(path)
        else:
            # Default fallback (non-interactive ASK becomes RENAME)
            new_path = generate_unique_filename(path)
            console.print(f"[cyan]Auto-renaming conflicting file: {path.name} → {new_path.name}[/cyan]")
            resolved_paths.append(new_path)
    
    return resolved_paths, skipped_paths


def ask_user_conflict_resolution(path: Path) -> Optional[Path]:
    """
    Ask user how to resolve a specific file conflict.
    
    Args:
        path: Conflicting file path
        
    Returns:
        Resolved path or None if user chooses to skip
    """
    console.print(f"\n[yellow]File already exists: {path.name}[/yellow]")
    
    choices = {
        "o": "Overwrite existing file",
        "r": "Rename (add suffix)",
        "c": "Choose new name",
        "s": "Skip this file"
    }
    
    for key, description in choices.items():
        console.print(f"  {key}: {description}")
    
    while True:
        choice = Prompt.ask("Choose action", choices=list(choices.keys()), default="r")
        
        if choice == "o":
            return path
        elif choice == "r":
            return generate_unique_filename(path)
        elif choice == "c":
            return ask_custom_filename(path)
        elif choice == "s":
            return None


def ask_custom_filename(original_path: Path) -> Optional[Path]:
    """
    Ask user for a custom filename.
    
    Args:
        original_path: Original file path
        
    Returns:
        New path with custom name or None if cancelled
    """
    default_name = original_path.stem
    
    while True:
        new_name = Prompt.ask(
            f"Enter new filename (without .pdf)", 
            default=default_name
        )
        
        if not new_name:
            return None
            
        new_path = original_path.parent / f"{new_name}.pdf"
        
        if new_path.exists():
            console.print(f"[yellow]File {new_path.name} also exists![/yellow]")
            if not Confirm.ask("Try again?", default=True):
                return generate_unique_filename(new_path)
        else:
            return new_path


def generate_unique_filename(path: Path, max_attempts: int = 100) -> Path:
    """
    Generate a unique filename by adding a numeric suffix.
    
    Args:
        path: Original file path
        max_attempts: Maximum number of suffix attempts
        
    Returns:
        Unique file path
        
    Raises:
        ValueError: If unable to generate unique name within max_attempts
    """
    if not path.exists():
        return path
    
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    
    # Check if filename already has a numeric suffix
    match = re.search(r'_(\d+)$', stem)
    if match:
        base_stem = stem[:match.start()]
        start_num = int(match.group(1)) + 1
    else:
        base_stem = stem
        start_num = 1
    
    for i in range(start_num, start_num + max_attempts):
        candidate = parent / f"{base_stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    
    raise ValueError(f"Unable to generate unique filename for {path.name} after {max_attempts} attempts")


def preview_file_operations(original_paths: list[Path], 
                            resolved_paths: list[Path], 
                            skipped_paths: list[Path]) -> None:
    """
    Show a preview of planned file operations.
    
    Args:
        original_paths: Original planned paths
        resolved_paths: Resolved paths after conflict resolution
        skipped_paths: Paths that will be skipped
    """
    console.print("\n[cyan]File Operation Preview:[/cyan]")
    
    # Show files that will be created
    if resolved_paths:
        console.print(f"[green]Will create {len(resolved_paths)} files:[/green]")
        for path in resolved_paths:
            console.print(f"  + {path.name}")
    
    # Show files that will be skipped
    if skipped_paths:
        console.print(f"[yellow]Will skip {len(skipped_paths)} existing files:[/yellow]")
        for path in skipped_paths:
            console.print(f"  - {path.name}")
    
    # Show renamed files
    renamed_count = 0
    for orig, resolved in zip(original_paths, resolved_paths):
        if orig.name != resolved.name:
            renamed_count += 1
    
    if renamed_count > 0:
        console.print(f"[cyan]{renamed_count} files will be renamed to avoid conflicts[/cyan]")


def suggest_conflict_free_basename(base_path: Path, desired_pattern: str) -> str:
    """
    Suggest a conflict-free base name for batch operations.
    
    Args:
        base_path: Directory where files will be created
        desired_pattern: Desired filename pattern (e.g., "alaska_cities")
        
    Returns:
        Conflict-free base pattern
    """
    # Check if any files matching the pattern exist
    pattern_files = list(base_path.glob(f"{desired_pattern}*.pdf"))
    
    if not pattern_files:
        return desired_pattern
    
    # Suggest alternatives
    alternatives = [
        f"{desired_pattern}_new",
        f"{desired_pattern}_extracted", 
        f"{desired_pattern}_v2",
        f"{desired_pattern}_updated"
    ]
    
    for alt in alternatives:
        alt_files = list(base_path.glob(f"{alt}*.pdf"))
        if not alt_files:
            return alt
    
    # Fall back to timestamp
    import time
    timestamp = int(time.time())
    return f"{desired_pattern}_{timestamp}"


# End of file #
