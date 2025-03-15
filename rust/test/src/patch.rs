use guerrilla::PatchGuard;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

pub struct Patches {
    pub patches: Mutex<HashMap<String, Vec<Arc<Mutex<PatchGuard>>>>>,
}

impl Patches {
    // Constructor to create a new Patches instance
    pub fn new() -> Self {
        Self {
            patches: Mutex::new(HashMap::new()),
        }
    }

    pub fn push(&self, key: &str, guards: Vec<Arc<Mutex<PatchGuard>>>) {
        let mut patches = self.patches.lock().unwrap();
        patches.insert(key.to_string(), guards);
    }

    // Retrieve a Vec<PatchGuard> for a specific key
    pub fn get(&self, key: &str) -> Option<Vec<Arc<Mutex<PatchGuard>>>> {
        let patches = self.patches.lock().unwrap();
        patches.get(key).cloned()
    }

    pub fn clear(&self, key: &str) {
        let mut patches = self.patches.lock().unwrap();
        patches.remove(key).unwrap();
    }
}
