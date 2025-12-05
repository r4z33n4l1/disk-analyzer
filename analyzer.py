#!/usr/bin/env python3
"""
Disk Analyzer - Scans directories and outputs size information as JSON.

JSON Schema:
{
    "path": "/absolute/path/to/root",
    "name": "root_folder_name",
    "size": 123456789,           # size in bytes
    "type": "dir",               # "dir" or "file"
    "children": [                # only for directories
        {
            "name": "child_name",
            "path": "/absolute/path/to/child",
            "size": 12345678,
            "type": "dir" | "file",
            "children": [...]    # recursive for dirs
        }
    ]
}

Usage:
    python analyzer.py [OPTIONS]

Options:
    --path PATH         Directory to scan (default: user home directory)
    --depth N           Max depth to scan (default: 3)
    --output FILE       Output JSON file (default: disk-report.json)
    --shortcuts N       Generate shortcuts for top N largest items (default: 0, disabled)
    --shortcuts-dir DIR Directory to store shortcuts (default: ./shortcuts)
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Optional
import plistlib


def get_size_with_du(path: str) -> int:
    """Get directory size using du command (fast)."""
    try:
        result = subprocess.run(
            ["du", "-sk", path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            size_kb = int(result.stdout.split()[0])
            return size_kb * 1024
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return 0


def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def get_folder_size_walk(path: str) -> int:
    """Get folder size using os.walk (fallback, slower)."""
    total = 0
    try:
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def scan_directory(path: str, max_depth: int, current_depth: int = 0) -> dict:
    """
    Recursively scan a directory and build a tree structure with sizes.
    
    Returns a dict with name, path, size, type, and children (for directories).
    """
    path = os.path.abspath(path)
    name = os.path.basename(path) or path
    indent = "  " * current_depth
    
    # Log current directory being scanned
    print(f"{indent}📂 {name}/", flush=True)
    
    if os.path.isfile(path):
        return {
            "name": name,
            "path": path,
            "size": get_file_size(path),
            "type": "file"
        }
    
    # It's a directory
    result = {
        "name": name,
        "path": path,
        "size": 0,
        "type": "dir",
        "children": []
    }
    
    # If we've reached max depth, just compute the size without children
    if current_depth >= max_depth:
        size = get_size_with_du(path)
        result["size"] = size
        print(f"{indent}   └─ ⏹ (max depth) {format_size(size)}", flush=True)
        return result
    
    # Scan children
    try:
        entries = os.listdir(path)
    except PermissionError:
        size = get_size_with_du(path)
        result["size"] = size
        print(f"{indent}   └─ 🔒 (permission denied) {format_size(size)}", flush=True)
        return result
    except OSError:
        print(f"{indent}   └─ ❌ (error reading)", flush=True)
        return result
    
    # Filter entries (skip hidden)
    valid_entries = [e for e in entries if not e.startswith('.')]
    total_entries = len(valid_entries)
    
    total_size = 0
    children = []
    dirs_count = 0
    files_count = 0
    
    for idx, entry in enumerate(valid_entries, 1):
        full_path = os.path.join(path, entry)
        
        try:
            if os.path.islink(full_path):
                # Skip symlinks to avoid infinite loops
                continue
            elif os.path.isdir(full_path):
                dirs_count += 1
                child = scan_directory(full_path, max_depth, current_depth + 1)
            else:
                files_count += 1
                child = {
                    "name": entry,
                    "path": full_path,
                    "size": get_file_size(full_path),
                    "type": "file"
                }
            
            children.append(child)
            total_size += child["size"]
        except OSError:
            continue
    
    # Sort children by size descending
    children.sort(key=lambda x: x["size"], reverse=True)
    
    result["children"] = children
    result["size"] = total_size
    
    # Print completion summary for this folder
    print(f"{indent}   └─ ✅ Done: {dirs_count} folders, {files_count} files = {format_size(total_size)}", flush=True)
    
    return result


def flatten_tree(node: dict, items: list = None) -> list:
    """Flatten the tree into a list of all items with their sizes."""
    if items is None:
        items = []
    
    items.append({
        "name": node["name"],
        "path": node["path"],
        "size": node["size"],
        "type": node["type"]
    })
    
    if "children" in node:
        for child in node["children"]:
            flatten_tree(child, items)
    
    return items


def create_webloc_file(target_path: str, shortcut_path: str):
    """Create a .webloc file that opens in Finder when double-clicked."""
    # Use file:// URL for local paths
    file_url = "file://" + target_path.replace(" ", "%20")
    
    plist_data = {
        "URL": file_url
    }
    
    with open(shortcut_path, "wb") as f:
        plistlib.dump(plist_data, f)


def create_alias(target_path: str, alias_path: str):
    """Create a macOS alias using osascript."""
    # Escape paths for AppleScript: escape backslashes then double quotes
    def escape_applescript_string(s):
        return s.replace('\\', '\\\\').replace('"', '\\"')

    target_escaped = escape_applescript_string(target_path)
    alias_dir = os.path.dirname(alias_path)
    alias_name = os.path.basename(alias_path)
    alias_dir_escaped = escape_applescript_string(alias_dir)
    alias_name_escaped = escape_applescript_string(alias_name)
    
    script = f'''
    tell application "Finder"
        set targetPath to POSIX file "{target_escaped}"
        set aliasDir to POSIX file "{alias_dir_escaped}"
        make new alias file at aliasDir to targetPath
        set name of result to "{alias_name_escaped}"
    end tell
    '''
    
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=10
        )
        return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def generate_shortcuts(tree: dict, shortcuts_dir: str, top_n: int = 50):
    """Generate shortcut files for the top N largest items."""
    # Flatten the tree and get all items
    all_items = flatten_tree(tree)
    
    # Sort by size and take top N
    all_items.sort(key=lambda x: x["size"], reverse=True)
    top_items = all_items[:top_n]
    
    # Create shortcuts directory
    shortcuts_path = Path(shortcuts_dir)
    if shortcuts_path.exists():
        shutil.rmtree(shortcuts_path)
    shortcuts_path.mkdir(parents=True, exist_ok=True)
    
    # Create a subdirectory for each type
    (shortcuts_path / "folders").mkdir(exist_ok=True)
    (shortcuts_path / "files").mkdir(exist_ok=True)
    
    created = 0
    for i, item in enumerate(top_items):
        # Create a safe filename
        safe_name = item["name"].replace("/", "_").replace(":", "_")
        size_mb = item["size"] / (1024 * 1024)
        
        # Prefix with rank and size for easy sorting
        prefix = f"{i+1:03d}_{size_mb:.0f}MB_"
        
        subdir = "folders" if item["type"] == "dir" else "files"
        shortcut_name = f"{prefix}{safe_name}.webloc"
        shortcut_full_path = shortcuts_path / subdir / shortcut_name
        
        try:
            create_webloc_file(item["path"], str(shortcut_full_path))
            created += 1
        except Exception as e:
            print(f"Warning: Could not create shortcut for {item['path']}: {e}", file=sys.stderr)
    
    print(f"Created {created} shortcuts in {shortcuts_dir}/")
    return created


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def main():
    parser = argparse.ArgumentParser(
        description="Disk Analyzer - Scan directories and output size information as JSON"
    )
    parser.add_argument(
        "--path",
        default=os.path.expanduser("~"),
        help="Directory to scan (default: user home directory)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum depth to scan (default: 3)"
    )
    parser.add_argument(
        "--output",
        default="disk-report.json",
        help="Output JSON file (default: disk-report.json)"
    )
    parser.add_argument(
        "--shortcuts",
        type=int,
        default=0,
        help="Generate shortcuts for top N largest items (default: 0, disabled)"
    )
    parser.add_argument(
        "--shortcuts-dir",
        default="./shortcuts",
        help="Directory to store shortcuts (default: ./shortcuts)"
    )
    
    args = parser.parse_args()
    
    target_path = os.path.abspath(os.path.expanduser(args.path))
    
    if not os.path.exists(target_path):
        print(f"Error: Path does not exist: {target_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Scanning: {target_path}")
    print(f"Max depth: {args.depth}")
    print()
    
    # Scan the directory
    tree = scan_directory(target_path, args.depth)
    
    # Write JSON output
    output_path = args.output
    with open(output_path, "w") as f:
        json.dump(tree, f, indent=2)
    
    print(f"Total size: {format_size(tree['size'])}")
    print(f"Report written to: {output_path}")
    
    # Generate shortcuts if requested
    if args.shortcuts > 0:
        print()
        generate_shortcuts(tree, args.shortcuts_dir, args.shortcuts)
    
    print("\nDone!")


if __name__ == "__main__":
    main()

