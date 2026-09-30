Literalinclude Line Number Checker
===================================

A tool to automatically detect and fix outdated line numbers in Sphinx ``literalinclude`` directives.

Problem
-------

When using ``literalinclude`` directives in Sphinx documentation, you often specify line numbers to include specific portions of code:

.. code-block:: rst

   .. literalinclude:: /path/to/config.yaml
      :lines: 10-25
      :emphasize-lines: 15-18

However, when the source files change (lines are added or removed), these line numbers become outdated, potentially showing the wrong code or breaking the documentation build.

Solution
--------

This tool:

1. Scans RST files for ``literalinclude`` directives with line specifications
2. Uses git history to detect when source files changed after the RST files
3. Identifies directives where line changes affect the specified range
4. Optionally fixes the line numbers automatically

Installation
------------

.. code-block:: bash

   pip install envoy.docs.literalinclude

Usage
-----

Check for outdated directives (dry run):

.. code-block:: bash

   literalinclude-check /path/to/repo

Check specific directories:

.. code-block:: bash

   literalinclude-check /path/to/repo --dirs docs api

Fix outdated directives:

.. code-block:: bash

   literalinclude-check /path/to/repo --fix

List all literalinclude directives:

.. code-block:: bash

   literalinclude-check /path/to/repo --list

JSON output:

.. code-block:: bash

   literalinclude-check /path/to/repo --json

How It Works
------------

1. **Discovery**: Finds all RST files in specified directories (default: ``docs`` and ``api``)
2. **Parsing**: Extracts ``literalinclude`` directives with their options:
   
   - ``:lines:`` - Line ranges to include
   - ``:emphasize-lines:`` - Lines to emphasize
   - Source file path

3. **Git Analysis**: For each directive:
   
   - Checks when the RST file was last modified
   - Checks when the source file was last modified
   - If source changed after RST, analyzes the diff

4. **Detection**: Flags directives as outdated if:
   
   - Lines were added/removed in the source file
   - Changes occurred at or before the maximum line number referenced
   
5. **Fixing**: Updates the line numbers in RST files to match current source

Limitations
-----------

- Requires a git repository
- Best-effort fixing - may not always determine correct new line numbers
- Currently focused on ``:lines:`` and ``:emphasize-lines:`` options
- Does not handle ``:start-after:`` and ``:end-before:`` markers yet

License
-------

Apache License 2.0
