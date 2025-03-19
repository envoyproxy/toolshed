# Rust Comprehension Macro

A Rust macro for Python-like list/dictionary comprehensions with support for vector, HashMap, and iterator comprehensions.

## Usage

### Vector Comprehensions

Create vectors using a comprehension-like syntax with square brackets:

```rust
// Basic vector comprehension
let squares = comp![x in 1..=5 => x * x];
// Result: [1, 4, 9, 16, 25]

// With a filter condition
let even_squares = comp![x in 1..=5 => x * x; if x % 2 == 0];
// Result: [4, 16]

// With a complex expression
let points = comp![i in 1..=3 => Point { x: i, y: i * i }];
```

### HashMap Comprehensions

Create HashMaps using curly braces and tuple patterns:

```rust
// Basic HashMap comprehension
let pairs = vec![(1, "one"), (2, "two"), (3, "three")];
let map = comp! {(k, v) in pairs => (k, v.to_string())};
// Result: {1: "one", 2: "two", 3: "three"}

// With a filter condition
let filtered_map = comp! {(k, v) in pairs => (k, v.to_string()); if k > 1};
// Result: {2: "two", 3: "three"}
```

### Iterator Comprehensions

Create iterators using the `iter!` prefix:

```rust
// Basic iterator comprehension
let iter = comp!(iter! x in 1..=3 => x * 2);
// Can be collected: iter.collect::<Vec<_>>() = [2, 4, 6]

// With a filter condition
let filtered_iter = comp!(iter! x in 1..=5 => x * 2; if x > 2);
// Result when collected: [6, 8, 10]
```

## Advanced Examples

### Nested Comprehensions

```rust
// Flattening a matrix
let matrix = vec![vec![1, 2], vec![3, 4]];
let flattened = comp![x in comp![row in matrix => row].concat() => x];
// Result: [1, 2, 3, 4]

// Creating a triangular pattern
let nested = comp![x in 1..=3 => comp![y in 1..=x => (x, y)]];
// Result: [[(1, 1)], [(2, 1), (2, 2)], [(3, 1), (3, 2), (3, 3)]]
```

### String Transformations

```rust
let words = vec!["hello", "world"];
let upper_words = comp![word in words => word.to_uppercase()];
// Result: ["HELLO", "WORLD"]
```

## Notes

- Vector and HashMap comprehensions evaluate eagerly and return a collected result
- Iterator comprehensions are lazy and need to be collected manually
- Use `iter!` prefix to clearly indicate an iterator comprehension
- For filter conditions, use `if` after the expression

## Implementation Details

- The macro handles ownership correctly via cloning for HashMap operations
- Proper pattern matching for filters ensures compatibility with all types
- The macro works with ranges, vectors, and other iterable collections
