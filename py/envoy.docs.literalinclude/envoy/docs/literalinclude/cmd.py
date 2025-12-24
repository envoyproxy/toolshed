"""Command-line interface for literalinclude checker/fixer."""

import argparse
import json
import sys
from pathlib import Path

from .checker import LiteralIncludeChecker
from .fixer import LiteralIncludeFixer


def main(argv=None):
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Check and fix literalinclude directives with outdated line numbers'
    )
    parser.add_argument(
        'repo_root',
        type=Path,
        help='Root directory of the repository'
    )
    parser.add_argument(
        '--dirs',
        nargs='+',
        default=['docs', 'api'],
        help='Directories to search for RST files (default: docs api)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Fix outdated line numbers (default: dry-run mode)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all literalinclude directives (not just outdated ones)'
    )
    
    args = parser.parse_args(argv)
    
    # Initialize checker
    checker = LiteralIncludeChecker(args.repo_root)
    
    if args.list:
        # List all directives
        return list_directives(checker, args)
    else:
        # Check and optionally fix outdated directives
        return check_and_fix(checker, args)


def list_directives(checker, args):
    """List all literalinclude directives."""
    rst_files = checker.find_rst_files(args.dirs)
    
    all_directives = []
    for rst_file in rst_files:
        directives = checker.parse_rst_file(rst_file)
        all_directives.extend(directives)
    
    if args.json:
        output = []
        for directive in all_directives:
            output.append({
                'rst_file': str(directive.rst_file),
                'rst_line': directive.rst_line_number,
                'source_file': str(directive.source_file),
                'lines': directive.lines_spec,
                'emphasize_lines': directive.emphasize_lines_spec,
                'start_after': directive.start_after,
                'end_before': directive.end_before,
            })
        print(json.dumps(output, indent=2))
    else:
        print(f"Found {len(all_directives)} literalinclude directives:\n")
        for directive in all_directives:
            print(f"  {directive.rst_file}:{directive.rst_line_number}")
            print(f"    -> {directive.source_file}")
            if directive.lines_spec:
                print(f"       :lines: {directive.lines_spec}")
            if directive.emphasize_lines_spec:
                print(f"       :emphasize-lines: {directive.emphasize_lines_spec}")
            print()
    
    return 0


def check_and_fix(checker, args):
    """Check for outdated directives and optionally fix them."""
    fixer = LiteralIncludeFixer(checker)
    
    # Find outdated directives
    outdated = checker.find_outdated_directives(args.dirs)
    
    if not outdated:
        if not args.json:
            print("✓ No outdated literalinclude directives found!")
        else:
            print(json.dumps({'status': 'ok', 'outdated_count': 0}))
        return 0
    
    # Fix them if requested
    if args.fix:
        stats = fixer.fix_all_outdated(args.dirs, dry_run=False)
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Fixed {stats['fixed']} out of {stats['total_outdated']} outdated directives")
            print(f"Failed to fix: {stats['failed']}")
            print("\nDetails:")
            for detail in stats['details']:
                status_symbol = '✓' if detail['status'] == 'fixed' else '✗'
                print(f"  {status_symbol} {detail['file']}:{detail['line']}")
                print(f"     {detail['reason']}")
        
        return 1 if stats['failed'] > 0 else 0
    else:
        # Dry run - just report
        if args.json:
            output = []
            for directive, reason in outdated:
                output.append({
                    'rst_file': str(directive.rst_file),
                    'rst_line': directive.rst_line_number,
                    'source_file': str(directive.source_file),
                    'reason': reason,
                })
            print(json.dumps({
                'status': 'outdated_found',
                'count': len(outdated),
                'directives': output
            }, indent=2))
        else:
            print(f"Found {len(outdated)} outdated literalinclude directives:\n")
            for directive, reason in outdated:
                print(f"  {directive.rst_file}:{directive.rst_line_number}")
                print(f"    -> {directive.source_file}")
                if directive.lines_spec:
                    print(f"       :lines: {directive.lines_spec}")
                print(f"    Reason: {reason}")
                print()
            
            print(f"\nRun with --fix to automatically update line numbers")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
