# Bazel Registry Audit

- Audit date: 2026-08-04
- Envoy main commit: [`16dd0f1efde1933677335f4785555d6d3736fbfc`](https://github.com/envoyproxy/envoy/commit/16dd0f1efde1933677335f4785555d6d3736fbfc)
- Registry path audited: `/home/runner/work/toolshed/toolshed/bazel-registry/modules/`

## Summary

| Module | Registry Version | Envoy Version | Status | Notes |
|---|---|---|---|---|
| `aspect_bazel_lib` | `2.21.2.envoy` | `2.21.2` | `up-to-date` | Exact version match; registry suffix only. |
| `aws-c-auth-testdata` | `0.9.5.envoy` | `0.10.4` | `needs-update` | Registry trails Envoy semver pin. |
| `aws-lc-fips` | `1.66.2.envoy` | `unknown` | `unknown-mapping` | No aws-lc-fips pin found in fetched Envoy files; registry module likely for future/alternate FIPS flow. |
| `bazel-compdb` | `0.0.0-20220906-4086479.envoy` | `40864791135333e1446a04553b63cbe744d358d0` | `unknown-mapping` | Same upstream project, but Envoy uses full git SHA while registry encodes pseudo-version. |
| `boost.headers` | `1.89.0.envoy` | `1.89.0` | `up-to-date` | Exact version match. |
| `boringssl-fips` | `0.20250107.0.envoy` | `0.20260413.0` | `needs-update` | Envoy boringssl_fips reuses `boringssl` location_name; registry lags Envoy BoringSSL snapshot. |
| `cel-cpp` | `0.14.0.envoy` | `0.14.0` | `up-to-date` | Exact version match. |
| `colm` | `0.14.7-211228-2d8ba76.envoy` | `2d8ba76ddaf6634f285d0a81ee42d5ee77d084cf` | `unknown-mapping` | Registry pseudo-version appears derived from same SHA; manual confirmation needed. |
| `cpp2sky` | `0.6.0.envoy` | `0.6.0` | `up-to-date` | Exact version match. |
| `dd-trace-cpp` | `2.0.0.envoy` | `2.1.1` | `needs-update` | Envoy is newer than registry. |
| `dragonbox` | `0.0.0-241028-6c7c925.envoy` | `6c7c925b571d54486b9ffae8d9d18a822801cbda` | `unknown-mapping` | Registry pseudo-version likely derived from Envoy SHA. |
| `emsdk` | `4.0.23.envoy` | `4.0.6` | `registry-ahead` | Registry is ahead of Envoy; switchover may need compatibility check. |
| `flatbuffers` | `25.12.19.envoy` | `25.12.19` | `up-to-date` | Exact version match. |
| `fp16` | `0.0.0-210320-0a92994.envoy` | `3d2de1816307bac63c16a297e8c4dc501b4076df` | `unknown-mapping` | Registry pseudo-version and Envoy SHA need manual lineage check. |
| `go-fips` | `1.24.12.envoy` | `unknown` | `unknown-mapping` | Only observed as transitive dep of registry boringssl-fips module, not in fetched Envoy main files. |
| `googleurl` | `0.0.0-221103-dd4080f.envoy` | `dd4080fec0b443296c0ed0036e1e776df8813aa7` | `unknown-mapping` | Registry pseudo-version likely tracks same SHA; manual confirmation needed. |
| `grpc` | `1.76.0.bcr.1.envoy` | `1.83.0` | `needs-update` | Large gap from Envoy gRPC pin. |
| `grpc-httpjson-transcoding` | `0.0.0-20250507-a6e226f.envoy` | `a6e226f9a2e656a973df3ad48f0ee5efacce1a28` | `unknown-mapping` | Registry pseudo-version appears derived from Envoy commit SHA. |
| `hessian2-codec` | `0.0.0-250114-6f5a647.envoy` | `6f5a64770f0374a761eece13c8863b80dc5adcd8` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit. |
| `hyperscan` | `5.4.2.envoy` | `5.4.2` | `up-to-date` | Exact version match. |
| `icu` | `78.2.envoy` | `78.2` | `up-to-date` | Exact version match. |
| `ipp-crypto` | `1.3.0.envoy` | `2.2.0` | `needs-update` | Registry significantly behind Envoy. |
| `kafka_message` | `3.9.1.envoy` | `3.9.2` | `needs-update` | Minor update needed. |
| `libcircllhist` | `0.3.2.envoy` | `0.3.2` | `up-to-date` | Exact version match. |
| `libevent` | `2.1.12-stable.bcr.0.200728-62c152d.envoy` | `release-2.2.2-alpha` | `needs-update` | Registry is on older libevent stream; Envoy moved to 2.2.2-alpha. |
| `libmaxminddb` | `1.12.2.envoy` | `1.13.3` | `needs-update` | Registry behind Envoy. |
| `libprotobuf-mutator` | `1.5.envoy` | `1.5` | `up-to-date` | Exact version match. |
| `librdkafka` | `2.6.0.envoy` | `2.6.0` | `up-to-date` | Exact version match. |
| `libsxg` | `0.0.0-210708-beaa393.envoy` | `beaa3939b76f8644f6833267e9f2462760838f18` | `unknown-mapping` | Registry pseudo-version likely same commit lineage. |
| `liburing` | `2.13.envoy` | `2.15` | `needs-update` | Registry behind Envoy. |
| `luajit` | `0.0.0-260126-871db2c.envoy` | `871db2c84ecefd70a850e03a6c340214a81739f0` | `unknown-mapping` | Envoy uses rolling SHA; registry pseudo-version likely same source. |
| `lz4` | `1.10.0.bcr.2.envoy` | `1.10.0` | `up-to-date` | Same upstream version; registry carries BCR suffix. |
| `msgpack-cxx` | `7.0.0.envoy` | `7.0.0` | `up-to-date` | Exact version match. |
| `nghttp2` | `1.66.0.envoy` | `1.66.0` | `up-to-date` | Exact version match. |
| `ocp-diag-core` | `0.0.0-230505-e965ac0.envoy` | `e965ac0ac6db6686169678e2a6c77ede904fa82c` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit lineage. |
| `opentelemetry-cpp` | `1.24.0.envoy` | `1.28.0` | `needs-update` | Registry behind Envoy. |
| `perfetto` | `53.0.envoy` | `57.2` | `needs-update` | Registry behind Envoy optional tracing dependency. |
| `prometheus-metrics-model` | `0.6.2.envoy` | `0.6.2` | `up-to-date` | Matches API repository_locations pin. |
| `proto-converter` | `0.0.0-20240625-1db7653.envoy` | `1db76535b86b80aa97489a1edcc7009e18b67ab7` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit lineage. |
| `proto-field-extraction` | `0.0.0-240710-d5d39f0.envoy` | `d5d39f0373e9b6691c32c85929838b1006bcb3fb` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit lineage. |
| `proto-processing` | `0.0.0-250110-279353c.envoy` | `279353cfab372ac7f268ae529df29c4d546ca18d` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit lineage. |
| `protobuf` | `33.4.envoy` | `35.1` | `needs-update` | Registry behind Envoy core protobuf pin. |
| `protoc-gen-validate` | `1.3.0.envoy` | `1.3.3` | `needs-update` | API repo pin is newer than registry. |
| `proxy-wasm-cpp-host` | `0.0.0-260115-beb8a4e.envoy` | `f2db56af443571e92a31c0b877106d9ea96e19ef` | `unknown-mapping` | Registry pseudo-version differs from Envoy SHA; likely older host snapshot. |
| `proxy-wasm-cpp-sdk` | `0.0.0-250925-e5256b0.envoy` | `e5256b0c5463ea9961965ad5de3e379e00486640` | `unknown-mapping` | Registry pseudo-version likely derived from same SHA. |
| `proxy-wasm-rust-sdk` | `0.2.4-251205-5283e57.envoy` | `0.2.4` | `unknown-mapping` | Semver matches but registry adds commit/date suffix; effectively aligned at tag 0.2.4. |
| `qat-zstd` | `1.0.0.envoy` | `1.0.0` | `up-to-date` | Exact version match. |
| `qatlib` | `25.08.0.envoy` | `26.02.0` | `needs-update` | Registry behind Envoy. |
| `qatzip` | `1.3.1.envoy` | `1.3.2` | `needs-update` | Registry behind Envoy. |
| `ragel` | `7.0.4-211228-d4577c9.envoy` | `d4577c924451b331c73c8ed0af04f6efd35ac0b4` | `unknown-mapping` | Pseudo-version vs SHA; likely same commit lineage. |
| `rules_apple` | `3.20.1.envoy` | `3.20.1` | `up-to-date` | Exact version match. |
| `rules_rust` | `0.68.1.envoy` | `0.69.0` | `needs-update` | Registry lags Envoy MODULE and repository pin. |
| `simdutf` | `7.3.4.envoy` | `8.1.0` | `needs-update` | Registry behind Envoy; tied to V8/proxy-wasm host bundle. |
| `skywalking-data-collect-protocol` | `10.3.0.envoy` | `10.4.0` | `needs-update` | Registry behind Envoy. |
| `sql-parser` | `0.0.0-200610-3b40ba2.envoy` | `52e5ad1f4fbb21301fcee7f9d18eef7e6ae6ab3e` | `unknown-mapping` | Registry pseudo-version differs substantially from Envoy SHA; likely stale. |
| `su-exec` | `0.3.envoy` | `0.3` | `up-to-date` | Exact version match. |
| `tcmalloc` | `0.0.0-20241022-5da4a88.envoy` | `12f255231938d30493186b0a037feedd70f5a1c1` | `unknown-mapping` | Registry pseudo-version and Envoy SHA may not refer to same snapshot. |
| `thrift` | `0.22.0.envoy` | `0.24.0` | `needs-update` | Registry behind Envoy. |
| `toolchains_llvm` | `1.8.0.envoy` | `1.8.0` | `up-to-date` | Exact version match. |
| `uadk` | `2.9.envoy` | `2.9` | `up-to-date` | Exact version match. |
| `v8` | `13.8.258.26.envoy` | `14.6.202.10` | `needs-update` | Registry behind Envoy; tied to proxy-wasm host bundle. |
| `vectorscan` | `5.4.11.envoy` | `5.4.11` | `up-to-date` | Exact version match. |
| `vpp-vcl` | `26.02-dev-85abefb.envoy` | `85abefb55ee931fa4e45c0b6a9fc8c43118651b3` | `unknown-mapping` | Registry pseudo-version likely derived from commit but not trivially comparable. |
| `wamr` | `2.4.4.envoy` | `WAMR-2.4.4` | `up-to-date` | Same upstream version with/without upstream tag prefix. |
| `wasmtime` | `24.0.0.envoy` | `45.0.2` | `needs-update` | Registry well behind Envoy. |
| `yq.bzl` | `0.1.1.envoy` | `0.1.1` | `up-to-date` | Exact version match. |
| `zipkin-api` | `1.0.0.envoy` | `1.0.0` | `up-to-date` | Matches API repository_locations pin. |
| `zlib-ng` | `2.3.2.envoy` | `2.3.2` | `up-to-date` | Exact version match. |

## Needs Update

- **`aws-c-auth-testdata`**: registry `0.9.5.envoy` vs Envoy `0.10.4` — Registry trails Envoy semver pin.
- **`boringssl-fips`**: registry `0.20250107.0.envoy` vs Envoy `0.20260413.0` — Envoy boringssl_fips reuses `boringssl` location_name; registry lags Envoy BoringSSL snapshot.
- **`dd-trace-cpp`**: registry `2.0.0.envoy` vs Envoy `2.1.1` — Envoy is newer than registry.
- **`grpc`**: registry `1.76.0.bcr.1.envoy` vs Envoy `1.83.0` — Large gap from Envoy gRPC pin.
- **`ipp-crypto`**: registry `1.3.0.envoy` vs Envoy `2.2.0` — Registry significantly behind Envoy.
- **`kafka_message`**: registry `3.9.1.envoy` vs Envoy `3.9.2` — Minor update needed.
- **`libevent`**: registry `2.1.12-stable.bcr.0.200728-62c152d.envoy` vs Envoy `release-2.2.2-alpha` — Registry is on older libevent stream; Envoy moved to 2.2.2-alpha.
- **`libmaxminddb`**: registry `1.12.2.envoy` vs Envoy `1.13.3` — Registry behind Envoy.
- **`liburing`**: registry `2.13.envoy` vs Envoy `2.15` — Registry behind Envoy.
- **`opentelemetry-cpp`**: registry `1.24.0.envoy` vs Envoy `1.28.0` — Registry behind Envoy.
- **`perfetto`**: registry `53.0.envoy` vs Envoy `57.2` — Registry behind Envoy optional tracing dependency.
- **`protobuf`**: registry `33.4.envoy` vs Envoy `35.1` — Registry behind Envoy core protobuf pin.
- **`protoc-gen-validate`**: registry `1.3.0.envoy` vs Envoy `1.3.3` — API repo pin is newer than registry.
- **`qatlib`**: registry `25.08.0.envoy` vs Envoy `26.02.0` — Registry behind Envoy.
- **`qatzip`**: registry `1.3.1.envoy` vs Envoy `1.3.2` — Registry behind Envoy.
- **`rules_rust`**: registry `0.68.1.envoy` vs Envoy `0.69.0` — Registry lags Envoy MODULE and repository pin.
- **`simdutf`**: registry `7.3.4.envoy` vs Envoy `8.1.0` — Registry behind Envoy; tied to V8/proxy-wasm host bundle.
- **`skywalking-data-collect-protocol`**: registry `10.3.0.envoy` vs Envoy `10.4.0` — Registry behind Envoy.
- **`thrift`**: registry `0.22.0.envoy` vs Envoy `0.24.0` — Registry behind Envoy.
- **`v8`**: registry `13.8.258.26.envoy` vs Envoy `14.6.202.10` — Registry behind Envoy; tied to proxy-wasm host bundle.
- **`wasmtime`**: registry `24.0.0.envoy` vs Envoy `45.0.2` — Registry well behind Envoy.

## Registry Ahead / Hard Switchover

- **`emsdk`**: registry `4.0.23.envoy` vs Envoy `4.0.6` — Registry is ahead of Envoy; switchover may need compatibility check.

## Up to Date

- **`aspect_bazel_lib`**: registry `2.21.2.envoy` vs Envoy `2.21.2` — Exact version match; registry suffix only.
- **`boost.headers`**: registry `1.89.0.envoy` vs Envoy `1.89.0` — Exact version match.
- **`cel-cpp`**: registry `0.14.0.envoy` vs Envoy `0.14.0` — Exact version match.
- **`cpp2sky`**: registry `0.6.0.envoy` vs Envoy `0.6.0` — Exact version match.
- **`flatbuffers`**: registry `25.12.19.envoy` vs Envoy `25.12.19` — Exact version match.
- **`hyperscan`**: registry `5.4.2.envoy` vs Envoy `5.4.2` — Exact version match.
- **`icu`**: registry `78.2.envoy` vs Envoy `78.2` — Exact version match.
- **`libcircllhist`**: registry `0.3.2.envoy` vs Envoy `0.3.2` — Exact version match.
- **`libprotobuf-mutator`**: registry `1.5.envoy` vs Envoy `1.5` — Exact version match.
- **`librdkafka`**: registry `2.6.0.envoy` vs Envoy `2.6.0` — Exact version match.
- **`lz4`**: registry `1.10.0.bcr.2.envoy` vs Envoy `1.10.0` — Same upstream version; registry carries BCR suffix.
- **`msgpack-cxx`**: registry `7.0.0.envoy` vs Envoy `7.0.0` — Exact version match.
- **`nghttp2`**: registry `1.66.0.envoy` vs Envoy `1.66.0` — Exact version match.
- **`prometheus-metrics-model`**: registry `0.6.2.envoy` vs Envoy `0.6.2` — Matches API repository_locations pin.
- **`qat-zstd`**: registry `1.0.0.envoy` vs Envoy `1.0.0` — Exact version match.
- **`rules_apple`**: registry `3.20.1.envoy` vs Envoy `3.20.1` — Exact version match.
- **`su-exec`**: registry `0.3.envoy` vs Envoy `0.3` — Exact version match.
- **`toolchains_llvm`**: registry `1.8.0.envoy` vs Envoy `1.8.0` — Exact version match.
- **`uadk`**: registry `2.9.envoy` vs Envoy `2.9` — Exact version match.
- **`vectorscan`**: registry `5.4.11.envoy` vs Envoy `5.4.11` — Exact version match.
- **`wamr`**: registry `2.4.4.envoy` vs Envoy `WAMR-2.4.4` — Same upstream version with/without upstream tag prefix.
- **`yq.bzl`**: registry `0.1.1.envoy` vs Envoy `0.1.1` — Exact version match.
- **`zipkin-api`**: registry `1.0.0.envoy` vs Envoy `1.0.0` — Matches API repository_locations pin.
- **`zlib-ng`**: registry `2.3.2.envoy` vs Envoy `2.3.2` — Exact version match.

## Unknown / No Clear Envoy Mapping

- **`aws-lc-fips`**: registry `1.66.2.envoy` vs Envoy `unknown` — No aws-lc-fips pin found in fetched Envoy files; registry module likely for future/alternate FIPS flow.
- **`bazel-compdb`**: registry `0.0.0-20220906-4086479.envoy` vs Envoy `40864791135333e1446a04553b63cbe744d358d0` — Same upstream project, but Envoy uses full git SHA while registry encodes pseudo-version.
- **`colm`**: registry `0.14.7-211228-2d8ba76.envoy` vs Envoy `2d8ba76ddaf6634f285d0a81ee42d5ee77d084cf` — Registry pseudo-version appears derived from same SHA; manual confirmation needed.
- **`dragonbox`**: registry `0.0.0-241028-6c7c925.envoy` vs Envoy `6c7c925b571d54486b9ffae8d9d18a822801cbda` — Registry pseudo-version likely derived from Envoy SHA.
- **`fp16`**: registry `0.0.0-210320-0a92994.envoy` vs Envoy `3d2de1816307bac63c16a297e8c4dc501b4076df` — Registry pseudo-version and Envoy SHA need manual lineage check.
- **`go-fips`**: registry `1.24.12.envoy` vs Envoy `unknown` — Only observed as transitive dep of registry boringssl-fips module, not in fetched Envoy main files.
- **`googleurl`**: registry `0.0.0-221103-dd4080f.envoy` vs Envoy `dd4080fec0b443296c0ed0036e1e776df8813aa7` — Registry pseudo-version likely tracks same SHA; manual confirmation needed.
- **`grpc-httpjson-transcoding`**: registry `0.0.0-20250507-a6e226f.envoy` vs Envoy `a6e226f9a2e656a973df3ad48f0ee5efacce1a28` — Registry pseudo-version appears derived from Envoy commit SHA.
- **`hessian2-codec`**: registry `0.0.0-250114-6f5a647.envoy` vs Envoy `6f5a64770f0374a761eece13c8863b80dc5adcd8` — Pseudo-version vs SHA; likely same commit.
- **`libsxg`**: registry `0.0.0-210708-beaa393.envoy` vs Envoy `beaa3939b76f8644f6833267e9f2462760838f18` — Registry pseudo-version likely same commit lineage.
- **`luajit`**: registry `0.0.0-260126-871db2c.envoy` vs Envoy `871db2c84ecefd70a850e03a6c340214a81739f0` — Envoy uses rolling SHA; registry pseudo-version likely same source.
- **`ocp-diag-core`**: registry `0.0.0-230505-e965ac0.envoy` vs Envoy `e965ac0ac6db6686169678e2a6c77ede904fa82c` — Pseudo-version vs SHA; likely same commit lineage.
- **`proto-converter`**: registry `0.0.0-20240625-1db7653.envoy` vs Envoy `1db76535b86b80aa97489a1edcc7009e18b67ab7` — Pseudo-version vs SHA; likely same commit lineage.
- **`proto-field-extraction`**: registry `0.0.0-240710-d5d39f0.envoy` vs Envoy `d5d39f0373e9b6691c32c85929838b1006bcb3fb` — Pseudo-version vs SHA; likely same commit lineage.
- **`proto-processing`**: registry `0.0.0-250110-279353c.envoy` vs Envoy `279353cfab372ac7f268ae529df29c4d546ca18d` — Pseudo-version vs SHA; likely same commit lineage.
- **`proxy-wasm-cpp-host`**: registry `0.0.0-260115-beb8a4e.envoy` vs Envoy `f2db56af443571e92a31c0b877106d9ea96e19ef` — Registry pseudo-version differs from Envoy SHA; likely older host snapshot.
- **`proxy-wasm-cpp-sdk`**: registry `0.0.0-250925-e5256b0.envoy` vs Envoy `e5256b0c5463ea9961965ad5de3e379e00486640` — Registry pseudo-version likely derived from same SHA.
- **`proxy-wasm-rust-sdk`**: registry `0.2.4-251205-5283e57.envoy` vs Envoy `0.2.4` — Semver matches but registry adds commit/date suffix; effectively aligned at tag 0.2.4.
- **`ragel`**: registry `7.0.4-211228-d4577c9.envoy` vs Envoy `d4577c924451b331c73c8ed0af04f6efd35ac0b4` — Pseudo-version vs SHA; likely same commit lineage.
- **`sql-parser`**: registry `0.0.0-200610-3b40ba2.envoy` vs Envoy `52e5ad1f4fbb21301fcee7f9d18eef7e6ae6ab3e` — Registry pseudo-version differs substantially from Envoy SHA; likely stale.
- **`tcmalloc`**: registry `0.0.0-20241022-5da4a88.envoy` vs Envoy `12f255231938d30493186b0a037feedd70f5a1c1` — Registry pseudo-version and Envoy SHA may not refer to same snapshot.
- **`vpp-vcl`**: registry `26.02-dev-85abefb.envoy` vs Envoy `85abefb55ee931fa4e45c0b6a9fc8c43118651b3` — Registry pseudo-version likely derived from commit but not trivially comparable.

## Envoy Deps Missing from Registry (best-effort)

- **`boringssl`** — Envoy uses upstream `boringssl` directly in `bazel/repository_locations.bzl`; registry has `boringssl-fips` but not plain `boringssl` in this modules set.
- **`abseil-cpp`** — Core Envoy dependency, no corresponding module in audited registry set.
- **`c-ares`** — Core Envoy dependency, not present in audited registry set.
- **`re2`** — Core Envoy dependency, not present in audited registry set.
- **`quiche`** — HTTP/3 dependency, not present in audited registry set.
- **`platforms`** — Bzlmod dependency in Envoy MODULE.bazel, not present in audited registry set.
- **`rules_python`** — Bzlmod dependency in Envoy MODULE.bazel, not present in audited registry set.
- **`zstd`** — Bzlmod dependency in Envoy MODULE.bazel, not present in audited registry set.
- **`gperftools`** — Bzlmod dependency in Envoy MODULE.bazel, not present in audited registry set.
- **`numactl`** — Envoy dependency, not present in audited registry set.

## Methodology

This audit:
1. Enumerated every module directory under `bazel-registry/modules/`.
2. Read each module `metadata.json` and used the highest entry in `versions` as the registry comparison point.
3. Read the following Envoy files from `envoyproxy/envoy` `main` at the commit above:
   - [`bazel/repository_locations.bzl`](https://github.com/envoyproxy/envoy/blob/16dd0f1efde1933677335f4785555d6d3736fbfc/bazel/repository_locations.bzl)
   - [`MODULE.bazel`](https://github.com/envoyproxy/envoy/blob/16dd0f1efde1933677335f4785555d6d3736fbfc/MODULE.bazel)
   - [`bazel/repositories.bzl`](https://github.com/envoyproxy/envoy/blob/16dd0f1efde1933677335f4785555d6d3736fbfc/bazel/repositories.bzl)
   - [`bazel/dependency_imports.bzl`](https://github.com/envoyproxy/envoy/blob/16dd0f1efde1933677335f4785555d6d3736fbfc/bazel/dependency_imports.bzl)
   - [`api/bazel/repository_locations.bzl`](https://github.com/envoyproxy/envoy/blob/16dd0f1efde1933677335f4785555d6d3736fbfc/api/bazel/repository_locations.bzl)
4. Mapped registry modules to Envoy dependency names heuristically (for example `protobuf` → `com_google_protobuf`, `grpc` → `com_github_grpc_grpc`).
5. Compared semver directly when both sides were semver-like. When Envoy used a git SHA or a registry module encoded a pseudo-version from a commit/date, the result is marked `unknown-mapping` unless equivalence was obvious from an identical upstream release tag.

### Notes on version interpretation

- Many registry modules use an `.envoy` suffix; that was treated as packaging metadata, not an upstream version change.
- Some registry modules encode commit-based pseudo-versions like `0.0.0-YYYYMMDD-<sha7>.envoy`, while Envoy pins the full SHA in `repository_locations.bzl`. Those need manual confirmation or source provenance checks before calling them updated/stale.
- `boringssl-fips` is special: Envoy's `_boringssl_fips()` uses `location_name = "boringssl"`, so the effective source version comes from the `boringssl` entry in `bazel/repository_locations.bzl`.
- `prometheus-metrics-model`, `zipkin-api`, and `protoc-gen-validate` were resolved from `api/bazel/repository_locations.bzl`.

## Recommended Next Steps

1. **Prioritize security-sensitive updates**: bring `boringssl-fips`, `protobuf`, `grpc`, `protoc-gen-validate`, and `aws-c-auth-testdata` in line first.
2. **Update the proxy-wasm/V8 cluster together**: `v8`, `simdutf`, `wasmtime`, and probably `proxy-wasm-cpp-host` should move in a coordinated batch because Envoy notes they are updated together.
3. **Refresh Intel/QAT stack together**: `ipp-crypto`, `qatlib`, `qatzip`, and `uadk` should be reviewed as a family, even though `uadk` is already current.
4. **Resolve pseudo-version lineage** for `googleurl`, `colm`, `ragel`, `proto-*`, `sql-parser`, `tcmalloc`, `proxy-wasm-*`, and similar modules by checking the underlying source tarball/commit mapping.
5. **Decide whether to backport or fast-forward registry-ahead entries** like `emsdk`; being ahead is not automatically safe if Envoy patches/build files assume the older source layout.
6. **Consider adding missing high-value Envoy deps** to the registry set (`boringssl`, `abseil-cpp`, `re2`, `c-ares`, `quiche`, etc.) if the goal is fuller registry coverage of Envoy main.
