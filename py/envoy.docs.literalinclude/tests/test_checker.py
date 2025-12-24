"""Tests for literalinclude checker."""

import tempfile
from pathlib import Path

import pytest

from envoy.docs.literalinclude import checker


def test_literal_include_directive_parse_line_spec():
    """Test parsing line specifications."""
    # Simple range
    lines = checker.LiteralIncludeDirective._parse_line_spec("1-10")
    assert lines == list(range(1, 11))
    
    # Multiple ranges and single lines
    lines = checker.LiteralIncludeDirective._parse_line_spec("1-5,10,15-20")
    assert 1 in lines
    assert 5 in lines
    assert 10 in lines
    assert 15 in lines
    assert 20 in lines
    assert 11 not in lines
    
    # Single line
    lines = checker.LiteralIncludeDirective._parse_line_spec("42")
    assert lines == [42]


def test_literal_include_directive_max_line_number():
    """Test getting maximum line number from directive."""
    directive = checker.LiteralIncludeDirective(
        rst_file=Path("test.rst"),
        rst_line_number=1,
        source_file=Path("source.yaml"),
        lines_spec="1-10,15,20-25"
    )
    assert directive.max_line_number == 25
    
    directive = checker.LiteralIncludeDirective(
        rst_file=Path("test.rst"),
        rst_line_number=1,
        source_file=Path("source.yaml"),
        emphasize_lines_spec="1-5"
    )
    assert directive.max_line_number == 5
    
    directive = checker.LiteralIncludeDirective(
        rst_file=Path("test.rst"),
        rst_line_number=1,
        source_file=Path("source.yaml")
    )
    assert directive.max_line_number is None


def test_literal_include_checker_parse_rst():
    """Test parsing RST files for literalinclude directives."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test RST file
        rst_content = """
Test Documentation
==================

.. literalinclude:: /config/example.yaml
   :lines: 1-10
   :emphasize-lines: 5-7

Some text.

.. literalinclude:: ../other/file.yaml
   :lines: 20-30
"""
        rst_file = tmpdir / "test.rst"
        rst_file.write_text(rst_content)
        
        # Create source files
        (tmpdir / "config").mkdir()
        (tmpdir / "config" / "example.yaml").write_text("content\n" * 50)
        (tmpdir / "other").mkdir()
        (tmpdir / "other" / "file.yaml").write_text("content\n" * 50)
        
        # Parse
        checker_obj = checker.LiteralIncludeChecker(tmpdir)
        directives = checker_obj.parse_rst_file(rst_file)
        
        assert len(directives) == 2
        assert directives[0].lines_spec == "1-10"
        assert directives[0].emphasize_lines_spec == "5-7"
        assert directives[0].max_line_number == 10
        assert directives[1].lines_spec == "20-30"
        assert directives[1].max_line_number == 30


def test_literal_include_checker_find_rst_files():
    """Test finding RST files in directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create directory structure
        docs = tmpdir / "docs"
        docs.mkdir()
        (docs / "test1.rst").write_text("test")
        (docs / "subdir").mkdir()
        (docs / "subdir" / "test2.rst").write_text("test")
        
        api = tmpdir / "api"
        api.mkdir()
        (api / "test3.rst").write_text("test")
        
        # Find files
        checker_obj = checker.LiteralIncludeChecker(tmpdir)
        rst_files = checker_obj.find_rst_files()
        
        assert len(rst_files) == 3
        assert any("test1.rst" in str(f) for f in rst_files)
        assert any("test2.rst" in str(f) for f in rst_files)
        assert any("test3.rst" in str(f) for f in rst_files)


def test_literal_include_checker_resolve_paths():
    """Test resolving source paths from RST files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        rst_file = tmpdir / "docs" / "guide.rst"
        rst_file.parent.mkdir(parents=True)
        
        checker_obj = checker.LiteralIncludeChecker(tmpdir)
        
        # Absolute path from root
        resolved = checker_obj._resolve_source_path(rst_file, "/config/example.yaml")
        assert resolved == tmpdir / "config" / "example.yaml"
        
        # Relative path
        resolved = checker_obj._resolve_source_path(rst_file, "../config/example.yaml")
        assert resolved.name == "example.yaml"
        assert "config" in str(resolved)
