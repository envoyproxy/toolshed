# Example Usage

This directory contains example code showing how to use the WAMR bzlmod module.

## Basic Example

```c
#include "wasm_export.h"
#include <stdio.h>
#include <string.h>

int main() {
    // Initialize WAMR runtime
    if (!wasm_runtime_init()) {
        printf("Failed to initialize WAMR runtime\n");
        return 1;
    }
    
    printf("WAMR runtime initialized successfully\n");
    
    // Your WASM loading and execution code here...
    
    // Cleanup
    wasm_runtime_destroy();
    
    return 0;
}
```

## BUILD.bazel

```starlark
cc_binary(
    name = "wasm_runner",
    srcs = ["main.c"],
    deps = ["@wamr//:iwasm"],
)
```

## MODULE.bazel

```starlark
module(name = "my_wasm_app", version = "1.0.0")

bazel_dep(name = "wamr", version = "2.4.4.envoy")
```

## Build and Run

```bash
# Default build (production settings)
bazel build //:wasm_runner

# Development build with debugging
bazel build //:wasm_runner \
  --@wamr//bazel:dump_call_stack=true \
  --@wamr//bazel:custom_name_section=true

# Build with SIMD support
bazel build //:wasm_runner --@wamr//bazel:simd=true
```

## Integration with proxy-wasm-cpp-host

Once this module is in the BCR, proxy-wasm-cpp-host can use it:

```starlark
# In proxy-wasm-cpp-host MODULE.bazel
bazel_dep(name = "wamr", version = "2.4.4.envoy")

# In BUILD file
cc_library(
    name = "wamr",
    deps = ["@wamr//:iwasm"],
    # ... rest of the configuration
)
```

This replaces the current complex cmake-based foreign_cc approach with a simple bzlmod dependency.
