// Links the wee8 prebuilt through the wasm C++ API, which is what Envoy's
// proxy-wasm v8 runtime uses (wasm::Engine::make / wasm::Store::make).
//
// The wasm *C* API (wasm_engine_new & co.) is intentionally compiled out of
// src/wasm/c-api.cc by the v8 patch in envoyproxy/bazel-registry (`#if 0`
// around the extern "C" block), so it must not be probed here.
#include "wasm-api/wasm.hh"

int main() {
  auto engine = wasm::Engine::make();
  auto store = wasm::Store::make(engine.get());
  return store ? 0 : 1;
}
