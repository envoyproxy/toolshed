#include <iostream>

// Exercise compiler-rt builtins by performing 128-bit integer division.
// The __divti3 symbol (128-bit signed division) is provided by
// libclang_rt.builtins.a (compiler-rt) or libgcc on platforms that do not
// have a native 128-bit division instruction (e.g. aarch64, x86_64).
int main() {
    volatile __int128 a = static_cast<__int128>(1000000000) * 1000000000;
    volatile __int128 b = 7;
    volatile __int128 result = a / b;
    std::cout << "result: " << static_cast<long long>(result) << std::endl;
    return 0;
}
