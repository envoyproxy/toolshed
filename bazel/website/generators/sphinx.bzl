"""Sphinx generator skeleton (for extensibility testing)."""

load("//website:providers.bzl", "WebsiteGeneratorInfo")

def _sphinx_generator_impl(ctx):
    """Implementation for sphinx generator skeleton."""
    # This is a skeleton implementation that proves the framework supports Sphinx
    script = ctx.actions.declare_file(ctx.label.name + "_script.sh")
    
    ctx.actions.write(
        output = script,
        content = """#!/bin/bash
set -e

CONTENT_PATH="$1"
echo "Sphinx generator skeleton invoked with content path: $CONTENT_PATH"
echo "Accepted asset types: {accepts}"
echo "Output path: {output_path}"

# TODO: In a real implementation, this would:
# 1. Set up Sphinx configuration
# 2. Process RST content
# 3. Apply themes
# 4. Generate HTML output

# For now, create minimal output to prove the wiring works
mkdir -p {output_path}
cat > {output_path}/index.html <<'EOF'
<!DOCTYPE html>
<html>
<head><title>Sphinx Generator Skeleton</title></head>
<body>
<h1>Sphinx Generator Skeleton</h1>
<p>This is a skeleton implementation showing Sphinx support is viable.</p>
<p>Accepted types: {accepts}</p>
</body>
</html>
EOF

echo "Sphinx generator skeleton completed"
""".format(
            accepts = ", ".join(ctx.attr.accepts),
            output_path = ctx.attr.output_path,
        ),
        is_executable = True,
    )
    
    generator_info = WebsiteGeneratorInfo(
        executable = script,
        accepts = ctx.attr.accepts,
        output_path = ctx.attr.output_path,
        dev_server = None,
    )
    
    return [
        generator_info,
        DefaultInfo(
            executable = script,
            runfiles = ctx.runfiles(files = [script]),
        ),
    ]

sphinx_generator = rule(
    implementation = _sphinx_generator_impl,
    attrs = {
        "accepts": attr.string_list(
            default = ["rst", "markdown", "sphinx_theme", "css", "js", "static"],
            doc = "List of asset types this generator accepts",
        ),
        "output_path": attr.string(
            default = "_build/html",
            doc = "Where the generator puts output",
        ),
    },
    executable = True,
    doc = "Sphinx generator skeleton for extensibility testing",
)
