"""Yew/Rust generator skeleton (for WASM extensibility testing)."""

load("//website:providers.bzl", "WebsiteGeneratorInfo")

def _yew_generator_impl(ctx):
    """Implementation for Yew generator skeleton."""
    # This is a skeleton implementation that proves the framework supports Rust/WASM
    script = ctx.actions.declare_file(ctx.label.name + "_script.sh")
    
    ctx.actions.write(
        output = script,
        content = """#!/bin/bash
set -e

CONTENT_PATH="$1"
echo "Yew/Rust generator skeleton invoked with content path: $CONTENT_PATH"
echo "Accepted asset types: {accepts}"
echo "Output path: {output_path}"

# TODO: In a real implementation, this would:
# 1. Compile Rust components with wasm-pack
# 2. Bundle WASM modules
# 3. Generate JavaScript bindings
# 4. Assemble static assets
# 5. Create final HTML with WASM loader

# For now, create minimal output to prove the wiring works
mkdir -p {output_path}
cat > {output_path}/index.html <<'EOF'
<!DOCTYPE html>
<html>
<head>
<title>Yew/WASM Generator Skeleton</title>
<script type="module">
// Placeholder for WASM loading
console.log("Yew/WASM framework ready");
</script>
</head>
<body>
<h1>Yew/WASM Generator Skeleton</h1>
<p>This is a skeleton implementation showing Rust/WASM support is viable.</p>
<p>Accepted types: {accepts}</p>
<div id="app"><!-- Yew app would mount here --></div>
</body>
</html>
EOF

echo "Yew generator skeleton completed"
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

yew_generator = rule(
    implementation = _yew_generator_impl,
    attrs = {
        "accepts": attr.string_list(
            default = ["rust_component", "css", "js", "static", "wasm"],
            doc = "List of asset types this generator accepts",
        ),
        "output_path": attr.string(
            default = "dist",
            doc = "Where the generator puts output",
        ),
    },
    executable = True,
    doc = "Yew/Rust generator skeleton for WASM extensibility testing",
)

def rust_assets(
        name,
        srcs = None,
        deps = None,
        prefix = "components",
        **kwargs):
    """Create Rust component assets (for Yew framework).
    
    Args:
        name: Name of the target
        srcs: Rust source files
        deps: Dependencies
        prefix: Mount point (default: "components")
        **kwargs: Additional arguments
    """
    # Import here to avoid circular dependency
    load("//website:assets.bzl", "static_assets")
    
    static_assets(
        name = name,
        srcs = srcs,
        deps = deps,
        asset_type = "rust_component",
        prefix = prefix,
        **kwargs
    )
