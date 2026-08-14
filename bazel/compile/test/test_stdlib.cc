// Exercises std::string and std::vector so that the resulting binary carries
// standard library symbols in whichever inline namespace the toolchain's C++
// standard library uses (__cxx11 for libstdc++, __1 for libc++).
//
// Kept deliberately simple: the point is the symbols, not the behaviour.
#include <iostream>
#include <string>
#include <vector>

std::string Join(const std::vector<std::string>& parts) {
  std::string out;
  for (const auto& part : parts) {
    if (!out.empty()) {
      out += ",";
    }
    out += part;
  }
  return out;
}

int main() {
  const std::vector<std::string> parts = {"hello", "stdlib"};
  std::cout << Join(parts) << std::endl;
  return 0;
}
