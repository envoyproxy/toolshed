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

def _wasmtime_crates_impl(mctx):
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
    return mctx.extension_metadata(
        root_module_direct_deps = ["cu"],
        root_module_direct_dev_deps = [],
    )

wasmtime_crates = module_extension(
    implementation = _wasmtime_crates_impl,
)
