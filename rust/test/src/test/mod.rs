pub mod patches;

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

    pub fn get_patch(&self, key: &str, index: usize) -> Arc<Mutex<PatchGuard>> {
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
        Test::testref(self, key)
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
    pub fn new(tests: &'a Tests<'a>, testid: &str) -> Self {
        Self {
            name: testid.to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        }
    }

    pub fn testref(tests: &'a Tests<'a>, testid: &str) -> TestRef<'a> {
        let test = Self::new(tests, testid);
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
    use crate::test::patches::Patch;
    use guerrilla::{patch0, patch1, patch2, patch3};
    use scopeguard::defer;
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
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("tests_clear", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("tests_clear");
            assert_eq!(calls, ["Test::drop", "Test::drop"]);
        };

        {
            let mut _tests = tests.tests.lock().unwrap();
            _tests.insert("SOMETEST".to_string(), Arc::new(Mutex::new(test.clone())));
        }

        tests.clear("SOMETEST");
        assert!(!tests.tests.lock().unwrap().contains_key("SOMETEST"));
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("tests_get", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("tests_get");
            assert_eq!(calls, ["Test::drop", "Test::drop"]);
        };

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
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("tests_get_bad", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("tests_get_bad");
            assert_eq!(calls, ["Test::drop"]);
        };

        {
            let mut _tests = tests.tests.lock().unwrap();
            _tests.insert("SOMETEST".to_string(), Arc::new(Mutex::new(test.clone())));
        }
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            tests.get("NOT A TEST");
        }));
        assert!(result.is_err());
        if let Err(panic) = result {
            if let Some(message) = panic.downcast_ref::<String>() {
                assert!(message.contains("Couldn't find test"));
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get_patch() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test_guard = patch0(Patch::noop, Patch::noop);
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
        drop(saved_guard);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_get_patch_bad() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test_guard = patch0(Patch::noop, Patch::noop);
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
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_push() {
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("tests_push", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("tests_push");
            assert_eq!(calls, ["Test::drop", "Test::drop"]);
        };

        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test = Test {
            name: "SOMETEST".to_string(),
            expectations: vec![],
            tests,
            fails: false,
            patch_index: None,
        };

        let test_arc = Arc::new(Mutex::new(test.clone()));
        tests.push("SOMETEST", test_arc.clone());

        let saved_test = tests
            .tests
            .lock()
            .unwrap()
            .get("SOMETEST")
            .cloned()
            .unwrap();
        let saved_test = saved_test.lock().unwrap();
        assert_eq!(test.name, saved_test.name);
        assert_eq!(test.fails, saved_test.fails);

        drop(test);
        drop(saved_test);
        tests.clear("SOMETEST");
        {
            let lock = tests.tests.lock().unwrap();
            drop(lock);
        }
        std::sync::atomic::fence(std::sync::atomic::Ordering::SeqCst);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_tests_test() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [
            patch1(drop_ptr, |_self| {
                Patch::drop_test("tests_test", &SPY, _self)
            }),
            patch2(Test::testref, |_self, key| {
                Patch::test_testref("tests_test", &SPY, _self, key)
            }),
        ];
        defer! {
            let calls = SPY.get("tests_test");
            assert_eq!(calls, ["Test::testref", "Test::drop"]);
            drop(guards);
        };

        let test_ref = tests.test("NEW TEST");
        assert_eq!(test_ref.test_arc.lock().unwrap().name, "NEW TEST");
        drop(test_ref);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_constructor() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let test_ref = Test::testref(tests, "NEW TEST");
        {
            let test = test_ref.test_arc.lock().unwrap();
            assert_eq!(test.name, "NEW TEST");
            assert!(std::ptr::eq(
                tests as *const Tests,
                test.tests as *const Tests
            ));
            assert!(!test.fails);
            assert_eq!(test.patch_index, None);

            let empty: Vec<&str> = vec![];
            assert_eq!(test.expectations, empty);
        }
        {
            let tests_map = tests.tests.lock().unwrap();
            assert!(
                tests_map.contains_key("NEW TEST"),
                "Test should be in the HashMap"
            );
        }
        let test_arc_addr = Arc::as_ptr(&test_ref.test_arc) as usize;
        let map_arc_addr = {
            let tests_map = tests.tests.lock().unwrap();
            let arc = tests_map
                .get("NEW TEST")
                .expect("Test should be in the HashMap");
            Arc::as_ptr(arc) as usize
        };
        assert_eq!(
            test_arc_addr, map_arc_addr,
            "Test Arc addresses should match"
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_get_patch() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: Some(23),
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [
            patch1(drop_ptr, |_self| {
                Patch::drop_test("test_get_patch", &SPY, _self)
            }),
            patch3(Tests::get_patch, |_self, name, idx| {
                Patch::test_get_patch("test_get_patch", &SPY, _self, name, idx)
            }),
        ];
        defer! {
            let calls = SPY.get("test_get_patch");
            assert_eq!(calls, ["Test::get_patch: \"SOMETEST\" 23", "Test::drop"]);
            drop(guards);
        };
        let patch = test.get_patch();
        drop(test);
        drop(patch);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_get_patch_bad() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [
            patch1(drop_ptr, |_self| {
                Patch::drop_test("test_get_patch_bad", &SPY, _self)
            }),
            patch3(Tests::get_patch, |_self, name, idx| {
                Patch::test_get_patch("test_get_patch_bad", &SPY, _self, name, idx)
            }),
        ];
        defer! {
            let calls = SPY.get("test_get_patch_bad");
            assert_eq!(calls, ["Test::drop"]);
            drop(guards);
        };

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            test.get_patch();
        }));
        assert!(result.is_err());
        if let Err(panic) = result {
            if let Some(message) = panic.downcast_ref::<String>() {
                assert!(message
                    .contains("You must call patch_index on the test before calling get_patch"));
            } else {
                panic!("Panic occurred but with unexpected type");
            }
        }
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_notify() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "NOTIFYTEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };

        let mut guards: Vec<Arc<Mutex<PatchGuard>>> = Vec::new();

        guards.push(Arc::new(Mutex::new(patch1(drop_ptr, |_self| {
            Patch::drop_test("test_notify", &SPY, _self)
        }))));

        defer! {
            drop(guards);
            let test_calls = TEST_SPY.get("NOTIFYTEST");
            assert_eq!(test_calls, ["BOOM"]);
            let calls = SPY.get("test_notify");
            assert_eq!(calls, ["Test::drop"]);
        };

        test.notify("BOOM");
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_patch_index() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let mut test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("test_patch_index", &SPY, _self)
        })];
        defer! {
            let calls = SPY.get("test_patch_index");
            assert_eq!(calls, ["Test::drop"]);
            drop(guards);
        };
        test.patch_index(23);
        assert_eq!(test.patch_index, Some(23));
        test.patch_index(23).patch_index(113);
        assert_eq!(test.patch_index, Some(113));
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_fail() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let mut test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("test_fail", &SPY, _self)
        })];
        defer! {
            let calls = SPY.get("test_fail");
            assert_eq!(calls, ["Test::drop"]);
            drop(guards);
        };

        let original_addr = &test as *const _ as usize;
        let returned_addr = test.fail() as *mut _ as usize;
        assert!(test.fails);
        assert_eq!(original_addr, returned_addr);

        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_patches() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("test_patches", &SPY, _self)
        })];
        defer! {
            let calls = SPY.get("test_patches");
            assert_eq!(calls, ["Test::drop"]);
            drop(guards);
        };
        assert!(std::ptr::eq(
            test.patches() as *const Lazy<Patches>,
            &TEST_PATCHES as *const Lazy<Patches>
        ));
        drop(test)
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_spy() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("test_spy", &SPY, _self)
        })];
        defer! {
            let calls = SPY.get("test_spy");
            assert_eq!(calls, ["Test::drop"]);
            drop(guards);
        };
        assert!(std::ptr::eq(
            test.spy() as *const Lazy<Spy>,
            &TEST_SPY as *const Lazy<Spy>
        ));
        drop(test)
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_test_drop() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let guards = [
            patch2(Spy::clear, |_self, name| {
                Patch::spy_clear("test_drop", &SPY, _self, name)
            }),
            patch2(Patches::clear, |_self, name| {
                Patch::patches_clear("test_drop", &SPY, _self, name)
            }),
        ];
        defer! {
            let calls = SPY.get("test_drop");
            assert_eq!(calls, ["Patches::clear: \"SOMETEST\"", "Spy::clear: \"SOMETEST\""]);
            drop(guards);
        };
        drop(test)
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_testref_drop() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "SOMETEST".to_string();
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [
            patch1(drop_ptr, |_self| {
                Patch::drop_test("testref_drop", &SPY, _self)
            }),
            patch2(Tests::clear, |_self, name| {
                Patch::tests_clear("testref_drop", &SPY, _self, name)
            }),
        ];
        defer! {
            drop(guards);
            let calls = SPY.get("testref_drop");
            assert_eq!(calls, ["Tests::clear: \"SOMETEST\"", "Test::drop", "Test::drop"]);
        };
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let test_arc = Arc::new(Mutex::new(test.clone()));
        let testref = TestRef { test_arc, tests };
        testref.drop();
        drop(test);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_testref_expecting() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "TESTREF_EXPECTING".to_string();
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("testref_expecting", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("testref_expecting");
            assert_eq!(calls, ["Test::drop", "Test::drop"]);
        };
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };

        let test_arc = Arc::new(Mutex::new(test.clone()));
        let testref = TestRef {
            test_arc: Arc::clone(&test_arc),
            tests,
        };
        testref.expecting(vec!["some", "test", "expectations"]);
        assert_eq!(
            test_arc.lock().unwrap().expectations,
            vec!["some", "test", "expectations"],
        );

        let testref2 = TestRef {
            test_arc: Arc::clone(&test_arc),
            tests,
        };
        testref2
            .expecting(vec!["some", "test", "expectations"])
            .expecting(vec!["other", "test", "expectations"]);
        assert_eq!(
            test_arc.lock().unwrap().expectations,
            vec!["other", "test", "expectations"],
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_testref_with_patches() {
        let tests = Box::leak(Box::new(Tests::new(&TEST_SPY, &TEST_PATCHES)));
        let name = "ANOTHERTEST".to_string();
        let drop_ptr = unsafe {
            std::mem::transmute::<*const (), for<'a, 'b> fn(&'a mut Test<'b>)>(
                core::ptr::drop_in_place::<Test> as *const (),
            )
        };
        let test = Test {
            name,
            tests,
            expectations: vec![],
            fails: false,
            patch_index: None,
        };
        let guards = [patch1(drop_ptr, |_self| {
            Patch::drop_test("testref_with_patches", &SPY, _self)
        })];
        defer! {
            drop(guards);
            let calls = SPY.get("testref_with_patches");
            assert_eq!(calls, ["Test::drop", "Test::drop"]);
        };

        let patches0 = vec![
            patch0(Patch::noop, Patch::noop),
            patch0(Patch::noop, Patch::noop),
            patch0(Patch::noop, Patch::noop),
        ];
        let ptrs: Vec<_> = patches0.iter().map(|guard| guard.ptr).collect();
        let patch_count = patches0.len();
        let test_arc = Arc::new(Mutex::new(test.clone()));
        let testref = TestRef {
            test_arc: Arc::clone(&test_arc),
            tests,
        };

        testref.with_patches(patches0);
        let test_bound = test_arc.lock().unwrap();
        let test_patches = test_bound.patches().patches.lock().unwrap();
        let stored_patches = test_patches.get("ANOTHERTEST");

        assert_eq!(stored_patches.unwrap().len(), patch_count);
        for (i, guard) in stored_patches.unwrap().iter().enumerate() {
            let result_ptr = guard.lock().unwrap().ptr;
            assert_eq!(
                result_ptr, ptrs[i],
                "PatchGuard ptr at index {} should match",
                i
            );
        }
        drop(test_patches);
        drop(test_bound);
        drop(test_arc);
        drop(test);
    }
}
