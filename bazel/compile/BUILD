load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake", "configure_make")
load("//:versions.bzl", "VERSIONS")

package(default_visibility = ["//visibility:public"])

SANITIZER_ENV = {
    "CXXFLAGS": "-nostdinc++ -nostdlib++",
    "LDFLAGS": "-nostdlib++",
}

BASE_CMAKE_CACHE = {
    "CMAKE_BUILD_TYPE": "RelWithDebInfo",
    "CMAKE_INSTALL_PREFIX": ".",
    "CMAKE_POSITION_INDEPENDENT_CODE": "ON",
    "LLVM_ENABLE_RUNTIMES": "libcxxabi;libcxx;libunwind",
    "LLVM_USE_LINKER": "lld",
    "CMAKE_SHARED_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_MODULE_LINKER_FLAGS": "-shared -Wl,-S -fuse-ld=lld",
    "CMAKE_EXE_LINKER_FLAGS": "-Wl,-S -fuse-ld=lld",
    "BUILD_SHARED_LIBS": "OFF",
    "LIBCXX_ENABLE_SHARED": "OFF",
    "LIBCXX_ENABLE_STATIC": "ON",
    "LIBCXXABI_ENABLE_SHARED": "OFF",
    "LIBCXXABI_ENABLE_STATIC": "ON",
    "LIBUNWIND_ENABLE_SHARED": "OFF",
    "LIBUNWIND_ENABLE_STATIC": "ON",
}

cmake(
    name = "libcxx_msan",
    cache_entries = BASE_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "MemoryWithOrigins",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    tags = ["manual"],
    working_directory = "runtimes",
)

cmake(
    name = "libcxx_tsan",
    cache_entries = BASE_CMAKE_CACHE | {
        "LLVM_USE_SANITIZER": "Thread",
    },
    env = SANITIZER_ENV,
    lib_source = "@llvm_source//:all",
    out_static_libs = [
        "libc++.a",
        "libc++abi.a",
    ],
    tags = ["manual"],
    working_directory = "runtimes",
)

genrule(
    name = "cxx_msan",
    srcs = [":libcxx_msan"],
    outs = ["msan-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"]],
    cmd = """
        mkdir -p msan-libs-x86_64/lib
        for f in $(locations :libcxx_msan); do
            if [[ $$f == *.a ]]; then
                cp $$f msan-libs-x86_64/lib/
            fi
        done
        tar cJf $@ msan-libs-x86_64
    """,
    tags = ["manual"],
)

genrule(
    name = "cxx_tsan",
    srcs = [":libcxx_tsan"],
    outs = ["tsan-llvm%s-x86_64.tar.xz" % VERSIONS["llvm"]],
    cmd = """
        mkdir -p tsan-libs-x86_64/lib
        for f in $(locations :libcxx_tsan); do
            if [[ $$f == *.a ]]; then
                cp $$f tsan-libs-x86_64/lib/
            fi
        done
        tar cJf $@ tsan-libs-x86_64
    """,
    tags = ["manual"],
)

configure_make(
    name = "libtool_build",
    configure_options = [
        "--disable-dependency-tracking",
        "--disable-ltdl-install",
    ],
    env = {
        "M4": "$$EXT_BUILD_DEPS/m4_build/bin/m4",
    },
    deps = [":m4_build"],
    lib_source = "@libtool_source//:all",
    out_binaries = [
        "libtool",
        "libtoolize",
    ],
    out_data_dirs = [
        "share/aclocal",
        "share/libtool",
    ],
    postfix_script = """
    # Patch libtoolize to be relocatable
    # The script determines its location and finds data relative to it
    sed -i 's|^  prefix=.*|  prefix="\\$(cd "\\$(dirname "\\$0")/.." \\&\\& pwd)"|' $INSTALLDIR/bin/libtoolize
    sed -i 's|^  datadir=.*|  datadir="\\${prefix}/share"|' $INSTALLDIR/bin/libtoolize
    sed -i 's|^  pkgauxdir=.*|  pkgauxdir="\\${datadir}/libtool/build-aux"|' $INSTALLDIR/bin/libtoolize
    sed -i 's|^  pkgltdldir=.*|  pkgltdldir="\\${datadir}/libtool"|' $INSTALLDIR/bin/libtoolize
    sed -i 's|^  aclocaldir=.*|  aclocaldir="\\${datadir}/aclocal"|' $INSTALLDIR/bin/libtoolize
    """,
    tags = ["manual"],
)

configure_make(
    name = "m4_build",
    lib_source = "@m4_source//:all",
    out_binaries = ["m4"],
    tags = ["manual"],
    configure_in_place = True,
    configure_options = [
        "--disable-dependency-tracking",
        "--disable-nls",
        "--without-libsigsegv",
        "--with-included-regex=yes",
    ],
    # Skip doc directory during build
    env = {
        "SUBDIRS": "lib src",
    },
)

configure_make(
    name = "autoconf_build",
    configure_options = [
        "--disable-dependency-tracking",
    ],
    env = {
        "M4": "$$EXT_BUILD_DEPS/m4_build/bin/m4",
    },
    lib_source = "@autoconf_source//:all",
    out_binaries = [
        "autoconf",
        "autoheader",
        "autom4te",
        "autoreconf",
        "autoscan",
        "autoupdate",
        "ifnames",
    ],
    out_data_dirs = ["share/autoconf"],
    tags = ["manual"],
    deps = [":m4_build"],
)

configure_make(
    name = "automake_build",
    configure_options = [
        "--disable-dependency-tracking",
    ],
    env = {
        "AUTOCONF": "$$EXT_BUILD_DEPS/autoconf_build/bin/autoconf",
        "AUTOM4TE": "$$EXT_BUILD_DEPS/autoconf_build/bin/autom4te",
        "M4": "$$EXT_BUILD_DEPS/m4_build/bin/m4",
        "PATH": "$$EXT_BUILD_DEPS/autoconf_build/bin:$$EXT_BUILD_DEPS/m4_build/bin:$$PATH",
    },
    lib_source = "@automake_source//:all",
    out_binaries = [
        "automake",
        "aclocal",
    ],
    out_data_dirs = [
        "share/aclocal-1.17",
        "share/automake-1.17",
    ],
    tags = ["manual"],
    deps = [
        ":autoconf_build",
        ":m4_build",
    ],
)

# Package autotools components
genrule(
    name = "libtool",
    srcs = [":libtool_build"],
    outs = ["libtool-%s.tar.xz" % VERSIONS["libtool"]],
    cmd = """
    ARCH=$$(uname -m)
    mkdir -p libtool-$$ARCH/bin libtool-$$ARCH/share
    for f in $(locations :libtool_build); do
        if [[ $$f == */bin/libtool* ]]; then
            cp $$f libtool-$$ARCH/bin/
        elif [[ -d $$f ]] && [[ $$f == */share/* ]]; then
            dirname=$$(basename $$f)
            cp -rL $$f libtool-$$ARCH/share/$$dirname
        fi
    done
    tar cJf $@ libtool-$$ARCH
    """,
    tags = ["manual"],
)

genrule(
    name = "m4",
    srcs = [":m4_build"],
    outs = ["m4-%s.tar.xz" % VERSIONS["m4"]],
    cmd = """
    ARCH=$$(uname -m)
    mkdir -p m4-$$ARCH/bin
    for f in $(locations :m4_build); do
        if [[ $$f == */bin/m4 ]]; then
            cp $$f m4-$$ARCH/bin/
        fi
    done
    tar cJf $@ m4-$$ARCH
    """,
    tags = ["manual"],
)

genrule(
    name = "autoconf",
    srcs = [":autoconf_build"],
    outs = ["autoconf-%s.tar.xz" % VERSIONS["autoconf"]],
    cmd = """
    ARCH=$$(uname -m)
    mkdir -p autoconf-$$ARCH/bin autoconf-$$ARCH/share
    for f in $(locations :autoconf_build); do
        if [[ $$f == */bin/* ]]; then
            cp $$f autoconf-$$ARCH/bin/
        elif [[ -d $$f ]] && [[ $$f == */share/* ]]; then
            dirname=$$(basename $$f)
            cp -rL $$f autoconf-$$ARCH/share/$$dirname
        fi
    done
    tar cJf $@ autoconf-$$ARCH
    """,
    tags = ["manual"],
)

genrule(
    name = "automake",
    srcs = [":automake_build"],
    outs = ["automake-%s.tar.xz" % VERSIONS["automake"]],
    cmd = """
    ARCH=$$(uname -m)
    mkdir -p automake-$$ARCH/bin automake-$$ARCH/share
    for f in $(locations :automake_build); do
        if [[ $$f == */bin/* ]]; then
            cp $$f automake-$$ARCH/bin/
        elif [[ -d $$f ]] && [[ $$f == */share/* ]]; then
            dirname=$$(basename $$f)
            cp -rL $$f automake-$$ARCH/share/$$dirname
        fi
    done
    tar cJf $@ automake-$$ARCH
    """,
    tags = ["manual"],
)

# Combined autotools package
genrule(
    name = "autotools",
    srcs = [
        ":m4_build",
        ":autoconf_build",
        ":automake_build",
        ":libtool_build",
    ],
    outs = ["autotools-%s-%s-%s-%s.tar.xz" % (VERSIONS["m4"], VERSIONS["autoconf"], VERSIONS["automake"], VERSIONS["libtool"])],
    cmd = """
    ARCH=$$(uname -m)
    mkdir -p autotools-$$ARCH/bin autotools-$$ARCH/share

    # Copy all binaries
    for f in $(locations :m4_build) $(locations :autoconf_build) $(locations :automake_build) $(locations :libtool_build); do
        if [[ $$f == */bin/* ]] && [[ -f $$f ]]; then
            cp $$f autotools-$$ARCH/bin/
        elif [[ -d $$f ]] && [[ $$f == */share/* ]]; then
            dirname=$$(basename $$f)
            cp -rL $$f autotools-$$ARCH/share/$$dirname
        fi
    done

    tar cJf $@ autotools-$$ARCH
    """,
    tags = ["manual"],
)
