"""Custom rule mirroring v8_lib_no_pointer_compression's shape.

Carries a dependency in a non-standard `library` attribute to verify that
the reachability aspect traverses and records edges on attributes outside the
former fixed _EDGE_ATTRS list.
"""

def _custom_library_rule_impl(ctx):
    return [DefaultInfo()]

custom_library_rule = rule(
    implementation = _custom_library_rule_impl,
    attrs = {
        "library": attr.label(
            allow_files = True,
            doc = "A dependency carried on a non-standard attribute name.",
        ),
        "_private": attr.label(
            default = Label("@bazel_skylib//:bzl_library.bzl"),
            allow_files = True,
            doc = "An implicit/private attribute — must not contribute edges.",
        ),
    },
)
