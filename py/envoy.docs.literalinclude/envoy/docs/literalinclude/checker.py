"""Checker for literalinclude directives in RST files."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LiteralIncludeDirective:
    """Represents a literalinclude directive found in an RST file."""

    rst_file: Path
    rst_line_number: int
    source_file: Path
    lines_spec: Optional[str] = None
    emphasize_lines_spec: Optional[str] = None
    start_after: Optional[str] = None
    end_before: Optional[str] = None

    @property
    def has_line_numbers(self) -> bool:
        """Check if this directive has line number specifications."""
        return (
            self.lines_spec is not None
            or self.emphasize_lines_spec is not None
        )

    @property
    def max_line_number(self) -> Optional[int]:
        """Get the maximum line number referenced in this directive."""
        max_line = None

        for spec in [self.lines_spec, self.emphasize_lines_spec]:
            if spec:
                numbers = self._parse_line_spec(spec)
                if numbers:
                    spec_max = max(numbers)
                    if max_line is None or spec_max > max_line:
                        max_line = spec_max

        return max_line

    @staticmethod
    def _parse_line_spec(spec: str) -> list[int]:
        """Parse a line specification like '1-10,15,20-25' into individual line
        numbers."""
        lines = []
        parts = spec.split(',')

        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                try:
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    lines.extend(range(start_num, end_num + 1))
                except ValueError:
                    continue
            else:
                try:
                    lines.append(int(part))
                except ValueError:
                    continue

        return lines


class LiteralIncludeChecker:
    """Checker that finds and validates literalinclude directives."""

    # Regex patterns for parsing literalinclude directives
    LITERALINCLUDE_RE = re.compile(
        r'^\.\.\s+literalinclude::\s+(.+?)$',
        re.MULTILINE
    )
    LINES_RE = re.compile(r'^\s+:lines:\s+(.+?)$', re.MULTILINE)
    EMPHASIZE_LINES_RE = re.compile(r'^\s+:emphasize-lines:\s+(.+?)$', re.MULTILINE)  # noqa: E501
    START_AFTER_RE = re.compile(r'^\s+:start-after:\s+(.+?)$', re.MULTILINE)
    END_BEFORE_RE = re.compile(r'^\s+:end-before:\s+(.+?)$', re.MULTILINE)

    def __init__(self, repo_root: Path):
        """Initialize the checker.

        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = Path(repo_root).resolve()

    def find_rst_files(self, search_dirs: Optional[list[str]] = None) -> list[Path]:  # noqa: E501
        """Find all RST files in specified directories.

        Args:
            search_dirs: List of directory names to search (default: ['docs', 'api'])  # noqa: E501

        Returns:
            List of Path objects for RST files
        """
        if search_dirs is None:
            search_dirs = ['docs', 'api']

        rst_files = []
        for search_dir in search_dirs:
            dir_path = self.repo_root / search_dir
            if dir_path.exists():
                rst_files.extend(dir_path.rglob('*.rst'))

        return rst_files

    def parse_rst_file(self, rst_file: Path) -> list[LiteralIncludeDirective]:
        """Parse an RST file to find literalinclude directives.

        Args:
            rst_file: Path to the RST file

        Returns:
            List of LiteralIncludeDirective objects
        """
        directives = []

        try:
            content = rst_file.read_text()
        except (IOError, OSError) as e:
            print(f"Warning: Could not read {rst_file}: {e}")
            return directives

        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            match = self.LITERALINCLUDE_RE.match(line)
            if match:
                source_path_str = match.group(1).strip()

                # Resolve the source file path relative to RST file
                source_file = self._resolve_source_path(rst_file, source_path_str)  # noqa: E501

                # Look ahead for options
                directive = LiteralIncludeDirective(
                    rst_file=rst_file,
                    rst_line_number=i,
                    source_file=source_file
                )

                # Parse options in following lines
                j = i
                while j < len(lines) and (lines[j].startswith('   :') or lines[j].strip() == ''):  # noqa: E501
                    option_line = lines[j]

                    if match := self.LINES_RE.match(option_line):
                        directive.lines_spec = match.group(1).strip()
                    elif match := self.EMPHASIZE_LINES_RE.match(option_line):
                        directive.emphasize_lines_spec = match.group(1).strip()
                    elif match := self.START_AFTER_RE.match(option_line):
                        directive.start_after = match.group(1).strip()
                    elif match := self.END_BEFORE_RE.match(option_line):
                        directive.end_before = match.group(1).strip()

                    j += 1

                directives.append(directive)

        return directives

    def _resolve_source_path(self, rst_file: Path, source_path_str: str) -> Path:  # noqa: E501
        """Resolve a source file path from a literalinclude directive.

        Args:
            rst_file: The RST file containing the directive
            source_path_str: The path string from the directive

        Returns:
            Resolved Path object
        """
        # Handle absolute paths from repo root
        if source_path_str.startswith('/'):
            return self.repo_root / source_path_str.lstrip('/')

        # Handle relative paths
        return (rst_file.parent / source_path_str).resolve()

    def get_file_last_modified(self, file_path: Path) -> Optional[str]:
        """Get the last git commit that modified a file.

        Args:
            file_path: Path to the file

        Returns:
            Commit hash or None if not in git
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H', '--', str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_file_changes_since(self, file_path: Path, since_commit: str) -> Optional[dict]:  # noqa: E501
        """Get line changes in a file since a specific commit.

        Args:
            file_path: Path to the file
            since_commit: Commit hash to compare against

        Returns:
            Dictionary with 'added_lines' and 'removed_lines' lists of line numbers,  # noqa: E501
            or None if unable to get changes
        """
        try:
            # Get the diff with line numbers
            result = subprocess.run(
                ['git', 'diff', '--unified=0', since_commit, 'HEAD', '--', str(file_path)],  # noqa: E501
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )

            diff_output = result.stdout
            if not diff_output.strip():
                return {'added_lines': [], 'removed_lines': []}

            added_lines = []
            removed_lines = []

            # Parse unified diff format more accurately
            current_old_start = None
            current_new_start = None

            for line in diff_output.split('\n'):
                if line.startswith('@@'):
                    # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@  # noqa: E501
                    match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)  # noqa: E501
                    if match:
                        current_old_start = int(match.group(1))
                        current_new_start = int(match.group(3))
                elif line.startswith('-') and not line.startswith('---'):
                    # Line was removed
                    if current_old_start is not None:
                        removed_lines.append(current_old_start)
                        current_old_start += 1
                elif line.startswith('+') and not line.startswith('+++'):
                    # Line was added
                    if current_new_start is not None:
                        added_lines.append(current_new_start)
                        current_new_start += 1
                elif line.startswith(' '):
                    # Context line - advance both counters
                    if current_old_start is not None:
                        current_old_start += 1
                    if current_new_start is not None:
                        current_new_start += 1

            return {
                'added_lines': added_lines,
                'removed_lines': removed_lines
            }
        except subprocess.CalledProcessError:
            return None

    def check_directive_outdated(self, directive: LiteralIncludeDirective) -> bool:  # noqa: E501
        """Check if a literalinclude directive has outdated line numbers.

        Args:
            directive: The directive to check

        Returns:
            True if the directive is potentially outdated
        """
        # Skip if no line numbers are specified
        if not directive.has_line_numbers:
            return False

        # Check if files exist
        if not directive.rst_file.exists() or not directive.source_file.exists():  # noqa: E501
            return False

        # Get last modification times
        rst_commit = self.get_file_last_modified(directive.rst_file)
        source_commit = self.get_file_last_modified(directive.source_file)

        if not rst_commit or not source_commit:
            return False

        # If source file was modified after RST file, check for changes
        try:
            # Check if source was modified after RST
            result = subprocess.run(
                ['git', 'log', '--format=%H', '--', str(directive.source_file)],  # noqa: E501
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            source_commits_str = result.stdout.strip()
            if not source_commits_str:
                return False
            source_commits = source_commits_str.split('\n')

            result = subprocess.run(
                ['git', 'log', '--format=%H', '--', str(directive.rst_file)],  # noqa: E501
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            rst_commits_str = result.stdout.strip()
            if not rst_commits_str:
                return False
            rst_commits = rst_commits_str.split('\n')

            # Find the commit where the directive was last modified
            # Simple heuristic: if source file has commits after the RST's last commit  # noqa: E501
            if source_commits and rst_commits:
                rst_last_idx = len(source_commits)  # Assume all source commits are after  # noqa: E501
                try:
                    rst_last_idx = source_commits.index(rst_commits[0])
                except ValueError:
                    pass

                # Source was modified after RST
                if rst_last_idx > 0:
                    # Check what changed
                    changes = self.get_file_changes_since(
                        directive.source_file,
                        rst_commit
                    )

                    if changes:
                        max_line = directive.max_line_number
                        if max_line:
                            # Check if changes affect lines up to max_line
                            for line_num in changes['added_lines'] + changes['removed_lines']:  # noqa: E501
                                if line_num <= max_line:
                                    return True

            return False
        except subprocess.CalledProcessError:
            return False

    def find_outdated_directives(
        self,
        search_dirs: Optional[list[str]] = None
    ) -> list[tuple[LiteralIncludeDirective, str]]:
        """Find all outdated literalinclude directives.

        Args:
            search_dirs: List of directory names to search

        Returns:
            List of tuples (directive, reason) for outdated directives
        """
        outdated = []
        rst_files = self.find_rst_files(search_dirs)

        for rst_file in rst_files:
            directives = self.parse_rst_file(rst_file)

            for directive in directives:
                if self.check_directive_outdated(directive):
                    reason = (
                        f"Source file '{directive.source_file.name}' was modified "  # noqa: E501
                        f"after RST file '{directive.rst_file.name}' and changes "  # noqa: E501
                        f"affect lines <= {directive.max_line_number}"
                    )
                    outdated.append((directive, reason))

        return outdated
