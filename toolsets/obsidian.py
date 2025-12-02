"""
Obsidian Vault Navigation Toolset

Designed for efficient navigation of large vaults:
- Preview note structure before reading (outline, size, links)
- Read specific sections or line ranges
- Search across the vault
- Follow wikilinks systematically
"""

from ai_core.tools import tool
from pathlib import Path
from config.paths import PATHS
from .file_utils import validate_filepath, ensure_md_extension, should_exclude
import os
import re
from typing import Optional

# Directories to exclude from AI access
VAULT_EXCLUDE = [
    "AI Chats",           # AI conversation logs
    "AI Memory",          # AI memory system
    ".obsidian",          # Obsidian config
    ".smart-connections", # Plugin data
    ".trash",             # Deleted files
    ".git",               # Git data if vault is versioned
]

def _resolve_vault_path(filepath: str, is_dir: bool = False) -> Path:
    """Resolve and validate a path within the vault."""
    if filepath and not is_dir:
        validate_filepath(filepath)
        filepath = ensure_md_extension(filepath)
    elif filepath:
        validate_filepath(filepath)
    
    if filepath and should_exclude(filepath, VAULT_EXCLUDE):
        raise ValueError(f"Access to {filepath} is not allowed")
    
    full_path = (PATHS.vault_path / filepath).resolve() if filepath else PATHS.vault_path.resolve()
    
    try:
        full_path.relative_to(PATHS.vault_path)
    except ValueError:
        raise ValueError("Invalid path: attempted to access outside of vault")
    
    return full_path


def _extract_headings(content: str) -> list:
    """Extract all markdown headings with their line numbers."""
    headings = []
    for i, line in enumerate(content.split('\n'), 1):
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            headings.append({
                'level': len(match.group(1)),
                'text': match.group(2).strip(),
                'line': i
            })
    return headings


def _extract_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter and return (metadata, end_line)."""
    if not content.startswith('---'):
        return {}, 0
    
    lines = content.split('\n')
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break
    
    if end_idx is None:
        return {}, 0
    
    # Parse simple key: value pairs
    metadata = {}
    for line in lines[1:end_idx]:
        if ':' in line:
            key, _, value = line.partition(':')
            metadata[key.strip()] = value.strip()
    
    return metadata, end_idx + 1


def _extract_wikilinks(content: str) -> list:
    """Extract all [[wikilinks]] from content."""
    # Match [[link]] or [[link|alias]]
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    links = re.findall(pattern, content)
    return list(dict.fromkeys(links))  # Remove duplicates, preserve order


def _format_size(size_bytes: int) -> str:
    """Format byte size to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024}KB"
    else:
        return f"{size_bytes // (1024 * 1024)}MB"


@tool(
    description="""List files and directories in the vault. Shows file sizes to help decide what to read.
    Use this to explore the vault structure before diving into specific notes.""",
    directory="Directory path relative to vault root. Empty string = vault root.",
    safe=True
)
def list_vault(directory: str = "") -> str:
    """List contents of a vault directory with sizes."""
    try:
        full_path = _resolve_vault_path(directory, is_dir=True)
    except ValueError as e:
        return f"Error: {e}"
    
    if not full_path.exists():
        return f"Error: Directory '{directory}' does not exist"
    if not full_path.is_dir():
        return f"Error: '{directory}' is not a directory"
    
    dirs = []
    files = []
    
    for item in sorted(full_path.iterdir()):
        if should_exclude(item.name, VAULT_EXCLUDE) or item.name.startswith('.'):
            continue
        
        if item.is_dir():
            # Count items in directory
            try:
                count = sum(1 for _ in item.iterdir() if not _.name.startswith('.'))
                dirs.append(f"📁 {item.name}/ ({count} items)")
            except:
                dirs.append(f"📁 {item.name}/")
        elif item.suffix == '.md':
            size = _format_size(item.stat().st_size)
            files.append(f"📄 {item.name} [{size}]")
    
    result = []
    if directory:
        result.append(f"Contents of: {directory}/")
    else:
        result.append("Contents of vault root:")
    result.append("")
    
    if dirs:
        result.append("Directories:")
        result.extend(f"  {d}" for d in dirs)
        result.append("")
    
    if files:
        result.append("Notes:")
        result.extend(f"  {f}" for f in files)
    
    if not dirs and not files:
        result.append("(empty)")
    
    return '\n'.join(result)


@tool(
    description="""Get the outline/structure of a note without reading its full content.
    Returns: frontmatter metadata, headings with line numbers, wikilinks, and total line count.
    Use this to understand a note's structure before reading specific sections.""",
    filepath="Path to the note relative to vault root (e.g., 'Projects/MyProject.md')",
    safe=True
)
def get_note_outline(filepath: str) -> str:
    """Get note structure: headings, links, metadata, size."""
    try:
        full_path = _resolve_vault_path(filepath)
    except ValueError as e:
        return f"Error: {e}"
    
    if not full_path.exists():
        return f"Error: Note '{filepath}' does not exist"
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    total_lines = len(lines)
    size = _format_size(len(content.encode('utf-8')))
    
    # Extract components
    frontmatter, fm_end = _extract_frontmatter(content)
    headings = _extract_headings(content)
    links = _extract_wikilinks(content)
    
    result = [f"📄 {filepath}", f"Size: {size} | Lines: {total_lines}", ""]
    
    if frontmatter:
        result.append("Frontmatter:")
        for k, v in frontmatter.items():
            result.append(f"  {k}: {v}")
        result.append("")
    
    if headings:
        result.append("Outline:")
        for h in headings:
            indent = "  " * (h['level'] - 1)
            result.append(f"  {indent}{'#' * h['level']} {h['text']} (line {h['line']})")
        result.append("")
    
    if links:
        result.append(f"Links ({len(links)}):")
        # Show first 20 links
        for link in links[:20]:
            result.append(f"  [[{link}]]")
        if len(links) > 20:
            result.append(f"  ... and {len(links) - 20} more")
    
    return '\n'.join(result)


@tool(
    description="""Read a note with line numbers. Supports reading specific line ranges for large notes.
    Lines are numbered starting from 1. Use get_note_outline first to see the structure.""",
    filepath="Path to the note relative to vault root",
    offset="Start reading from this line number (1-based). Default: 1",
    limit="Maximum number of lines to return. Default: 200 (use for large notes)",
    safe=True
)
def read_note(filepath: str, offset: int = 1, limit: int = 200) -> str:
    """Read note content with line numbers and optional range."""
    try:
        full_path = _resolve_vault_path(filepath)
    except ValueError as e:
        return f"Error: {e}"
    
    if not full_path.exists():
        return f"Error: Note '{filepath}' does not exist"
    
    with open(full_path, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    offset = max(1, offset)  # Ensure offset is at least 1
    start_idx = offset - 1   # Convert to 0-based
    end_idx = min(start_idx + limit, total_lines)
    
    result = [f"📄 {filepath} (lines {offset}-{end_idx} of {total_lines})"]
    result.append("-" * 60)
    
    for i in range(start_idx, end_idx):
        line_num = i + 1
        line_content = all_lines[i].rstrip('\n')
        result.append(f"{line_num:6}|{line_content}")
    
    if end_idx < total_lines:
        remaining = total_lines - end_idx
        result.append("-" * 60)
        result.append(f"... {remaining} more lines. Use offset={end_idx + 1} to continue reading.")
    
    return '\n'.join(result)


@tool(
    description="""Read a specific section of a note by heading name.
    The section includes everything from the heading until the next heading of equal or higher level.
    Use get_note_outline first to see available headings.""",
    filepath="Path to the note relative to vault root",
    heading="The exact heading text to find (without the # symbols)",
    safe=True
)
def read_note_section(filepath: str, heading: str) -> str:
    """Read a specific section by heading name."""
    try:
        full_path = _resolve_vault_path(filepath)
    except ValueError as e:
        return f"Error: {e}"
    
    if not full_path.exists():
        return f"Error: Note '{filepath}' does not exist"
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    headings = _extract_headings(content)
    
    # Find the target heading
    target = None
    for h in headings:
        if h['text'].lower() == heading.lower():
            target = h
            break
    
    if not target:
        available = [h['text'] for h in headings]
        return f"Error: Heading '{heading}' not found.\nAvailable headings: {available}"
    
    # Find the end of this section (next heading of same or higher level)
    start_line = target['line']
    end_line = len(lines)
    
    for h in headings:
        if h['line'] > target['line'] and h['level'] <= target['level']:
            end_line = h['line'] - 1
            break
    
    # Extract section
    section_lines = lines[start_line - 1:end_line]
    
    result = [f"📄 {filepath} > {heading} (lines {start_line}-{end_line})"]
    result.append("-" * 60)
    
    for i, line in enumerate(section_lines, start_line):
        result.append(f"{i:6}|{line}")
    
    return '\n'.join(result)


@tool(
    description="""Search for text across notes in the vault. Returns matching notes with context.
    Searches file names and content. Use to find relevant notes before reading them.""",
    query="Text to search for (case-insensitive)",
    directory="Limit search to this directory. Empty = search entire vault.",
    max_results="Maximum number of matching notes to return. Default: 10",
    safe=True
)
def search_vault(query: str, directory: str = "", max_results: int = 10) -> str:
    """Search for text across vault notes."""
    try:
        search_path = _resolve_vault_path(directory, is_dir=True) if directory else PATHS.vault_path
    except ValueError as e:
        return f"Error: {e}"
    
    if not search_path.exists():
        return f"Error: Directory '{directory}' does not exist"
    
    query_lower = query.lower()
    matches = []
    
    # Search all markdown files
    for md_file in search_path.rglob('*.md'):
        # Skip excluded directories
        rel_path = md_file.relative_to(PATHS.vault_path)
        if any(part in VAULT_EXCLUDE for part in rel_path.parts):
            continue
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # Check filename match
        name_match = query_lower in md_file.stem.lower()
        
        # Find content matches with context
        content_matches = []
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if query_lower in line.lower():
                content_matches.append((i, line.strip()[:100]))
        
        if name_match or content_matches:
            matches.append({
                'path': str(rel_path),
                'name_match': name_match,
                'content_matches': content_matches[:3],  # First 3 matches
                'total_matches': len(content_matches)
            })
        
        if len(matches) >= max_results:
            break
    
    if not matches:
        return f"No notes found matching '{query}'"
    
    result = [f"Search results for '{query}':"]
    result.append("")
    
    for m in matches:
        result.append(f"📄 {m['path']}")
        if m['name_match']:
            result.append("   ✓ Filename match")
        if m['content_matches']:
            for line_num, preview in m['content_matches']:
                result.append(f"   Line {line_num}: ...{preview}...")
            if m['total_matches'] > 3:
                result.append(f"   ({m['total_matches']} total matches)")
        result.append("")
    
    return '\n'.join(result)


@tool(
    description="""Get all wikilinks from a note. Use this to discover connected notes without reading the full content.
    Returns a list of linked notes that you can then explore.""",
    filepath="Path to the note relative to vault root",
    safe=True
)
def get_note_links(filepath: str) -> str:
    """Extract all wikilinks from a note."""
    try:
        full_path = _resolve_vault_path(filepath)
    except ValueError as e:
        return f"Error: {e}"
    
    if not full_path.exists():
        return f"Error: Note '{filepath}' does not exist"
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    links = _extract_wikilinks(content)
    
    if not links:
        return f"No wikilinks found in {filepath}"
    
    result = [f"Links in {filepath} ({len(links)} total):"]
    result.append("")
    
    for link in links:
        # Check if linked note exists
        link_path = PATHS.vault_path / f"{link}.md"
        exists = "✓" if link_path.exists() else "✗"
        result.append(f"  {exists} [[{link}]]")
    
    return '\n'.join(result)


# Export the tools
TOOLS = [
    list_vault,
    get_note_outline,
    read_note,
    read_note_section,
    search_vault,
    get_note_links,
]
