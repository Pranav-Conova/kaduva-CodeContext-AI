"""Patch generation using difflib."""

import difflib


def generate_patch(old_code: str, new_code: str, filename: str = "file") -> str:
    """
    Generate a unified diff patch between old and new code.

    Args:
        old_code: The original file content.
        new_code: The modified file content.
        filename: The filename to show in the diff header.

    Returns:
        A unified diff string, or empty string if no changes detected.
    """
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )

    return "\n".join(diff)


def apply_patch_to_content(old_code: str, new_code: str) -> str:
    """
    For MVP, we simply return the new code as the 'applied' result.
    The actual patching logic is handled by applying the full new file.
    """
    return new_code
