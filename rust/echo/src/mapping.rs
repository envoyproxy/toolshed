use axum::http::HeaderMap;
use indexmap::IndexMap;
use serde::{Deserialize, Serialize, de};

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct OrderedMap(IndexMap<String, String>);

impl From<HeaderMap> for OrderedMap {
    fn from(src: HeaderMap) -> OrderedMap {
        let mut map = IndexMap::new();

        for (key, value) in src.iter() {
            map.insert(
                key.to_string(),
                value.to_str().unwrap_or_default().to_string(),
            );
        }
        OrderedMap(map)
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
            assert_eq!(mapping.0.get(key_str), Some(&value_str.to_string()));
            assert_eq!(mapping.0.keys().nth(i), Some(&key_str.to_string()));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_map_from_list() {
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
            assert_eq!(mapping.0.get(key), Some(value));
            assert_eq!(mapping.0.keys().nth(i), Some(key));
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_map_from_iterator() {
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
            assert_eq!(mapping.0.get(key), Some(value));
            assert_eq!(mapping.0.keys().nth(i), Some(key));
        }
    }

    #[test]
    fn test_ordered_map_deserialization() {
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
}
