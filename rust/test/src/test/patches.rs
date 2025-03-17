use crate::{test::TestRef, Patches, Spy, Test, Tests};
use guerrilla::{disable_patch, patch0, PatchGuard};
use once_cell::sync::Lazy;
use std::sync::{Arc, Mutex};

pub struct Patch {}

impl Patch {
    pub fn drop_test(testid: &str, spy: &Spy, _self: &mut Test) {
        spy.push(testid, "Test::drop");
    }

    pub fn new_test<'a>(
        testid: &'a str,
        spy: &Spy,
        _self: &'a Tests<'a>,
        key: &'a str,
    ) -> TestRef<'a> {
        spy.push(testid, "Test::new");
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

    pub fn noop() {
        println!("NOOP");
        println!("NOOP");
    }

    pub fn patches_clear(testid: &str, spy: &Spy, _self: &Patches, key: &str) {
        spy.push(testid, &format!("Patches::clear: {:?}", key));
    }

    pub fn spy_clear(testid: &str, spy: &Spy, _self: &Spy, key: &str) {
        spy.push(testid, &format!("Spy::clear: {:?}", key));
    }

    pub fn spy_push(
        testid: &str,
        spy: &Spy,
        spy_patch: &Lazy<Mutex<Option<Arc<Mutex<PatchGuard>>>>>,
        _self: &Spy,
        key: &str,
        value: &str,
    ) {
        let patch = spy_patch.lock().unwrap();
        if let Some(patch) = &*patch {
            disable_patch!(
                patch.lock().unwrap(),
                spy.push(testid, &format!("Spy::push: {:?} {:?}", key, value))
            );
        }
    }

    pub fn test_get_patch(
        testid: &str,
        spy: &Spy,
        _self: &Tests,
        key: &str,
        index: usize,
    ) -> Arc<Mutex<PatchGuard>> {
        spy.push(testid, &format!("Test::get_patch: {:?} {:?}", key, index));
        Arc::new(Mutex::new(patch0(Self::noop, Self::noop)))
    }

    pub fn tests_clear(testid: &str, spy: &Spy, _self: &Tests, key: &str) {
        spy.push(testid, &format!("Tests::clear: {:?}", key));
    }
}
