"""Tests for codebase indexing, repo map generation, and context retrieval."""

import tempfile
from pathlib import Path
import pytest

from termcoder.context.indexer import CodebaseIndexer
from termcoder.context.repo_map import RepoMapGenerator
from termcoder.context.retriever import ContextRetriever


def test_indexer_file_discovery_and_ignores():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create files
        (root / "main.py").write_text("def hello(): pass")
        (root / "utils.py").write_text("class Helper: pass")
        (root / "ignored.pyc").write_bytes(b"\x00\x01")

        # Create node_modules and .git
        (root / "node_modules").mkdir()
        (root / "node_modules" / "pkg.js").write_text("console.log('skip')")

        indexer = CodebaseIndexer(root)
        files = indexer.list_files()
        rel_paths = indexer.get_relative_paths()

        assert "main.py" in rel_paths
        assert "utils.py" in rel_paths
        assert not any("node_modules" in p for p in rel_paths)
        assert not any(p.endswith(".pyc") for p in rel_paths)


def test_repo_map_symbol_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code = """
class DataService:
    def fetch_all(self):
        pass

    def save(self):
        pass

def process_pipeline():
    pass
"""
        (root / "service.py").write_text(code)
        indexer = CodebaseIndexer(root)
        repo_map_gen = RepoMapGenerator(indexer)
        repo_map = repo_map_gen.generate_map()

        assert "service.py" in repo_map
        assert "class DataService" in repo_map
        assert "def process_pipeline" in repo_map


def test_context_retriever_mentions():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "calculator.py").write_text("def add(a, b): return a + b")

        indexer = CodebaseIndexer(root)
        retriever = ContextRetriever(indexer)

        prompt = "Can you explain @calculator.py and how it works?"
        cleaned, attached = retriever.resolve_mentions(prompt)

        assert len(attached) == 1
        assert attached[0]["path"] == "calculator.py"
        assert "def add(a, b): return a + b" in attached[0]["content"]
        assert "`@calculator.py`" in cleaned


def test_context_retriever_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "file1.py").write_text("ALPHA_CONSTANT = 42\nbeta = 10")
        (root / "file2.py").write_text("ALPHA_CONSTANT = 99\ngamma = 20")

        indexer = CodebaseIndexer(root)
        retriever = ContextRetriever(indexer)

        results = retriever.search_code("ALPHA_CONSTANT")
        assert len(results) == 2
        assert any(r["file"] == "file1.py" for r in results)
        assert any(r["file"] == "file2.py" for r in results)
