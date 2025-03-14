use guerrilla::PatchGuard;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

pub struct Patches {
    pub calls: Mutex<HashMap<String, Vec<Arc<Mutex<PatchGuard>>>>>,
}

impl Patches {
    // Constructor to create a new Patches instance
    pub fn new() -> Self {
        Self {
            calls: Mutex::new(HashMap::new()),
        }
    }

    pub fn push(&self, key: &str, guards: Vec<Arc<Mutex<PatchGuard>>>) {
        let mut calls = self.calls.lock().unwrap();
        calls.insert(key.to_string(), guards);
    }

    // Retrieve a Vec<PatchGuard> for a specific key
    pub fn get(&self, key: &str) -> Option<Vec<Arc<Mutex<PatchGuard>>>> {
        let calls = self.calls.lock().unwrap();
        calls.get(key).cloned()
    }

    pub fn clear(&self, key: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls.remove(key).unwrap();
    }
}
