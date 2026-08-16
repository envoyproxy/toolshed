load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:versions.bzl", "VERSIONS")

def load_github_archives():
    for k, v in VERSIONS.items():
        if type(v) == type("") or v.get("type") != "github_archive":
            continue
        kwargs = dict(name = k, **v)

        # Format string values, but not lists
        formatted_kwargs = {}
        for arg_k, arg_v in kwargs.items():
            if arg_k in ["arch", "download_suffix", "repo", "type", "version"]:
                continue
            if type(arg_v) == type(""):
                formatted_kwargs[arg_k] = arg_v.format(**kwargs)
            else:
                formatted_kwargs[arg_k] = arg_v
        http_archive(**formatted_kwargs)

def load_http_archives():
    for k, v in VERSIONS.items():
        if type(v) == type("") or v.get("type") != "http_archive":
            continue
        if k in ["llvm_libcxx_aarch64", "llvm_libcxx_x86_64"]:
            # These repos must remain opaque tarball blobs in WORKSPACE mode.
            # setup_llvm_prebuilt() is the source of truth for creating them.
            continue
        kwargs = dict(name = k, **v)

        # Format string values, but not lists
        formatted_kwargs = {}
        for arg_k, arg_v in kwargs.items():
            if arg_k in ["arch", "bins_release", "download_suffix", "repo", "type", "version"]:
                continue
            if type(arg_v) == type(""):
                formatted_kwargs[arg_k] = arg_v.format(**kwargs)
            else:
                formatted_kwargs[arg_k] = arg_v
        http_archive(**formatted_kwargs)

def load_archives():
    load_github_archives()
    load_http_archives()
