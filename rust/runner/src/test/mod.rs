pub mod data;
pub mod dummy;
pub mod patch;
pub mod spy;

use once_cell::sync::Lazy;
use patch::Patches;
use spy::Spy;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

pub struct Tests<'a> {
    pub calls: Mutex<HashMap<String, Arc<Mutex<Test<'a>>>>>,
    pub spy: &'a Lazy<Spy>,
    pub patches: &'a Lazy<Patches>,
}

impl<'a> Tests<'a> {
    pub fn new(spy: &'a Lazy<Spy>, patches: &'a Lazy<Patches>) -> Self {
        Self {
            calls: Mutex::new(HashMap::new()),
            spy,
            patches,
        }
    }

    pub fn push(&self, key: &str, test: Arc<Mutex<Test<'a>>>) {
        let mut calls = self.calls.lock().unwrap();
        calls.insert(key.to_string(), test);
    }

    pub fn get(&self, key: &str) -> Option<Arc<Mutex<Test<'a>>>> {
        self.calls.lock().unwrap().get(key).cloned()
        // .map(|v| v)
    }

    pub fn clear(&self, key: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls.remove(key).unwrap();
    }
}

pub struct Test<'a> {
    pub name: String,
    expectations: Vec<&'a str>,
    tests: &'a Lazy<Tests<'a>>,
}

impl<'a> Test<'a> {
    pub fn new(tests: &'a Lazy<Tests<'a>>, testid: &str) -> TestRef<'a> {
        let test = Self {
            name: testid.to_string(),
            expectations: vec![],
            tests,
        };
        let test_arc = Arc::new(Mutex::new(test));
        tests.push(testid, test_arc.clone());
        TestRef { test_arc, tests }
    }

    fn patches(&self) -> &Lazy<Patches> {
        self.tests.patches
    }

    fn spy(&self) -> &Lazy<Spy> {
        self.tests.spy
    }
}

pub struct TestRef<'a> {
    test_arc: Arc<Mutex<Test<'a>>>,
    tests: &'a Lazy<Tests<'a>>,
}

impl<'a> TestRef<'a> {
    pub fn drop(&self) {
        self.tests.clear(&self.name());
    }

    pub fn name(&self) -> String {
        self.test_arc.lock().unwrap().name.clone()
    }

    pub fn expecting(self, expectations: Vec<&'a str>) -> Self {
        {
            let mut test = self.test_arc.lock().unwrap();
            test.expectations = expectations;
        }
        self
    }

    pub fn with_patches(self, patches: Vec<guerrilla::PatchGuard>) -> Self {
        let converted_patches: Vec<Arc<Mutex<guerrilla::PatchGuard>>> = patches
            .into_iter()
            .map(|patch| Arc::new(Mutex::new(patch)))
            .collect();
        {
            let test = self.test_arc.lock().unwrap();
            test.patches().push(&test.name, converted_patches);
        }
        self
    }

    pub fn arc(self) -> Arc<Mutex<Test<'a>>> {
        self.test_arc
    }
}

impl Drop for Test<'_> {
    fn drop(&mut self) {
        let calls = self.spy().get(&self.name);
        self.patches().clear(&self.name);
        self.spy().clear(&self.name);
        assert_eq!(*calls, self.expectations);
    }
}
