pub use crate::{patch::Patches, spy::Spy};
use guerrilla::PatchGuard;
use once_cell::sync::Lazy;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

pub struct Tests<'a> {
    pub tests: Mutex<HashMap<String, Arc<Mutex<Test<'a>>>>>,
    pub spy: &'a Lazy<Spy>,
    pub patches: &'a Lazy<Patches>,
}

impl<'a> Tests<'a> {
    pub fn new(spy: &'a Lazy<Spy>, patches: &'a Lazy<Patches>) -> Self {
        Self {
            tests: Mutex::new(HashMap::new()),
            spy,
            patches,
        }
    }

    pub fn clear(&self, key: &str) {
        let mut tests = self.tests.lock().unwrap();
        tests.remove(key).unwrap();
    }

    pub fn get(&self, key: &str) -> Arc<Mutex<Test<'a>>> {
        self.tests
            .lock()
            .unwrap()
            .get(key)
            .cloned()
            .unwrap_or_else(|| panic!("Couldn't find test ({:?}), did you register it?", key))
    }

    pub fn get_patch<'b>(&self, key: &'b str, index: usize) -> Arc<Mutex<PatchGuard>> {
        self.patches
            .get(key)
            .and_then(|guards| guards.get(index).cloned())
            .unwrap_or_else(|| panic!("No patchguard found for {:?}/{:?}", key, index))
    }

    pub fn push(&self, key: &str, test: Arc<Mutex<Test<'a>>>) {
        let mut tests = self.tests.lock().unwrap();
        tests.insert(key.to_string(), test);
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
        self.tests.get_patch(&self.name, idx)
    }

    pub fn notify(&self, msg: &str) {
        self.tests.spy.push(&self.name, msg);
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

#[cfg(test)]
mod tests {
    use super::*;
    use guerrilla::{patch1, patch2, patch3};
    use serial_test::serial;

    static SPY: Lazy<Spy> = Lazy::new(Spy::new);

    static TEST_SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TEST_PATCHES: Lazy<Patches> = Lazy::new(Patches::new);

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_constructor() {
        let tests = Tests::new(&TEST_SPY, &TEST_PATCHES);
        assert!(std::ptr::eq(
            tests.spy as *const Lazy<Spy>,
            &TEST_SPY as *const Lazy<Spy>
        ));
        assert!(std::ptr::eq(
            tests.patches as *const Lazy<Patches>,
            &TEST_PATCHES as *const Lazy<Patches>
        ));
    }

    fn _drop_test(testid: &str, _test: &mut Test) {
        SPY.push(testid, "Test::drop");
    }

    fn _new_test<'a>(testid: &'a str, _self: &'a Tests<'a>, key: &'a str) -> TestRef<'a> {
        SPY.push(testid, "Test::new");
        let test = Test {
            name: key.to_string(),
            expectations: vec![],
            tests: _self,
            fails: false,
            patch_index: None,
        };

        let test_arc = Arc::new(Mutex::new(test));
        TestRef {
            test_arc,
            tests: _self,
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_clear() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };

        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };
        let guard = patch1(drop_ptr, |_self| _drop_test("tests_clear", _self));
        {
            let mut _tests = tests.tests.lock().unwrap();
            _tests.insert("SOMETEST".to_string(), Arc::new(Mutex::new(test.clone())));
        }

        tests.clear("SOMETEST");
        assert!(!tests.tests.lock().unwrap().contains_key("SOMETEST"));

        drop(test);
        let calls = SPY.get("tests_clear");
        assert_eq!(calls, ["Test::drop", "Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get() {
        // let tests = Tests::new(&TEST_SPY, &TEST_PATCHES);
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };

        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };

        let guard = patch1(drop_ptr, |_self| _drop_test("tests_get", _self));

        {
            let mut _tests = tests.tests.lock().unwrap();
            _tests.insert("SOMETEST".to_string(), Arc::new(Mutex::new(test.clone())));
        }

        let saved_test = tests.get("SOMETEST");
        let saved_test = saved_test.lock().unwrap();
        assert_eq!(test.name, saved_test.clone().name);
        assert_eq!(test.fails, saved_test.fails);

        drop(test);
        drop(saved_test);
        // drop(saved_test);
        let calls = SPY.get("tests_get");
        assert_eq!(calls, ["Test::drop", "Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get_bad() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };

        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };

        let guard = patch1(drop_ptr, |_self| _drop_test("tests_get_bad", _self));

        {
            let mut _tests = tests.tests.lock().unwrap();
            _tests.insert("SOMETEST".to_string(), Arc::new(Mutex::new(test.clone())));
        }

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tests.get("NOT A TEST");
        }));

        // Verify that it panicked as expected
        assert!(result.is_err());

        if let Err(panic) = result {
            if let Some(message) = panic.downcast_ref::<String>() {
                assert!(message.contains("Couldn't find test"));
            } else if let Some(message) = panic.downcast_ref::<&str>() {
                assert!(message.contains("Couldn't find test"));
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }

        drop(test);
        let calls = SPY.get("tests_get_bad");
        assert_eq!(calls, ["Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get_patch() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };
        let guard = patch1(drop_ptr, |_self| _drop_test("tests_get_patch", _self));

        let test_guard = patch3(Tests::push, |_self, key, test| ());
        let test_guard_ptr = test_guard.ptr;
        {
            let mut _patches = tests.patches.patches.lock().unwrap();
            _patches.insert(
                "SOMEPATCH".to_string(),
                vec![Arc::new(Mutex::new(test_guard))],
            );
        }

        let saved_guard = tests.get_patch("SOMEPATCH", 0);
        let saved_guard = saved_guard.lock().unwrap();
        assert_eq!(test_guard_ptr, saved_guard.ptr);

        drop(test);
        let calls = SPY.get("tests_get_patch");
        assert_eq!(calls, ["Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get_patch_bad() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };
        let guard = patch1(drop_ptr, |_self| _drop_test("tests_get_patch_bad", _self));

        let test_guard = patch3(Tests::push, |_self, key, test| ());
        let test_guard_ptr = test_guard.ptr;
        {
            let mut _patches = tests.patches.patches.lock().unwrap();
            _patches.insert(
                "SOMEPATCH".to_string(),
                vec![Arc::new(Mutex::new(test_guard))],
            );
        }

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tests.get_patch("NOT A PATCH", 0);
        }));
        assert!(result.is_err());
        if let Err(panic) = result {
            if let Some(message) = panic.downcast_ref::<String>() {
                assert!(message.contains("No patchguard found for"));
            } else if let Some(message) = panic.downcast_ref::<&str>() {
                assert!(message.contains("No patchguard found for"));
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tests.get_patch("SOMEPATCH", 23);
        }));
        assert!(result.is_err());
        if let Err(panic) = result {
            if let Some(message) = panic.downcast_ref::<String>() {
                assert!(message.contains("No patchguard found for"));
            } else if let Some(message) = panic.downcast_ref::<&str>() {
                assert!(message.contains("No patchguard found for"));
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }

        drop(test);
        let calls = SPY.get("tests_get_patch_bad");
        assert_eq!(calls, ["Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_push() {
        // let tests = Tests::new(&TEST_SPY, &TEST_PATCHES);
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };

        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };

        let guard = patch1(drop_ptr, |_self| _drop_test("tests_push", _self));

        tests.push("SOMETEST", Arc::new(Mutex::new(test.clone())));
        let saved_test = tests
            .tests
            .lock()
            .unwrap()
            .get("SOMETEST")
            .cloned()
            .unwrap();
        let saved_test = saved_test.lock().unwrap();

        assert_eq!(test.name, saved_test.clone().name);
        assert_eq!(test.fails, saved_test.fails);

        drop(test);
        drop(saved_test);
        let calls = SPY.get("tests_push");
        assert_eq!(calls, ["Test::drop", "Test::drop"]);
        drop(guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_test() {
        // let tests = Tests::new(&TEST_SPY, &TEST_PATCHES);
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));

        let drop_ptr = unsafe {
            std::mem::transmute::<_, fn(&mut Test)>(core::ptr::drop_in_place::<Test> as *const ())
        };

        let guards = [
            patch1(drop_ptr, |_self| _drop_test("tests_test", _self)),
            patch2(Test::new, |_self, key| _new_test("tests_test", _self, key)),
        ];

        let test_ref = tests.test("NEW TEST");
        assert_eq!(test_ref.test_arc.lock().unwrap().name, "NEW TEST");

        drop(test_ref);
        let calls = SPY.get("tests_test");
        assert_eq!(calls, ["Test::new", "Test::drop"]);
        drop(guards);
    }
}
