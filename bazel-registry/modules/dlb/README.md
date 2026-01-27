# Intel DLB (Dynamic Load Balancer) Bazel Module

This module provides the Intel DLB user-space library (`libdlb`) as a Bazel `cc_library` target.

## Overview

Intel DLB is a hardware accelerator for efficient, load-balanced, event-driven processing. This module packages the user-space library for use in Bazel-based projects.

## Usage

### Adding the Dependency

In your `MODULE.bazel` file:

```starlark
bazel_dep(name = "dlb", version = "8.8.0.envoy")
```

### Using in BUILD Files

```starlark
cc_binary(
    name = "my_app",
    srcs = ["my_app.c"],
    deps = ["@dlb//:dlb"],
)
```

The library includes:
- All DLB API headers (including `dlb.h`, `dlb2_user.h`)
- The static library `libdlb.a`
- Proper compiler flags and pthread linking

## Build Configuration

The library is built with:
- `-DDLB_DISABLE_DOMAIN_SERVER`: Disables the domain server feature
- `-D_GNU_SOURCE`: Enables GNU extensions
- `-std=c99`: C99 standard
- `-lpthread`: Links pthread library

## Platform Support

This module targets **Linux x86_64** systems only, as DLB is Intel-specific hardware.

## Source

- Version: 8.8.0
- Source: https://downloadmirror.intel.com/819078/dlb_linux_src_release_8.8.0.txz
- SHA256: 564534254ef32bfed56e0a464c53fca0907e446b30929c253210e2c3d6de58b9

## Implementation Notes

This module uses Bazel's native `rules_cc` to build the library, replacing the original Makefile-based build system. The key differences from the upstream source:

1. **Header Handling**: The `dlb2_user.h` header is automatically copied from `driver/dlb2/uapi/linux/` to `libdlb/` directory using a genrule, replicating what Envoy does with patch commands.

2. **No Make**: The module uses pure Bazel `cc_library` rules instead of `rules_foreign_cc` and Make.

3. **Static Library**: Produces a static library suitable for linking into C/C++ applications.

## Example Code

```c
#include <dlb.h>
#include <stdio.h>

int main() {
    dlb_hdl_t dlb;
    dlb_dev_cap_t cap;
    
    // Open DLB device 0
    if (dlb_open(0, &dlb) == -1) {
        perror("dlb_open");
        return 1;
    }
    
    // Get device capabilities
    if (dlb_get_dev_capabilities(dlb, &cap) == -1) {
        perror("dlb_get_dev_capabilities");
        dlb_close(dlb);
        return 1;
    }
    
    printf("DLB capabilities: domains=%d\n", cap.num_sched_domains);
    
    dlb_close(dlb);
    return 0;
}
```

## Testing with Local Registry

To test this module with a local Bazel Central Registry clone:

```bash
# In your .bazelrc
common --registry=file:///path/to/toolshed/bazel-registry
common --registry=https://bcr.bazel.build

# Then use normally
bazel build @dlb//:dlb
```

## License

The DLB source code is licensed under Intel's terms. This Bazel module packaging is Apache-2.0 licensed.

## Maintainers

- Envoy Proxy maintainers (@envoyproxy)

## Related

- [Envoy DLB Connection Balancer](https://github.com/envoyproxy/envoy/tree/main/contrib/dlb)
- [Intel DLB Documentation](https://www.intel.com/content/www/us/en/developer/topic-technology/open/overview.html)
