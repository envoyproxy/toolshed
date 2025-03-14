use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

#[derive(Clone)]
pub struct Spy {
    pub calls: Arc<Mutex<HashMap<String, Vec<String>>>>,
}

impl Spy {
    pub fn new() -> Self {
        Self {
            calls: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn get(&self, key: &str) -> Vec<String> {
        let mut calls = self.calls.lock().unwrap();
        calls
            .entry(key.to_string())
            .or_insert_with(Vec::new)
            .to_vec()
    }

    pub fn clear(&self, key: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls.insert(key.to_string(), Vec::new());
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
