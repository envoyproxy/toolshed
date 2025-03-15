use guerrilla::PatchGuard;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

pub struct Patches {
    pub patches: Mutex<HashMap<String, Vec<Arc<Mutex<PatchGuard>>>>>,
}

impl Patches {
    pub fn new() -> Self {
        Self {
            patches: Mutex::new(HashMap::new()),
        }
    }

    pub fn clear(&self, key: &str) {
        let mut patches = self.patches.lock().unwrap();
        patches.remove(key).unwrap();
    }

    pub fn get(&self, key: &str) -> Option<Vec<Arc<Mutex<PatchGuard>>>> {
        let patches = self.patches.lock().unwrap();
        patches.get(key).cloned()
    }

    pub fn push(&self, key: &str, guards: Vec<Arc<Mutex<PatchGuard>>>) {
        let mut patches = self.patches.lock().unwrap();
        patches.insert(key.to_string(), guards);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use guerrilla::patch0;
    use serial_test::serial;

    fn _noop() {
        println!("NOOP");
        println!("NOOP");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_patches_constructor() {
        let patches = Patches::new();
        let _patches = patches.patches.lock().unwrap();
        assert!(_patches.is_empty());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_patches_clear() {
        let patches = Patches {
            patches: Mutex::new(HashMap::new()),
        };
        let patch_guards = vec![
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
        ];
        {
            let mut _patches = patches.patches.lock().unwrap();
            _patches.insert("FOO".to_string(), patch_guards.clone());
        }
        patches.clear("FOO");
        let _patches = patches.patches.lock().unwrap();
        assert!(!_patches.contains_key("FOO"));
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_patches_get() {
        let patches = Patches {
            patches: Mutex::new(HashMap::new()),
        };
        let patch_guards = vec![
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
        ];
        let ptrs: Vec<_> = patch_guards
            .iter()
            .map(|guard| guard.lock().unwrap().ptr)
            .collect();
        {
            let mut _patches = patches.patches.lock().unwrap();
            _patches.insert("FOO".to_string(), patch_guards.clone());
        }

        let result = patches.get("FOO");
        assert!(result.is_some(), "Should have found key 'FOO'");
        let result_vec = result.unwrap();
        assert_eq!(
            result_vec.len(),
            patch_guards.len(),
            "Vector lengths should match"
        );
        for (i, guard) in result_vec.iter().enumerate() {
            let result_ptr = guard.lock().unwrap().ptr;
            assert_eq!(
                result_ptr, ptrs[i],
                "PatchGuard ptr at index {} should match",
                i
            );
        }
        assert!(patches.get("BAR").is_none(), "Key 'BAR' should not exist");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_patches_push() {
        let patches = Patches {
            patches: Mutex::new(HashMap::new()),
        };
        let patch_guards = vec![
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
            Arc::new(Mutex::new(patch0(_noop, _noop))),
        ];
        let ptrs: Vec<_> = patch_guards
            .iter()
            .map(|guard| guard.lock().unwrap().ptr)
            .collect();
        patches.push("FOO", patch_guards.clone());
        let result = patches.get("FOO");
        assert!(result.is_some(), "Should have found key 'FOO'");
        let result_vec = result.unwrap();
        assert_eq!(
            result_vec.len(),
            patch_guards.len(),
            "Vector lengths should match"
        );
        for (i, guard) in result_vec.iter().enumerate() {
            let result_ptr = guard.lock().unwrap().ptr;
            assert_eq!(
                result_ptr, ptrs[i],
                "PatchGuard ptr at index {} should match",
                i
            );
        }
    }
}
