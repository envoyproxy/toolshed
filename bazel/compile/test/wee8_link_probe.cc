#include "wasm-api/wasm.h"

int main() {
  wasm_engine_t *engine = wasm_engine_new();
  wasm_store_t *store = wasm_store_new(engine);
  wasm_store_delete(store);
  wasm_engine_delete(engine);
  return 0;
}
