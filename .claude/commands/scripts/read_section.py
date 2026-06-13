#!/usr/bin/env python3
"""
Read a specific section from a markdown file by GitHub-style anchor.

Usage:
    python3 scripts/read_section.py ARCHITECTURE.md#graph-architecture--gnn-first
    python3 scripts/read_section.py ARCHITECTURE.md#list   ← list all anchors in file
"""

import re
import sys


def to_anchor(heading_line: str) -> str:
    """Convert a markdown heading line to its GitHub anchor slug."""
    text = re.sub(r"^#+\s*", "", heading_line).strip()
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)   # strip non-word except space/hyphen
    text = text.strip()
    text = re.sub(r"\s", "-", text)         # each space → hyphen (matches GitHub: no collapse)
    return text


def list_sections(file_path: str) -> None:
    with open(file_path) as f:
        for line in f:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                anchor = to_anchor(line)
                heading = line.lstrip("#").strip()
                print(f"{'  ' * (level - 1)}#{anchor}  —  {heading}")


def read_section(file_path: str, anchor: str) -> str:
    with open(file_path) as f:
        lines = f.readlines()

    start = -1
    start_level = 0

    for i, line in enumerate(lines):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if to_anchor(line) == anchor:
                start = i
                start_level = level
                break

    if start == -1:
        print(f"Error: anchor '#{anchor}' not found in {file_path}", file=sys.stderr)
        print(f"\nAvailable sections (run with #list to see all):", file=sys.stderr)
        list_sections(file_path)
        sys.exit(1)

    # Collect lines until next heading at same or higher level
    end = len(lines)
    for i in range(start + 1, len(lines)):  # start is always >= 0 here
        if lines[i].startswith("#"):
            level = len(lines[i]) - len(lines[i].lstrip("#"))
            if level <= start_level:
                end = i
                break

    return "".join(lines[start:end])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: read_section.py <file>#<anchor>", file=sys.stderr)
        print("       read_section.py <file>#list", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    if "#" not in arg:
        print("Error: argument must be <file>#<anchor>", file=sys.stderr)
        sys.exit(1)

    file_path, anchor = arg.split("#", 1)

    if anchor == "list":
        list_sections(file_path)
    else:
        print(read_section(file_path, anchor), end="")
