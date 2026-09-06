"""Context retriever: handles @file mentions, code searching, and relevance matching."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from termcoder.context.indexer import CodebaseIndexer


class ContextRetriever:
    """Retrieves file contents, resolves mentions, and searches codebase."""

    def __init__(self, indexer: CodebaseIndexer) -> None:
        self.indexer = indexer

    def resolve_mentions(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Detect @file or @dir mentions in user prompt and load their contents.
        Returns cleaned text and list of attached file context objects:
        [{"path": "...", "content": "..."}]
        """
        attached: List[Dict[str, str]] = []
        # Match @path/to/file or @"path with spaces"
        mention_pattern = re.compile(r'@("([^"]+)"|([a-zA-Z0-9_\-\.\/\\]+))')

        def _replace_mention(match: re.Match) -> str:
            raw_path = match.group(2) if match.group(2) else match.group(3)
            # Remove trailing punctuation like commas, periods, colons
            clean_path = raw_path.rstrip(".,;:!?")
            resolved = self._find_matching_file(clean_path)
            if resolved and resolved.is_file():
                try:
                    content = resolved.read_text(encoding="utf-8", errors="ignore")
                    rel_path = str(resolved.relative_to(self.indexer.root)).replace("\\", "/")
                    attached.append({"path": rel_path, "content": content})
                    return f"`@{rel_path}`"
                except Exception:
                    pass
            return match.group(0)

        cleaned_text = mention_pattern.sub(_replace_mention, text)
        return cleaned_text, attached

    def _find_matching_file(self, mention: str) -> Optional[Path]:
        """Try exact match, relative match, or case-insensitive match."""
        # 1. Direct path from root
        target = (self.indexer.root / mention).resolve()
        if target.exists() and not self.indexer.is_ignored(target):
            return target

        # 2. Search indexed files by name
        mention_name = Path(mention).name.lower()
        for file_path in self.indexer.list_files():
            if file_path.name.lower() == mention_name:
                return file_path

        return None

    def search_code(
        self,
        query: str,
        is_regex: bool = False,
        path_filter: str = "",
        max_matches: int = 40,
    ) -> List[Dict[str, Any]]:
        """Search codebase for matches with line numbers and snippets."""
        results = []
        pattern = None

        if is_regex:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error:
                pattern = re.compile(re.escape(query), re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        files = self.indexer.list_files()
        for file_path in files:
            rel_str = str(file_path.relative_to(self.indexer.root)).replace("\\", "/")
            if path_filter and path_filter.lower() not in rel_str.lower():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    results.append({
                        "file": rel_str,
                        "line": idx,
                        "content": line.strip()[:200],
                    })
                    if len(results) >= max_matches:
                        return results

        return results
