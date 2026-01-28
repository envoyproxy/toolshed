# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

load("@rules_rust//crate_universe:defs.bzl", "crate", "crates_repository")

def _wasmtime_crates_impl(module_ctx):
    # Use crates_repository to generate Rust dependencies from wasmtime's Cargo files
    crates_repository(
        name = "cu",
        cargo_lockfile = "//:Cargo.lock",
        manifests = ["//:Cargo.toml"],
        annotations = {
            "wasmtime": [crate.annotation(
                crate_features = ["cranelift"],
            )],
        },
    )
    
    # List all the crate repositories that will be generated
    # These match the dependencies in wasmtime's Cargo.lock
    crate_names = [
        "ahash-0.8.11",
        "aho-corasick-1.1.3",
        "anyhow-1.0.86",
        "arbitrary-1.3.2",
        "bitflags-2.6.0",
        "bumpalo-3.16.0",
        "cc-1.1.7",
        "cfg-if-1.0.0",
        "cobs-0.2.3",
        "cranelift-bforest-0.111.0",
        "cranelift-bitset-0.111.0",
        "cranelift-codegen-0.111.0",
        "cranelift-codegen-meta-0.111.0",
        "cranelift-codegen-shared-0.111.0",
        "cranelift-control-0.111.0",
        "cranelift-entity-0.111.0",
        "cranelift-frontend-0.111.0",
        "cranelift-isle-0.111.0",
        "cranelift-native-0.111.0",
        "cranelift-wasm-0.111.0",
        "crc32fast-1.4.2",
        "either-1.13.0",
        "embedded-io-0.4.0",
        "env_logger-0.10.2",
        "equivalent-1.0.1",
        "errno-0.3.9",
        "fallible-iterator-0.3.0",
        "gimli-0.29.0",
        "hashbrown-0.13.2",
        "hashbrown-0.14.5",
        "heck-0.4.1",
        "hermit-abi-0.3.9",
        "humantime-2.1.0",
        "id-arena-2.2.1",
        "indexmap-2.3.0",
        "is-terminal-0.4.12",
        "itertools-0.12.1",
        "itoa-1.0.11",
        "leb128-0.2.5",
        "libc-0.2.155",
        "libm-0.2.8",
        "linux-raw-sys-0.4.14",
        "log-0.4.22",
        "mach2-0.4.2",
        "memchr-2.7.4",
        "memfd-0.6.4",
        "object-0.36.2",
        "once_cell-1.19.0",
        "paste-1.0.15",
        "pin-project-lite-0.2.14",
        "postcard-1.0.8",
        "proc-macro2-1.0.86",
        "psm-0.1.21",
        "quote-1.0.36",
        "regalloc2-0.9.3",
        "regex-1.10.5",
        "regex-automata-0.4.7",
        "regex-syntax-0.8.4",
        "rustc-hash-1.1.0",
        "rustix-0.38.34",
        "ryu-1.0.18",
        "semver-1.0.23",
        "serde-1.0.204",
        "serde_derive-1.0.204",
        "serde_json-1.0.120",
        "slice-group-by-0.3.1",
        "smallvec-1.13.2",
        "sptr-0.3.2",
        "stable_deref_trait-1.2.0",
        "syn-2.0.72",
        "target-lexicon-0.12.16",
        "termcolor-1.4.1",
        "thiserror-1.0.63",
        "thiserror-impl-1.0.63",
        "tracing-0.1.40",
        "tracing-attributes-0.1.27",
        "tracing-core-0.1.32",
        "unicode-ident-1.0.12",
        "unicode-xid-0.2.4",
        "version_check-0.9.5",
        "wasm-encoder-0.215.0",
        "wasmparser-0.215.0",
        "wasmprinter-0.215.0",
        "wasmtime-24.0.0",
        "wasmtime-asm-macros-24.0.0",
        "wasmtime-c-api-macros-24.0.0",
        "wasmtime-component-macro-24.0.0",
        "wasmtime-component-util-24.0.0",
        "wasmtime-cranelift-24.0.0",
        "wasmtime-environ-24.0.0",
        "wasmtime-jit-icache-coherence-24.0.0",
        "wasmtime-slab-24.0.0",
        "wasmtime-types-24.0.0",
        "wasmtime-versioned-export-macros-24.0.0",
        "wasmtime-wit-bindgen-24.0.0",
        "winapi-util-0.1.8",
        "windows-sys-0.52.0",
        "windows-targets-0.52.6",
        "windows_aarch64_gnullvm-0.52.6",
        "windows_aarch64_msvc-0.52.6",
        "windows_i686_gnu-0.52.6",
        "windows_i686_gnullvm-0.52.6",
        "windows_i686_msvc-0.52.6",
        "windows_x86_64_gnu-0.52.6",
        "windows_x86_64_gnullvm-0.52.6",
        "windows_x86_64_msvc-0.52.6",
        "wit-parser-0.215.0",
        "zerocopy-0.7.35",
        "zerocopy-derive-0.7.35",
    ]
    
    return module_ctx.extension_metadata(
        root_module_direct_deps = ["cu"] + ["cu__" + name for name in crate_names],
        root_module_direct_dev_deps = [],
    )

wasmtime_crates = module_extension(
    implementation = _wasmtime_crates_impl,
)
