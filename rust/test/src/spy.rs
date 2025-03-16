use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

#[derive(Clone, Debug)]
pub struct Spy {
    pub calls: Arc<Mutex<HashMap<String, Vec<String>>>>,
}

impl Spy {
    pub fn new() -> Self {
        Self {
            calls: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn clear(&self, key: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls.insert(key.to_string(), Vec::new());
    }

    pub fn get(&self, key: &str) -> Vec<String> {
        let mut calls = self.calls.lock().unwrap();
        calls
            .entry(key.to_string())
            .or_insert_with(Vec::new)
            .to_vec()
    }

    pub fn push(&self, key: &str, value: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls
            .entry(key.to_string())
            .or_insert_with(Vec::new)
            .to_vec();
        let vec = calls.get_mut(key).unwrap();
        vec.push(value.to_string());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial(toolshed_lock)]
    fn test_spy_constructor() {
        let spy = Spy::new();
        let calls = spy.calls.lock().unwrap();
        assert!(calls.is_empty());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_spy_clear() {
        let spy = Spy {
            calls: Arc::new(Mutex::new(HashMap::new())),
        };
        let messages = vec![
            "SOME".to_string(),
            "TEST".to_string(),
            "MESSAGES".to_string(),
        ];
        {
            let mut calls = spy.calls.lock().unwrap();
            calls.insert("FOO".to_string(), messages.clone());
        }
        spy.clear("FOO");
        assert!(spy.get("FOO").is_empty());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_spy_get() {
        let spy = Spy {
            calls: Arc::new(Mutex::new(HashMap::new())),
        };
        let messages = vec![
            "SOME".to_string(),
            "TEST".to_string(),
            "MESSAGES".to_string(),
        ];
        {
            let mut calls = spy.calls.lock().unwrap();
            calls.insert("FOO".to_string(), messages.clone());
        }
        assert_eq!(spy.get("FOO"), messages);
        assert!(spy.get("BAR").is_empty());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_spy_push() {
        let spy = Spy {
            calls: Arc::new(Mutex::new(HashMap::new())),
        };
        let messages = vec!["SOME", "TEST", "MESSAGES"];
        spy.push("FOO", messages[0]);
        spy.push("FOO", messages[1]);
        spy.push("FOO", messages[2]);
        assert_eq!(spy.get("FOO"), messages);
    }
}
