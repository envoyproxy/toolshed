#include <assert.h>

#include "third_party/wasm-api/wasm.hh"

int main() {
  auto config = wasm::Config::make();
  assert(config != nullptr);
  return 0;
}
