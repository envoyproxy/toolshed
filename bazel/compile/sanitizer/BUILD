load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")

package(default_visibility = ["//visibility:public"])

LLVM_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++ -nostdlib++",
    "LDFLAGS": "-nostdlib++",
}

GCC_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++",
    "LDFLAGS": "",
}

MACOS_SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++",
    "LDFLAGS": "",
}

SANITIZER_ENV = select({
    "//compile:gcc_build": GCC_SANITIZER_ENV,
    "//compile:macos_build": MACOS_SANITIZER_ENV,
    "//conditions:default": LLVM_SANITIZER_ENV,
})

LLVM_LINKER_FLAGS = {
    "LLVM_USE_LINKER": "lld",
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S -fuse-ld=lld",
}

GCC_LINKER_FLAGS = {
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
}

MACOS_LINKER_FLAGS = {
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S",
}

BASE_CMAKE_CACHE_COMMON = {
    "CMAKE_BUILD_TYPE": "RelWithDebInfo",
    "CMAKE_INSTALL_PREFIX": ".",
    "CMAKE_POSITION_INDEPENDENT_CODE": "ON",
    "LLVM_ENABLE_RUNTIMES": "libcxxabi;libcxx;libunwind",
    "BUILD_SHARED_LIBS": "OFF",
    "LIBCXX_ENABLE_SHARED": "OFF",
    "LIBCXX_ENABLE_STATIC": "ON",
    "LIBCXXABI_ENABLE_SHARED": "OFF",
    "LIBCXXABI_ENABLE_STATIC": "ON",
    "LIBUNWIND_ENABLE_SHARED": "OFF",
    "LIBUNWIND_ENABLE_STATIC": "ON",
}

BASE_CMAKE_CACHE = BASE_CMAKE_CACHE_COMMON | select({
    "//compile:gcc_build": GCC_LINKER_FLAGS,
    "//compile:macos_build": MACOS_LINKER_FLAGS,
    "//conditions:default": LLVM_LINKER_FLAGS,
})

PYTHON_CMAKE_CACHE = {
    "Python3_EXECUTABLE": "$$EXT_BUILD_ROOT/$(PYTHON3)",
}

cmake(
    name = "libcxx_msan",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "MemoryWithOrigins",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

cmake(
    name = "libcxx_tsan",
    cache_entries = BASE_CMAKE_CACHE | PYTHON_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "Thread",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
    toolchains = ["@rules_python//python:current_py_toolchain"],
    working_directory = "runtimes",
)

filegroup(
    name = "libcxx_msan_headers",
    srcs = [":libcxx_msan"],
    output_group = "include",
)

pkg_files(
    name = "msan_libs_files",
    srcs = [":libcxx_msan"],
    excludes = [":libcxx_msan_headers"],
    prefix = "msan-libs-x86_64/lib",
    strip_prefix = ".",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)

filegroup(
    name = "libcxx_tsan_headers",
    srcs = [":libcxx_tsan"],
    output_group = "include",
)

pkg_files(
    name = "tsan_libs_files",
    srcs = [":libcxx_tsan"],
    excludes = [":libcxx_tsan_headers"],
    prefix = "tsan-libs-x86_64/lib",
    strip_prefix = ".",
    target_compatible_with = select({
        "//compile:gcc_build": ["@platforms//:incompatible"],
        "//compile:macos_build": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)
