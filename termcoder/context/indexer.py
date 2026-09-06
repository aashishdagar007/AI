"""Codebase indexer and directory scanner with .gitignore support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set, Tuple

# Default directories and files to ignore across all languages
DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".termcoder",
    ".idea",
    ".vscode",
    ".eggs",
    "*.egg-info",
}

# Binary and non-text extensions to exclude from code index
BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".ogg", ".zip", ".tar", ".gz", ".7z",
    ".pdf", ".docx", ".xlsx", ".pptx", ".ttf", ".woff", ".woff2",
    ".db", ".sqlite", ".sqlite3", ".parquet"
}


class CodebaseIndexer:
    """Scans and indexes workspace files respecting .gitignore."""

    def __init__(self, root_dir: Path | str = ".") -> None:
        self.root = Path(root_dir).resolve()
        self.ignore_patterns: List[str] = []
        self._load_gitignores()

    def _load_gitignores(self) -> None:
        """Read .gitignore and .aiignore rules from root."""
        for filename in [".gitignore", ".aiignore"]:
            ignore_path = self.root / filename
            if ignore_path.exists():
                try:
                    with open(ignore_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped and not stripped.startswith("#"):
                                self.ignore_patterns.append(stripped.rstrip("/"))
                except Exception:
                    pass

    def is_ignored(self, path: Path) -> bool:
        """Check if a path matches ignore patterns or binary extensions."""
        rel_str = str(path.relative_to(self.root)).replace("\\", "/")
        parts = rel_str.split("/")

        # Check against default ignored directory names
        for part in parts:
            if part in DEFAULT_IGNORES:
                return True
            if part.endswith(".egg-info"):
                return True

        # Check extension
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True

        # Check gitignore patterns
        for pattern in self.ignore_patterns:
            clean_pat = pattern.strip("/")
            if pattern.startswith("*.") and path.name.endswith(pattern[1:]):
                return True
            if clean_pat in parts or rel_str == clean_pat or rel_str.startswith(clean_pat + "/"):
                return True

        return False

    def list_files(self, max_files: int = 1500) -> List[Path]:
        """Scan workspace and return a list of non-ignored code files."""
        indexed_files: List[Path] = []
        try:
            for root, dirs, files in os.walk(self.root):
                # Prune ignored directories in-place to speed up walk
                rel_root = Path(root).resolve()
                dirs[:] = [
                    d for d in dirs
                    if d not in DEFAULT_IGNORES and not self.is_ignored(rel_root / d)
                ]

                for file in files:
                    file_path = rel_root / file
                    if not self.is_ignored(file_path):
                        indexed_files.append(file_path)
                        if len(indexed_files) >= max_files:
                            return indexed_files
        except Exception:
            pass

        return indexed_files

    def get_relative_paths(self) -> List[str]:
        """Return list of project files as relative POSIX paths."""
        return [str(f.relative_to(self.root)).replace("\\", "/") for f in self.list_files()]

    def generate_file_tree(self, max_depth: int = 4) -> str:
        """Generate a visual ASCII tree of the project structure."""
        files = self.get_relative_paths()
        if not files:
            return "(Empty project or no indexed files)"

        tree_lines = [f"{self.root.name}/"]
        dirs_seen: Set[str] = set()

        for path_str in sorted(files)[:250]:
            parts = path_str.split("/")
            if len(parts) > max_depth + 1:
                continue
            indent = "  " * (len(parts) - 1)
            tree_lines.append(f"{indent}├── {parts[-1]}")

        if len(files) > 250:
            tree_lines.append(f"... and {len(files) - 250} more files.")

        return "\n".join(tree_lines)
