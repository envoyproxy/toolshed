"""Tests for literalinclude fixer."""

import tempfile
from pathlib import Path

from envoy.docs.literalinclude import checker, fixer


def test_fixer_adjust_line_spec():
    """Test adjusting line specifications to not exceed max line."""
    # Cap range that exceeds max
    adjusted = fixer.LiteralIncludeFixer._adjust_line_spec("1-100", 50)
    assert adjusted == "1-50"

    # Remove ranges that entirely exceed max
    adjusted = fixer.LiteralIncludeFixer._adjust_line_spec("60-100", 50)
    assert adjusted == "1"  # fallback

    # Mixed ranges and single lines
    adjusted = fixer.LiteralIncludeFixer._adjust_line_spec("1-10,55,60-70", 50)
    assert "1-10" in adjusted
    assert "55" not in adjusted
    assert "60-70" not in adjusted


def test_fixer_calculate_correct_lines():
    """Test calculating correct line numbers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create source file with 30 lines
        source = tmpdir / "source.yaml"
        source.write_text("line\n" * 30)

        rst = tmpdir / "test.rst"
        rst.write_text("test")

        # Directive that exceeds file length
        directive = checker.LiteralIncludeDirective(
            rst_file=rst,
            rst_line_number=1,
            source_file=source,
            lines_spec="1-50"
        )

        checker_obj = checker.LiteralIncludeChecker(tmpdir)
        fixer_obj = fixer.LiteralIncludeFixer(checker_obj)

        corrections = fixer_obj.calculate_correct_lines(directive)

        assert corrections is not None
        assert 'lines' in corrections
        # Should be capped to 30
        assert "30" in corrections['lines']


def test_fixer_fix_directive():
    """Test fixing a directive in an RST file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create source file
        source = tmpdir / "source.yaml"
        source.write_text("line\n" * 20)

        # Create RST file with outdated line numbers
        rst = tmpdir / "test.rst"
        rst_content = """
Documentation
=============

.. literalinclude:: source.yaml
   :lines: 1-50
   :emphasize-lines: 40-45
"""
        rst.write_text(rst_content)

        # Create directive
        directive = checker.LiteralIncludeDirective(
            rst_file=rst,
            rst_line_number=5,
            source_file=source,
            lines_spec="1-50",
            emphasize_lines_spec="40-45"
        )

        checker_obj = checker.LiteralIncludeChecker(tmpdir)
        fixer_obj = fixer.LiteralIncludeFixer(checker_obj)

        # Fix in dry-run mode first
        result = fixer_obj.fix_directive(directive, dry_run=True)
        assert result is True

        # File should not be modified yet
        assert "1-50" in rst.read_text()

        # Actually fix
        result = fixer_obj.fix_directive(directive, dry_run=False)
        assert result is True

        # File should be modified
        fixed_content = rst.read_text()
        assert "1-50" not in fixed_content
        assert "1-20" in fixed_content  # Capped to actual file length
