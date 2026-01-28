# WAMR (WebAssembly Micro Runtime) Bazel Module

This bzlmod module provides a pure `rules_cc` build for WAMR (WebAssembly Micro Runtime) version 2.4.4.

## Features

- **Pure rules_cc build**: No cmake or foreign_cc required
- **Configurable features**: Control runtime behavior via build flags
- **Cross-platform**: Supports Linux, macOS, with architecture-specific optimizations
- **Production defaults**: Minimal footprint with optional debug features

## Usage

Add to your `MODULE.bazel`:

```starlark
bazel_dep(name = "wamr", version = "2.4.4.envoy")
```

Use in your BUILD file:

```starlark
cc_binary(
    name = "my_wasm_runner",
    srcs = ["main.c"],
    deps = ["@wamr//:iwasm"],
)
```

## Available Targets

- `@wamr//:iwasm` - Main WAMR library
- `@wamr//:wamr_lib` - Alias for compatibility

## Configuration Flags

### Runtime Mode
- `--@wamr//bazel:fast_interp=true` (default: True)  
  Enable fast interpreter for better performance

### Debug Features (default: False)
- `--@wamr//bazel:dump_call_stack=true`  
  Enable call stack dumping for debugging
- `--@wamr//bazel:custom_name_section=true`  
  Enable custom name section support
- `--@wamr//bazel:load_custom_section=true`  
  Enable loading custom sections

### WebAssembly Features
- `--@wamr//bazel:bulk_memory=true` (default: True)  
  Enable bulk memory operations
- `--@wamr//bazel:ref_types=true` (default: True)  
  Enable reference types
- `--@wamr//bazel:tail_call=true` (default: True)  
  Enable tail call optimization
- `--@wamr//bazel:simd=true` (default: False)  
  Enable SIMD support

## Examples

### Development build with debugging:
```bash
bazel build //your:target \
  --@wamr//bazel:dump_call_stack=true \
  --@wamr//bazel:custom_name_section=true
```

### Production build (defaults are already optimized):
```bash
bazel build //your:target
```

### Enable SIMD support:
```bash
bazel build //your:target --@wamr//bazel:simd=true
```

## Platform Support

- **Linux**: x86_64, aarch64
- **macOS**: x86_64, aarch64 (Apple Silicon)
- **Architecture fallback**: Uses general C implementation for unsupported architectures

## Disabled Features

This module intentionally disables:
- AOT (Ahead-of-Time compilation)
- JIT (Just-in-Time compilation)
- WASI libc (both builtin and full)
- Multi-module support

These features are not needed for basic WebAssembly interpretation and keeping them disabled reduces binary size and complexity.

## Version

WAMR 2.4.4 (WAMR-2.4.4 tag from upstream)

## License

Apache 2.0 with LLVM exception (same as upstream WAMR)

## References

- Upstream: https://github.com/bytecodealliance/wasm-micro-runtime
- WAMR Documentation: https://wamr.gitbook.io/
