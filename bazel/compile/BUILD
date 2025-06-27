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
    toolchains = [
        "@rules_perl//:current_toolchain",
    ],
    configure_options = [
        "--disable-dependency-tracking",
        "--disable-ltdl-install",
    ],
    env = {
        "M4": "$$EXT_BUILD_DEPS/m4_build/bin/m4",
        "PERL": "$(PERL)",
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

    # Strip build-time compiler paths from libtool
    sed -i 's|^AR=.*|AR="\\${AR:-ar}"|' $INSTALLDIR/bin/libtool
    sed -i 's|^CC=.*|CC="\\${CC:-cc}"|' $INSTALLDIR/bin/libtool
    sed -i 's|^LD=.*|LD="\\${LD:-ld}"|' $INSTALLDIR/bin/libtool
    sed -i 's|^LTCC=.*|LTCC="\\${CC:-cc}"|' $INSTALLDIR/bin/libtool
    sed -i 's|^LTCFLAGS=.*|LTCFLAGS="\\${CFLAGS}"|' $INSTALLDIR/bin/libtool
    # These need to be determined at runtime based on the actual compiler
    sed -i '/^compiler_lib_search_dirs=/s|=.*|="\\${LIBTOOL_COMPILER_LIB_SEARCH_DIRS}"|' $INSTALLDIR/bin/libtool
    sed -i '/^compiler_lib_search_path=/s|=.*|="\\${LIBTOOL_COMPILER_LIB_SEARCH_PATH}"|' $INSTALLDIR/bin/libtool
    sed -i '/^predep_objects=/s|=.*|="\\${LIBTOOL_PREDEP_OBJECTS}"|' $INSTALLDIR/bin/libtool
    sed -i '/^postdep_objects=/s|=.*|="\\${LIBTOOL_POSTDEP_OBJECTS}"|' $INSTALLDIR/bin/libtool
    sed -i '/^sys_lib_search_path_spec=/s|=.*|="\\${LIBTOOL_SYS_LIB_SEARCH_PATH_SPEC:-/usr/lib /lib}"|' $INSTALLDIR/bin/libtool
    """,
    tags = ["manual"],
)

configure_make(
    name = "m4_build",
    lib_source = "@m4_source//:all",
    out_binaries = ["m4"],
    tags = ["manual"],
    toolchains = [],
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
    configure_in_place = True,
    toolchains = [
        "@rules_perl//:current_toolchain",
    ],
    configure_prefix = "export PATH=\"$${EXT_BUILD_ROOT}/external/perl_linux_amd64/bin:$$PATH\" && ",
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
    postfix_script = """
    for f in $INSTALLDIR/bin/*; do
        if [[ -f "$f" ]]; then
            sed -i '1s|^#!.*perl.*$|#!/usr/bin/env perl|' "$f"
            sed -i '0,/^eval .*/{s|exec .*perl|exec /usr/bin/env perl|}' "$f"
    # sed -i '/^eval '\\''case \\$# in/,/if 0;$/d' "$f"
            sed -i "s#my \\$pkgdatadir = .*#my \\$pkgdatadir = \\$ENV{'autom4te_perllibdir'} || do { my \\$d = \\$0; \\$d =~ s,[^/]*\\$,../share/autoconf,; \\$d };#g" "$f"
            sed -i "s#my \\$autom4te *= *\\$ENV{'AUTOM4TE'} *|| *'[^']*';#my \\$autom4te = \\$ENV{'AUTOM4TE'} or die 'AUTOM4TE not set';#g" "$f"
            sed -i "s#my \\$autoheader *= *\\$ENV{'AUTOHEADER'} *|| *'[^']*';#my \\$autoheader = \\$ENV{'AUTOHEADER'} or die 'AUTOHEADER not set';#g" "$f"
            sed -i "s#my \\$autoconf *= *\\$ENV{'AUTOCONF'} *|| *'[^']*';#my \\$autoconf = \\$ENV{'AUTOCONF'} or die 'AUTOCONF not set';#g" "$f"
            sed -i "s#my \\$trailer_m4 *= *\\$ENV{'trailer_m4'} *|| *'[^']*';#my \\$trailer_m4 = \\$ENV{'trailer_m4'} or die 'trailer_m4 not set';#g" "$f"
            sed -i "s#my \\$m4 *= *\\$ENV{\\"M4\\"} *|| *'[^']*';#my \\$m4 = \\$ENV{\\"M4\\"} or die 'M4 not set';#g" "$f"
            sed -i "s#my @include = ('[^']*');#my \\@include = (\\$ENV{\\"AC_MACRODIR\\"} or die 'AC_MACRODIR not set');#g" "$f"
        fi
    done
    """,
    tags = ["manual"],
    deps = [":m4_build"],
    build_data = select({
        "@platforms//cpu:x86_64": ["@perl_linux_amd64//:runtime"],
        "@platforms//cpu:aarch64": ["@perl_linux_arm64//:runtime"],
    }),
)

configure_make(
    name = "automake_build",
    toolchains = [
        "@rules_perl//:current_toolchain",
    ],
    configure_in_place = True,
    configure_prefix = "export PATH=\"$$EXT_BUILD_ROOT/external/perl_linux_amd64/bin:$$EXT_BUILD_DEPS/autoconf_build/bin:$$PATH\" && export autom4te_perllibdir=\"$$EXT_BUILD_DEPS/autoconf_build/share/autoconf\" && export AC_MACRODIR=\"$$EXT_BUILD_DEPS/autoconf_build/share/autoconf\" && export AUTOM4TE_CFG=\"$$EXT_BUILD_DEPS/autoconf_build/share/autoconf/autom4te.cfg\" && export am_cv_autoconf_works=yes && export am_cv_autoconf_version='2.72' && export am_cv_prog_automake_version='1.17' && export am_cv_automake_acdir='share/automake-1.17/acdir' && ",
    configure_options = [
        "--disable-dependency-tracking",
        "ac_cv_prog_am_AUTOCONF=$$EXT_BUILD_DEPS/autoconf_build/bin/autoconf",
    ],
    env = {
        "AUTOCONF": "$$EXT_BUILD_DEPS/autoconf_build/bin/autoconf",
        "AUTOM4TE": "$$EXT_BUILD_DEPS/autoconf_build/bin/autom4te",
        "M4": "$$EXT_BUILD_DEPS/m4_build/bin/m4",
        "PATH": "$$EXT_BUILD_DEPS/autoconf_build/bin:$$EXT_BUILD_DEPS/m4_build/bin:$$PATH",
        "PERL": "$(PERL)",
        "autom4te_perllibdir": "$$EXT_BUILD_DEPS/autoconf_build/share/autoconf",
        "AC_MACRODIR": "$$EXT_BUILD_DEPS/autoconf_build/share/autoconf",
        "AUTOM4TE_CFG": "$$EXT_BUILD_DEPS/autoconf_build/share/autoconf/autom4te.cfg",
        "autom4te_buildauxdir": "$$EXT_BUILD_DEPS/autoconf_build/share/autoconf/build-aux",
        "trailer_m4": "$$EXT_BUILD_DEPS/autoconf_build/share/autoconf/autoconf/trailer.m4",
    },
    lib_source = "@automake_source//:all",
    out_binaries = [
        "automake",
        "aclocal",
    ],
    out_data_dirs = [
        "share/aclocal-1.16",
        "share/automake-1.16",
    ],
    tags = ["manual"],
    deps = [
        ":autoconf_build",
        ":m4_build",
    ],
    postfix_script = """
    for f in $INSTALLDIR/bin/*; do
        if [[ -f "$f" ]]; then
            # Replace shebang line with /usr/bin/env perl (no hardcoded path)
            sed -i '1s|^#!.*perl.*$|#!/usr/bin/env perl|' "$f"
            sed -i '0,/^eval .*/{s|exec .*perl|exec /usr/bin/env perl|}' "$f"
            sed -i "s#^\\s*unshift (@INC, '.*')#  unshift (\\@INC, (\\$ENV{'automake_incdir'} or die 'automake_incdir not set'))#g" "$f"
            sed -i "s#my @automake_includes = ('[^']*' \\. \\$APIVERSION);#my \\@automake_includes = ((\\$ENV{'ACLOCAL_AUTOMAKE_DIR'} || die 'ACLOCAL_AUTOMAKE_DIR not set'));#g" "$f"
            # Fix reference to ac-config-macro-dirs.m4 - it's in autoconf share, not automake
            sed -i "s#\\$automake_includes\\[0\\]/internal/ac-config-macro-dirs\\.m4#\\$ENV{'AC_MACRODIR'}/internal/ac-config-macro-dirs.m4#g" "$f"
            # sed -i "s#my @automake_includes = ('[^']*' \\. \\$APIVERSION);#my \\@automake_includes = split(':', \\$ENV{'ACLOCAL_PATH'} or die 'ACLOCAL_PATH not set');#g" "$f"
            # sed -i "s#my @automake_includes = ('[^']*' \\. \\$APIVERSION);#my \\@automake_includes = split(':', \\$ENV{'ACLOCAL_PATH'} or die 'ACLOCAL_PATH not set');#g" "$f"
            # Fix reference to ac-config-macro-dirs.m4 - it's in autoconf share, not automake
            # sed -i "s#\\$automake_includes\\[0\\]/internal/ac-config-macro-dirs\\.m4#\\$ENV{'AC_MACRODIR'}/internal/ac-config-macro-dirs.m4#g" "$f"
            sed -i "s#my @system_includes = ('[^']*');#my \\@system_includes = ();#g" "$f"
            sed -i "s#^\\s*my \\$traces =.*#  my \\$traces = (\\$ENV{'AUTOM4TE'} or die 'AUTOM4TE not set') . ' ';#" "$f"
        fi
    done

    # Fix Config.pm
    sed -i "s#our \\$libdir = \\$ENV{\\"AUTOMAKE_LIBDIR\\"} || '[^']*';#our \\$libdir = \\$ENV{\\"AUTOMAKE_LIBDIR\\"} or die 'AUTOMAKE_LIBDIR not set';#" $INSTALLDIR/share/automake-1.17/Automake/Config.pm
    """,
    build_data = select({
        "@platforms//cpu:x86_64": ["@perl_linux_amd64//:runtime"],
        "@platforms//cpu:aarch64": ["@perl_linux_arm64//:runtime"],
    }),
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
    for f in $(locations :m4_build) $(locations :autoconf_build) $(locations :automake_build) $(locations :libtool_build); do
        if [[ $$f == */bin/* ]] && [[ -f $$f ]]; then
            cp $$f autotools-$$ARCH/bin/
        elif [[ -d $$f ]] && [[ $$f == */share/* ]]; then
            dirname=$$(basename $$f)
            cp -rL $$f autotools-$$ARCH/share/$$dirname
        fi
    done
    find autotools-$$ARCH -type l -exec bash -c 'target=$$(readlink -f "{}"); rm "{}" && cp -a "$$target" "{}"' \\;
    if grep -qr --exclude='*.cfg' sandbox autotools-$$ARCH; then
        echo "'sandbox' found in output dir, aborting" >&2
        grep -r --exclude='*.cfg' sandbox autotools-$$ARCH >&2
        exit 1
    fi
    tar cJf $@ autotools-$$ARCH
    """,
    tags = ["manual"],
)
