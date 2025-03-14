pub mod patch;
pub mod spy;

pub use crate::{patch::Patches, spy::Spy};
use guerrilla::PatchGuard;
use once_cell::sync::Lazy;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

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

    pub fn get_patch<'b>(&self, key: &'b str) -> (&'b str, Arc<Mutex<PatchGuard>>) {
        let (testid, index) = key.split_once('/').map_or_else(
            move || {
                panic!(
                    "Invalid testid format, expected 'testid/index' but got: {}",
                    key
                )
            },
            |(testid_part, index_part)| {
                let index = index_part
                    .parse::<usize>()
                    .unwrap_or_else(|_| panic!("Invalid index format: {}", index_part));
                (testid_part, index)
            },
        );

        if let Some(patch_guard) = self
            .patches
            .get(testid)
            .and_then(|guards| guards.get(index).cloned())
        {
            (testid, patch_guard)
        } else {
            panic!("No PatchGuard found")
        }
    }

    pub fn get_patch2<'b>(&self, key: &'b str, index: usize) -> Arc<Mutex<PatchGuard>> {
        if let Some(patch_guard) = self
            .patches
            .get(key)
            .and_then(|guards| guards.get(index).cloned())
        {
            patch_guard
        } else {
            panic!("No PatchGuard found")
        }
    }

    pub fn test(&'a self, key: &str) -> TestRef<'a> {
        Test::new(self, key)
    }
}

#[derive(Clone)]
pub struct Test<'a> {
    pub name: String,
    expectations: Vec<&'a str>,
    tests: &'a Tests<'a>,
    pub fails: bool,
    pub patch_index: Option<usize>,
}

unsafe impl<'a> Send for Test<'a> {}
unsafe impl<'a> Sync for Test<'a> {}

impl<'a> Test<'a> {
    pub fn new(tests: &'a Tests<'a>, testid: &str) -> TestRef<'a> {
        let test = Self {
            name: testid.to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };
        let test_arc = Arc::new(Mutex::new(test));
        tests.push(testid, test_arc.clone());
        TestRef { test_arc, tests }
    }

    pub fn get_patch(&self) -> Arc<Mutex<PatchGuard>> {
        let idx = self
            .patch_index
            .expect("You must call patch_index on the test before calling get_patch");
        self.tests.get_patch2(&self.name, idx)
    }

    pub fn patch_index(&mut self, idx: usize) -> &mut Self {
        self.patch_index = Some(idx);
        self
    }

    pub fn fail(&mut self) -> &mut Self {
        self.fails = true;
        self
    }

    fn patches(&self) -> &Lazy<Patches> {
        self.tests.patches
    }

    pub fn spy(&self) -> &Lazy<Spy> {
        self.tests.spy
    }
}

pub struct TestRef<'a> {
    test_arc: Arc<Mutex<Test<'a>>>,
    tests: &'a Tests<'a>,
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

    pub fn with_patches(self, patches: Vec<PatchGuard>) -> Self {
        let converted_patches: Vec<Arc<Mutex<PatchGuard>>> = patches
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
        ::log::trace!("Test complete: {:?}", &self.name);
        let calls = self.spy().get(&self.name);
        self.patches().clear(&self.name);
        self.spy().clear(&self.name);
        assert_eq!(*calls, self.expectations);
    }
}
