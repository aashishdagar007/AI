"""Structural repository map generator extracting classes, functions, and definitions."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional
from termcoder.context.indexer import CodebaseIndexer


class RepoMapGenerator:
    """Generates a concise architectural map of symbols across project files."""

    def __init__(self, indexer: CodebaseIndexer) -> None:
        self.indexer = indexer

    def generate_map(self, max_tokens_approx: int = 4000) -> str:
        """Generate a repository map listing files and key symbols."""
        files = self.indexer.list_files(max_files=400)
        lines: List[str] = ["# Codebase Structure & Key Symbols:"]

        for file_path in files:
            rel_path = str(file_path.relative_to(self.indexer.root)).replace("\\", "/")
            symbols = self._extract_symbols(file_path)
            if symbols:
                sym_str = ", ".join(symbols[:15])
                if len(symbols) > 15:
                    sym_str += f", +{len(symbols) - 15} more"
                lines.append(f"- {rel_path} -> {sym_str}")
            else:
                lines.append(f"- {rel_path}")

            # Safety cap on length
            if sum(len(l) for l in lines) > max_tokens_approx * 4:
                lines.append("... [remaining repository symbols truncated for brevity]")
                break

        return "\n".join(lines)

    def _extract_symbols(self, file_path: Path) -> List[str]:
        """Extract top-level and class symbols from source file."""
        suffix = file_path.suffix.lower()
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        if suffix == ".py":
            return self._extract_python_symbols(content)
        elif suffix in {".js", ".ts", ".jsx", ".tsx", ".mjs"}:
            return self._extract_js_symbols(content)
        elif suffix in {".go", ".rs", ".java", ".cpp", ".c", ".cs"}:
            return self._extract_generic_symbols(content)
        return []

    def _extract_python_symbols(self, code: str) -> List[str]:
        """Parse Python AST to extract class names, methods, and functions."""
        symbols: List[str] = []
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    methods = [
                        n.name
                        for n in node.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not n.name.startswith("__")
                    ]
                    if methods:
                        symbols.append(f"class {node.name}({', '.join(methods[:4])})")
                    else:
                        symbols.append(f"class {node.name}")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"def {node.name}()")
        except Exception:
            # Fallback regex if syntax error or partial code
            for match in re.finditer(r"^(?:def|class)\s+([a-zA-Z0-9_]+)", code, re.MULTILINE):
                symbols.append(match.group(1))
        return symbols

    def _extract_js_symbols(self, code: str) -> List[str]:
        """Regex extractor for JS/TS functions, classes, exports."""
        symbols: List[str] = []
        # Class declarations
        for m in re.finditer(r"class\s+([a-zA-Z0-9_]+)", code):
            symbols.append(f"class {m.group(1)}")
        # Functions and arrow exports
        for m in re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)", code):
            symbols.append(f"function {m.group(1)}")
        for m in re.finditer(r"(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", code):
            symbols.append(f"fn {m.group(1)}")
        return symbols

    def _extract_generic_symbols(self, code: str) -> List[str]:
        """Regex extractor for Go, Rust, Java, C#."""
        symbols: List[str] = []
        # Go: func (r Receiver) Name or func Name
        for m in re.finditer(r"func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(", code):
            symbols.append(f"func {m.group(1)}")
        # Rust: fn name, struct name, impl name
        for m in re.finditer(r"(?:pub\s+)?(?:fn|struct|enum|trait)\s+([a-zA-Z0-9_]+)", code):
            symbols.append(m.group(1))
        return symbols
