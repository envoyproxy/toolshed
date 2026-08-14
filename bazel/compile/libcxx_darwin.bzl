"""Rules for building the darwin libcxx release artifact."""

def _libcxx_darwin_extract_impl(ctx):
    out_dir = ctx.actions.declare_directory(ctx.label.name)
    srcs = ctx.files.srcs
    install_name_tool = ctx.executable.install_name_tool

    arguments = [out_dir.path, install_name_tool.path] + [src.path for src in srcs]
    ctx.actions.run_shell(
        inputs = srcs,
        tools = [install_name_tool],
        outputs = [out_dir],
        command = """
set -euo pipefail

out_dir="$1"
install_name_tool="$2"
shift 2

mkdir -p "${out_dir}/include" "${out_dir}/lib"

for src in "$@"; do
  case "${src}" in
    */include/c++/v1/__config_site)
      cp "${src}" "${out_dir}/include/__config_site"
      ;;
    */lib/libc++.1.0.dylib|*/lib/libc++.1.dylib|*/lib/libc++.dylib|*/lib/libc++abi.1.0.dylib|*/lib/libc++abi.1.dylib|*/lib/libc++abi.dylib)
      cp -a "${src}" "${out_dir}/lib/"
      ;;
  esac
done

"${install_name_tool}" -id /usr/lib/libc++.1.dylib "${out_dir}/lib/libc++.1.dylib"
"${install_name_tool}" -id /usr/lib/libc++abi.dylib "${out_dir}/lib/libc++abi.1.dylib"
""",
        arguments = arguments,
        mnemonic = "DarwinLibcxxExtract",
        progress_message = "Extracting darwin libcxx from LLVM release",
    )

    return [DefaultInfo(files = depset([out_dir]))]

libcxx_darwin_extract = rule(
    implementation = _libcxx_darwin_extract_impl,
    attrs = {
        "srcs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "Darwin libcxx inputs from @llvm_tarball_macos_arm64.",
        ),
        "install_name_tool": attr.label(
            executable = True,
            cfg = "exec",
            allow_files = True,
            mandatory = True,
            doc = "llvm-install-name-tool executable.",
        ),
    },
    doc = "Extracts and patches darwin libcxx files from an LLVM macOS tarball.",
)
