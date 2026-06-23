"""Fixer for literalinclude line number issues."""

import re
from typing import Optional

from .checker import LiteralIncludeChecker, LiteralIncludeDirective


class LiteralIncludeFixer:
    """Fixer that updates line numbers in literalinclude directives."""

    def __init__(self, checker: LiteralIncludeChecker):
        """Initialize the fixer.

        Args:
            checker: LiteralIncludeChecker instance
        """
        self.checker = checker

    def calculate_correct_lines(
        self,
        directive: LiteralIncludeDirective
    ) -> Optional[dict[str, str]]:
        """Calculate the correct line numbers for a directive.

        This attempts to determine what the line numbers should be based
        on the current state of the source file.

        Args:
            directive: The directive to fix

        Returns:
            Dictionary with 'lines' and/or 'emphasize_lines' keys with
            corrected specs, or None if unable to determine correct lines
        """
        if not directive.source_file.exists():
            return None

        # For now, this is a placeholder that returns the original specs
        # A more sophisticated implementation would:
        # 1. Look at the git history to see what changed
        # 2. Try to identify the original snippet by content matching
        # 3. Update the line numbers to match the new location

        # Simple approach: count lines in the source file and validate
        try:
            with open(directive.source_file, 'r') as f:
                total_lines = sum(1 for _ in f)

            result = {}

            # Check if current line specs are valid
            max_line = directive.max_line_number
            if max_line and max_line > total_lines:
                # Line numbers exceed file length, needs fixing
                # For now, just cap it to the file length
                if directive.lines_spec:
                    result['lines'] = self._adjust_line_spec(
                        directive.lines_spec,
                        total_lines
                    )
                if directive.emphasize_lines_spec:
                    result['emphasize_lines'] = self._adjust_line_spec(
                        directive.emphasize_lines_spec,
                        total_lines
                    )

            return result if result else None
        except (IOError, OSError):
            return None

    @staticmethod
    def _adjust_line_spec(spec: str, max_line: int) -> str:
        """Adjust a line specification to not exceed max_line.

        Args:
            spec: Line specification like '1-10,15,20-25'
            max_line: Maximum valid line number

        Returns:
            Adjusted line specification
        """
        parts = spec.split(',')
        adjusted_parts = []

        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                try:
                    start_num = int(start.strip())
                    end_num = int(end.strip())

                    if start_num > max_line:
                        continue  # Skip this range entirely

                    end_num = min(end_num, max_line)
                    adjusted_parts.append(f"{start_num}-{end_num}")
                except ValueError:
                    adjusted_parts.append(part)
            else:
                try:
                    line_num = int(part)
                    if line_num <= max_line:
                        adjusted_parts.append(part)
                except ValueError:
                    adjusted_parts.append(part)

        return ','.join(adjusted_parts) if adjusted_parts else '1'

    def fix_directive(
        self,
        directive: LiteralIncludeDirective,
        dry_run: bool = True
    ) -> bool:
        """Fix a literalinclude directive with outdated line numbers.

        Args:
            directive: The directive to fix
            dry_run: If True, don't actually modify files

        Returns:
            True if the directive was fixed (or would be fixed in dry run mode)
        """
        corrections = self.calculate_correct_lines(directive)

        if not corrections:
            return False

        try:
            content = directive.rst_file.read_text()
            lines = content.split('\n')

            # Find the directive and update it
            modified = False
            for i in range(
                    directive.rst_line_number - 1,
                    min(directive.rst_line_number + 20, len(lines))
            ):
                line = lines[i]

                if 'lines' in corrections and ':lines:' in line:
                    old_match = re.match(
                        r'(\s+):lines:\s+(.+?)$', line
                    )
                    if old_match:
                        indent = old_match.group(1)
                        lines[i] = (
                            f"{indent}:lines: {corrections['lines']}"
                        )
                        modified = True

                if (
                        'emphasize_lines' in corrections
                        and ':emphasize-lines:' in line
                ):
                    old_match = re.match(
                        r'(\s+):emphasize-lines:\s+(.+?)$', line
                    )
                    if old_match:
                        indent = old_match.group(1)
                        lines[i] = (
                            f"{indent}:emphasize-lines: "
                            f"{corrections['emphasize_lines']}"
                        )
                        modified = True

            if modified and not dry_run:
                directive.rst_file.write_text('\n'.join(lines))

            return modified
        except (IOError, OSError) as e:
            print(f"Error fixing {directive.rst_file}: {e}")
            return False

    def fix_all_outdated(
        self,
        search_dirs: Optional[list[str]] = None,
        dry_run: bool = True
    ) -> dict:
        """Fix all outdated literalinclude directives.

        Args:
            search_dirs: List of directory names to search
            dry_run: If True, don't actually modify files

        Returns:
            Dictionary with statistics about fixes
        """
        outdated = self.checker.find_outdated_directives(search_dirs)

        stats = {
            'total_outdated': len(outdated),
            'fixed': 0,
            'failed': 0,
            'details': []
        }

        for directive, reason in outdated:
            if self.fix_directive(directive, dry_run=dry_run):
                stats['fixed'] += 1
                stats['details'].append({
                    'file': str(directive.rst_file),
                    'line': directive.rst_line_number,
                    'status': 'fixed' if not dry_run else 'would_fix',
                    'reason': reason
                })
            else:
                stats['failed'] += 1
                stats['details'].append({
                    'file': str(directive.rst_file),
                    'line': directive.rst_line_number,
                    'status': 'failed',
                    'reason': reason
                })

        return stats
