load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")

sh_test(
    name = "test_autotools",
    srcs = ["test_autotools.sh"],
    data = ["@autotools_x86_64//:all"],
)

genrule(
    name = "prepare_autotools_files",
    outs = [
        "configure.ac",
        "Makefile.am",
        "src/Makefile.am",
        "src/hello.c",
        "src/hello.h",
        "src/main.c",
    ],
    cmd = """
mkdir -p src m4 build-aux
cat > $(@D)/configure.ac <<'EOF'
AC_INIT([libhello], [1.0], [test@example.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign])
AC_PROG_CC
# AC_CONFIG_HEADERS([src/hello.h])
LT_INIT
AC_CONFIG_FILES([
 Makefile
 src/Makefile
])
AC_OUTPUT
EOF

cat > $(@D)/Makefile.am <<'EOF'
ACLOCAL_AMFLAGS = -I m4
SUBDIRS = src
EOF

cat > $(@D)/src/Makefile.am <<'EOF'
lib_LTLIBRARIES = libhello.la
libhello_la_SOURCES = hello.c
libhello_la_LDFLAGS = -version-info 1:0:0

bin_PROGRAMS = hello_test
hello_test_SOURCES = main.c
hello_test_LDADD = libhello.la

include_HEADERS = hello.h
EOF

cat > $(@D)/src/hello.c <<'EOF'
#include <stdio.h>
#include "hello.h"

void hello_world(const char *name) {
    printf("Hello, %s from autotools!\\n", name);
}

int get_version(void) {
    return 42;
}
EOF

cat > $(@D)/src/hello.h <<'EOF'
#ifndef HELLO_H
#define HELLO_H

void hello_world(const char *name);
int get_version(void);

#endif
EOF

cat > $(@D)/src/main.c <<'EOF'
#include <stdio.h>
#include "hello.h"

int main(int argc, char *argv[]) {
    hello_world(argc > 1 ? argv[1] : "World");
    printf("Library version: %d\\n", get_version());
    return 0;
}
EOF
""",
)


filegroup(
    name = "hellolib",
    srcs = [
        "configure.ac",
        "Makefile.am",
        "src/Makefile.am",
        "src/hello.c",
        "src/hello.h",
        "src/main.c",
    ],
)

# Build the autotools project using the toolchain
configure_make(
    name = "build_libhello",
    lib_source = "hellolib",
    configure_in_place = True,
    configure_prefix = """
    find .

    # Skip common ancestor logic for now, just copy files
    for f in $(locations :hellolib); do
      if [[ -f "$$EXT_BUILD_ROOT/$$f" ]]; then
        mkdir -p "$$(dirname "$$f")"
        cp $$EXT_BUILD_ROOT/$$f ./
      fi
    done

    # Parse autotools base directory from locations

    for f in $(locations @autotools_x86_64//:all); do
        if echo "$$f" | grep -q "/bin/autoreconf$$"; then
            AUTOTOOLS_DIR=$$EXT_BUILD_ROOT/$$(dirname $$(dirname $$f))
            break
        fi
    done

    # Also need perl
    for f in $(locations @perl_linux_amd64//:runtime); do
        if echo "$$f" | grep -q "/bin/perl$$"; then
            PERL_DIR=$$EXT_BUILD_ROOT/$$(dirname $$(dirname $$f))
            break
        fi
    done


    # Set up PATH
    export PATH="$$AUTOTOOLS_DIR/bin:$$PERL_DIR/bin:$$PATH"

    # Tool binaries
    export M4="$$AUTOTOOLS_DIR/bin/m4 "
    export AUTOCONF="$$AUTOTOOLS_DIR/bin/autoconf "
    export AUTOHEADER="$$AUTOTOOLS_DIR/bin/autoheader "
    export AUTORECONF="$$AUTOTOOLS_DIR/bin/autoreconf "
    export AUTOMAKE="$$AUTOTOOLS_DIR/bin/automake "
    export ACLOCAL="$$AUTOTOOLS_DIR/bin/aclocal "
    export LIBTOOLIZE="$$AUTOTOOLS_DIR/bin/libtoolize "
    export LIBTOOL="$$AUTOTOOLS_DIR/bin/libtool "
    # dumb perl shit needs a space after path
    export AUTOM4TE="$$AUTOTOOLS_DIR/bin/autom4te "
    export PERL="$$PERL_DIR/bin/perl"

    # Autoconf paths
    export autom4te_perllibdir="$$AUTOTOOLS_DIR/share/autoconf"
    export AC_MACRODIR="$$AUTOTOOLS_DIR/share/autoconf"
    export AUTOM4TE_CFG="$$AUTOTOOLS_DIR/share/autoconf/autom4te.cfg"
    export trailer_m4="$$AUTOTOOLS_DIR/share/autoconf/autoconf/trailer.m4"
    export autom4te_buildauxdir="$$AUTOTOOLS_DIR/share/autoconf/build-aux"

    # Automake paths
    export automake_incdir="$$AUTOTOOLS_DIR/share/automake-1.16"
    export AUTOMAKE_LIBDIR="$$AUTOTOOLS_DIR/share/automake-1.16"
    export ACLOCAL_PATH="$$AUTOTOOLS_DIR/share/aclocal-1.16:$$AUTOTOOLS_DIR/share/aclocal"

    export AUTOMAKE_SHARE="$$AUTOTOOLS_DIR/share/automake-1.16"
    export ACLOCAL_AUTOMAKE_DIR="$$AUTOTOOLS_DIR/share/aclocal-1.16"

    # Libtool paths
    export pkgauxdir="$$AUTOTOOLS_DIR/share/libtool/build-aux"
    export pkgdatadir="$$AUTOTOOLS_DIR/share/libtool"


    # Create m4 directory
    mkdir -p m4 build-aux

    pwd
    ls -l .
    cat Makefile.am
    cat configure.ac


    # Fix autom4te.cfg paths
    sed -i "s|--prepend-include '[^']*share/autoconf'|--prepend-include '$${AUTOTOOLS_DIR}/share/autoconf'|g" \
        "$$AUTOM4TE_CFG"

    cat "$$AUTOM4TE_CFG"

    # Debug aclocal
    echo "=== Adding debug to aclocal ==="
    cp $$ACLOCAL aclocal.debug
    sed -i '/^my @automake_includes = /a\\print STDERR "DEBUG: Initial automake_includes = @automake_includes\\n";' aclocal.debug
    sed -i '/@automake_includes = (\\$$ENV{"ACLOCAL_AUTOMAKE_DIR"})/a\\print STDERR "DEBUG: automake_includes after env override = @automake_includes\\n";' aclocal.debug
    sed -i '/if (! opendir (DIR, \\$$m4dir))/i\\      print STDERR "DEBUG: Trying to open directory: \\$$m4dir\\n";' aclocal.debug
    sed -i '/my \\$$fullfile = File::Spec->canonpath/a\\      print STDERR "DEBUG: Examining file: \\$$fullfile\\n";' aclocal.debug
    sed -i '/verb "found macro \\$macro in \\$file"/a\\      print STDERR "DEBUG: Found macro \\$macro in \\$file\\n";' aclocal.debug

    echo "Running debug aclocal"
    ./aclocal.debug -I m4 --verbose || {
        echo "aclocal.debug failed"
        exit 1
    }

    # autom4te --language=autoconf --trace=AC_CONFIG_FILES configure.ac
    cat src/Makefile.am
    # cat src/configure.ac

    # $$AUTOM4TE --language=autoconf --trace=AM_INIT_AUTOMAKE configure.ac


    AUTOMAKE="automake --add-missing --copy --force-missing --verbose --warnings=all,no-error" \
        autoreconf -fiv


    # Continue with autoreconf
    $$AUTORECONF -fivm || {
        exit 1
    }

    """,
    out_binaries = ["hello_test"],
    out_shared_libs = ["libhello.so"],
    out_static_libs = ["libhello.a"],
    build_data = [
        "@autotools_x86_64//:all",
        "@perl_linux_amd64//:runtime",
        ":hellolib",
    ],
    visibility = ["//visibility:public"],
)

# Test that the built binary works
sh_test(
    name = "test_built_binary",
    srcs = ["test_built_binary.sh"],
    data = [":build_libhello"],
)
