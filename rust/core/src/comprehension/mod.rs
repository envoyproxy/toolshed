#[macro_export]
macro_rules! comp {
    [ $x:ident in $range:expr => $expr:expr ] => {{
        ($range).into_iter().map(|$x| $expr).collect::<Vec<_>>()
    }};
    [ $x:ident in $range:expr => $expr:expr; if $cond:expr ] => {{
        ($range).into_iter().filter(|&$x| $cond).map(|$x| $expr).collect::<Vec<_>>()
    }};
    { ($k:ident, $v:ident) in $range:expr => ($key_expr:expr, $value_expr:expr) } => {{
        let range = $range.clone();
        range.into_iter().map(|($k, $v)| ($key_expr, $value_expr)).collect::<std::collections::HashMap<_, _>>()
    }};
    { ($k:ident, $v:ident) in $range:expr => ($key_expr:expr, $value_expr:expr); if $cond:expr } => {{
        let range = $range.clone();
        range.into_iter()
            .filter(|&(ref k, _)| {
                let $k = *k;  // Dereference here
                $cond
            })
            .map(|($k, $v)| ($key_expr, $value_expr))
            .collect::<std::collections::HashMap<_, _>>()
    }};
    (iter! $x:ident in $range:expr => $expr:expr) => {{
        ($range).into_iter().map(|$x| $expr)
    }};
    (iter! $x:ident in $range:expr => $expr:expr; if $cond:expr) => {{
        ($range).into_iter()
            .filter(|&$x| $cond)
            .map(|$x| $expr)
    }};
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    #[test]
    fn test_vec_comprehension() {
        let squares = comp![x in 1..=5 => x * x];
        assert_eq!(squares, vec![1, 4, 9, 16, 25]);

        let even_squares = comp![x in 1..=5 => x * x; if x % 2 == 0];
        assert_eq!(even_squares, vec![4, 16]);
    }

    #[test]
    fn test_hashmap_comprehension() {
        let pairs = vec![(1, "one"), (2, "two"), (3, "three")];
        let map = comp! {(k, v) in pairs => (k, v.to_string())};

        let mut expected = HashMap::new();
        expected.insert(1, "one".to_string());
        expected.insert(2, "two".to_string());
        expected.insert(3, "three".to_string());
        assert_eq!(map, expected);

        let filtered_map = comp! {(k, v) in pairs => (k, v.to_string()); if k > 1};

        let mut expected_filtered = HashMap::new();
        expected_filtered.insert(2, "two".to_string());
        expected_filtered.insert(3, "three".to_string());
        assert_eq!(filtered_map, expected_filtered);
    }

    #[test]
    fn test_iterator_comprehension() {
        let iter = comp!(iter! x in 1..=3 => x * 2);
        assert_eq!(iter.collect::<Vec<_>>(), vec![2, 4, 6]);

        let filtered_iter = comp!(iter! x in 1..=5 => x * 2; if x > 2);
        assert_eq!(filtered_iter.collect::<Vec<_>>(), vec![6, 8, 10]);
    }

    #[test]
    fn test_complex_expressions() {
        let doubles = comp![x in vec![1, 2, 3] => x * 2];
        assert_eq!(doubles, vec![2, 4, 6]);

        let words = vec!["hello", "world"];
        let upper_words = comp![word in words => word.to_uppercase()];
        assert_eq!(upper_words, vec!["HELLO", "WORLD"]);

        struct Point {
            x: i32,
            y: i32,
        }
        let points = comp![i in 1..=3 => Point { x: i, y: i * i }];
        assert_eq!(points.len(), 3);
        assert_eq!(points[0].x, 1);
        assert_eq!(points[0].y, 1);
        assert_eq!(points[2].x, 3);
        assert_eq!(points[2].y, 9);
    }

    #[test]
    fn test_nested_comprehensions() {
        let matrix = vec![vec![1, 2], vec![3, 4]];
        let flattened = comp![x in comp![row in matrix => row].concat() => x];
        assert_eq!(flattened, vec![1, 2, 3, 4]);

        let nested = comp![x in 1..=3 => comp![y in 1..=x => (x, y)]];
        assert_eq!(
            nested,
            vec![
                vec![(1, 1)],
                vec![(2, 1), (2, 2)],
                vec![(3, 1), (3, 2), (3, 3)]
            ]
        );
    }

    #[test]
    fn test_edge_cases() {
        let empty_vec: Vec<i32> = comp![x in Vec::<i32>::new() => x * 2];
        assert_eq!(empty_vec, Vec::<i32>::new());

        let single = comp![x in vec![42] => x];
        assert_eq!(single, vec![42]);

        let nothing: Vec<i32> = comp![x in 1..=10 => x; if x > 100];
        assert_eq!(nothing, Vec::<i32>::new());
    }
}
