"""Shared CMake configuration for LLVM runtime builds."""

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
