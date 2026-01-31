"""
Safe file modification utility for Crow.
Implements safeguards to prevent self-destruction during self-modification.
"""

import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


def create_backup(file_path: Path) -> Path:
    """Create a timestamped backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / "backup" / f"{file_path.name}.{timestamp}.bak"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return backup_path


def validate_python_syntax(file_path: Path) -> Tuple[bool, str]:
    """Validate Python syntax using py_compile."""
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "Syntax valid"
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def find_line_containing(lines: list, target: str) -> int:
    """Find the index of the first line containing target string. Returns -1 if not found."""
    for i, line in enumerate(lines):
        if target in line:
            return i
    return -1


def safe_insert_after_line(
    file_path: Path,
    target_line_content: str,
    new_content: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Safely insert content after a line containing target_line_content.
    
    Args:
        file_path: Path to the file to modify
        target_line_content: String to search for in the file
        new_content: Content to insert after the found line
        dry_run: If True, don't actually write, just validate
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Read original content
    try:
        original_content = file_path.read_text()
        lines = original_content.splitlines(keepends=True)
    except Exception as e:
        return False, f"Failed to read file: {e}"
    
    # Find target line
    target_index = find_line_containing(lines, target_line_content)
    if target_index == -1:
        return False, f"Target line not found: '{target_line_content}'"
    
    # Check if content already exists (prevent duplicates)
    first_new_line = new_content.strip().split('\n')[0]
    if find_line_containing(lines, first_new_line) != -1:
        return False, f"Content appears to already exist (found: '{first_new_line}')"
    
    # Insert new content
    new_lines = new_content.splitlines(keepends=True)
    if not new_content.endswith('\n'):
        new_lines[-1] += '\n'
    
    modified_lines = lines[:target_index + 1] + new_lines + lines[target_index + 1:]
    modified_content = ''.join(modified_lines)
    
    if dry_run:
        return True, f"Dry run: Would insert {len(new_lines)} lines after line {target_index}"
    
    # Create backup
    backup_path = create_backup(file_path)
    
    # Write to temporary file first
    temp_path = file_path.with_suffix('.tmp')
    try:
        temp_path.write_text(modified_content)
    except Exception as e:
        return False, f"Failed to write temp file: {e}"
    
    # Validate syntax (for Python files)
    if file_path.suffix == '.py':
        valid, msg = validate_python_syntax(temp_path)
        if not valid:
            temp_path.unlink()  # Clean up temp file
            return False, f"Syntax validation failed: {msg}"
    
    # Move temp to real file
    try:
        shutil.move(temp_path, file_path)
    except Exception as e:
        temp_path.unlink()
        return False, f"Failed to replace file: {e}"
    
    return True, f"Successfully inserted after line {target_index}. Backup at: {backup_path}"


def safe_replace_line(
    file_path: Path,
    target_line_content: str,
    new_line: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Safely replace a line containing target_line_content.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Read original content
    try:
        original_content = file_path.read_text()
        lines = original_content.splitlines(keepends=True)
    except Exception as e:
        return False, f"Failed to read file: {e}"
    
    # Find target line
    target_index = find_line_containing(lines, target_line_content)
    if target_index == -1:
        return False, f"Target line not found: '{target_line_content}'"
    
    if dry_run:
        return True, f"Dry run: Would replace line {target_index}"
    
    # Create backup
    backup_path = create_backup(file_path)
    
    # Replace line
    if not new_line.endswith('\n'):
        new_line += '\n'
    lines[target_index] = new_line
    modified_content = ''.join(lines)
    
    # Write to temporary file first
    temp_path = file_path.with_suffix('.tmp')
    try:
        temp_path.write_text(modified_content)
    except Exception as e:
        return False, f"Failed to write temp file: {e}"
    
    # Validate syntax (for Python files)
    if file_path.suffix == '.py':
        valid, msg = validate_python_syntax(temp_path)
        if not valid:
            temp_path.unlink()
            return False, f"Syntax validation failed: {msg}"
    
    # Move temp to real file
    try:
        shutil.move(temp_path, file_path)
    except Exception as e:
        temp_path.unlink()
        return False, f"Failed to replace file: {e}"
    
    return True, f"Successfully replaced line {target_index}. Backup at: {backup_path}"


if __name__ == "__main__":
    # Test the module
    print("Safe modification utility loaded successfully.")
    print("Functions available: create_backup, validate_python_syntax, safe_insert_after_line, safe_replace_line")
