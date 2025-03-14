use indexmap::IndexMap;
use serde::{de, Deserialize, Serialize};

#[macro_export]
macro_rules! impl_orderedmap {
    ($struct:ident) => {
        toolshed_core::_impl_orderedmap!($struct);
        toolshed_core::_impl_orderedmap_from!($struct, (&[(String, String)],));
        toolshed_core::_impl_orderedmap_fromiter!($struct, ((String, String),));
        toolshed_core::_impl_orderedmap_deserialize!($struct);
    };
}

#[macro_export]
macro_rules! _impl_orderedmap {
    ($struct:ident) => {
        impl $struct {
            pub fn get(&self, key: &str) -> Option<&String> {
                self.0.get(key)
            }

            pub fn keys(&self) -> impl Iterator<Item = &String> {
                self.0.keys()
            }
        }

        impl std::fmt::Debug for $struct {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "{:?}", self.0)
            }
        }
    };
}

#[macro_export]
macro_rules! _impl_orderedmap_deserialize {
    ($struct:ident) => {
        impl<'de> serde::Deserialize<'de> for $struct {
            fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
            where
                D: serde::de::Deserializer<'de>,
            {
                let map: Vec<(String, String)> = Vec::deserialize(deserializer)?;
                Ok($struct(toolshed_core::mapping::OrderedMap::from_iter(map)))
            }
        }
    };
}

#[macro_export]
macro_rules! _impl_orderedmap_from {
    ($struct:ident, ($( $t:ty ),* $(,)?)) => {
        $(
            impl From<$t> for $struct {
                fn from(src: $t) -> Self {
                    $struct(toolshed_core::mapping::OrderedMap::from(src))
                }
            }
        )*
    }
}

#[macro_export]
macro_rules! _impl_orderedmap_fromiter {
    ($struct:ident, ($( $t:ty ),* $(,)?)) => {
        $(
            impl FromIterator<$t> for $struct {
                fn from_iter<I: IntoIterator<Item = $t>>(iter: I) -> Self {
                    $struct(toolshed_core::mapping::OrderedMap::from_iter(iter))
                }
            }
        )*
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct OrderedMap(IndexMap<String, String>);

impl OrderedMap {
    pub fn get(&self, key: &str) -> Option<&String> {
        self.0.get(key)
    }

    pub fn keys(&self) -> impl Iterator<Item = &String> {
        self.0.keys()
    }
}

impl FromIterator<(String, String)> for OrderedMap {
    fn from_iter<I: IntoIterator<Item = (String, String)>>(iter: I) -> Self {
        let map = IndexMap::from_iter(iter);
        OrderedMap(map)
    }
}

impl From<&[(String, String)]> for OrderedMap {
    fn from(src: &[(String, String)]) -> OrderedMap {
        let map = IndexMap::from_iter(src.iter().cloned());
        OrderedMap(map)
    }
}

impl<'de> Deserialize<'de> for OrderedMap {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        let map: Vec<(String, String)> = Vec::deserialize(deserializer)?;
        Ok(OrderedMap(IndexMap::from_iter(map)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate as toolshed_core;
    use serial_test::serial;

    #[derive(Clone, PartialEq, Serialize)]
    struct CustomOrderedMap(OrderedMap);
    impl_orderedmap!(CustomOrderedMap);

    #[test]
    #[serial(toolshed_lock)]
    fn test_orderedmap_from_list() {
        let iterator = [
            ("a0".to_string(), "a".to_string()),
            ("b0".to_string(), "b".to_string()),
            ("c0".to_string(), "c".to_string()),
            ("a1".to_string(), "a".to_string()),
            ("b1".to_string(), "b".to_string()),
            ("c1".to_string(), "c".to_string()),
        ];
        let mapping = OrderedMap::from(iterator.as_ref());
        for (i, (key, value)) in iterator.iter().enumerate() {
            assert_eq!(mapping.get(key), Some(value));
            assert_eq!(mapping.keys().nth(i), Some(key));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_orderedmap_from_iterator() {
        let iterator = vec![
            ("a0".to_string(), "a".to_string()),
            ("b0".to_string(), "b".to_string()),
            ("c0".to_string(), "c".to_string()),
            ("a1".to_string(), "a".to_string()),
            ("b1".to_string(), "b".to_string()),
            ("c1".to_string(), "c".to_string()),
        ];
        let mapping = iterator.clone().into_iter().collect::<OrderedMap>();
        for (i, (key, value)) in iterator.iter().enumerate() {
            assert_eq!(mapping.get(key), Some(value));
            assert_eq!(mapping.keys().nth(i), Some(key));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_orderedmap_deserialization() {
        let json_data = r#"
    [
        ["X-FOO", "baz"],
        ["X-BAR", "baz"]
    ]
    "#;
        let deserialized: OrderedMap =
            serde_json::from_str(json_data).expect("Failed to deserialize");
        let expected = vec![
            ("X-FOO".to_string(), "baz".to_string()),
            ("X-BAR".to_string(), "baz".to_string()),
        ];
        let expected_map = OrderedMap(IndexMap::from_iter(expected));
        assert_eq!(deserialized, expected_map);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_custommap_from_list() {
        let iterator = [
            ("a0".to_string(), "a".to_string()),
            ("b0".to_string(), "b".to_string()),
            ("c0".to_string(), "c".to_string()),
            ("a1".to_string(), "a".to_string()),
            ("b1".to_string(), "b".to_string()),
            ("c1".to_string(), "c".to_string()),
        ];
        let mapping = CustomOrderedMap::from(iterator.as_ref());
        for (i, (key, value)) in iterator.iter().enumerate() {
            assert_eq!(mapping.get(key), Some(value));
            assert_eq!(mapping.keys().nth(i), Some(key));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_custommap_from_iterator() {
        let iterator = vec![
            ("a0".to_string(), "a".to_string()),
            ("b0".to_string(), "b".to_string()),
            ("c0".to_string(), "c".to_string()),
            ("a1".to_string(), "a".to_string()),
            ("b1".to_string(), "b".to_string()),
            ("c1".to_string(), "c".to_string()),
        ];
        let mapping = iterator.clone().into_iter().collect::<CustomOrderedMap>();
        for (i, (key, value)) in iterator.iter().enumerate() {
            assert_eq!(mapping.get(key), Some(value));
            assert_eq!(mapping.keys().nth(i), Some(key));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_custommap_deserialization() {
        let json_data = r#"
    [
        ["X-FOO", "baz"],
        ["X-BAR", "baz"]
    ]
    "#;
        let deserialized: CustomOrderedMap =
            serde_json::from_str(json_data).expect("Failed to deserialize");
        let expected = vec![
            ("X-FOO".to_string(), "baz".to_string()),
            ("X-BAR".to_string(), "baz".to_string()),
        ];
        let expected_map = CustomOrderedMap(OrderedMap::from_iter(expected));
        assert_eq!(deserialized, expected_map);
    }
}
