use axum::http::HeaderMap;
use indexmap::IndexMap;
use serde::Serialize;
use toolshed_core as core;

#[derive(Clone, PartialEq, Serialize)]
pub struct OrderedMap(core::mapping::OrderedMap);

core::impl_orderedmap!(OrderedMap);

impl From<HeaderMap> for OrderedMap {
    fn from(src: HeaderMap) -> OrderedMap {
        let mut map = IndexMap::new();

        for (key, value) in src.iter() {
            map.insert(
                key.to_string(),
                value.to_str().unwrap_or_default().to_string(),
            );
        }
        OrderedMap(core::mapping::OrderedMap::from_iter(map))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial(toolshed_lock)]
    fn test_map_from_headermap() {
        let mut headers = HeaderMap::new();
        headers.insert("X-FOO", "foo".parse().unwrap());
        headers.insert("X-BAR", "bar".parse().unwrap());
        headers.insert("X-BAZ", "bar".parse().unwrap());
        let mapping = OrderedMap::from(headers.clone());
        for (i, (key, value)) in headers.iter().enumerate() {
            let key_str = key.as_str();
            let value_str = value.to_str().unwrap();
            assert_eq!(mapping.get(key_str), Some(&value_str.to_string()));
            assert_eq!(mapping.keys().nth(i), Some(&key_str.to_string()));
        }
    }
}
