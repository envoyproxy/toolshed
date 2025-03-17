use as_any::AsAny;
use std::{any, io};

pub fn downcast<T: 'static>(thing: &dyn AsAny) -> Result<&T, io::Error> {
    match thing.as_any().downcast_ref::<T>() {
        Some(thing) => Ok(thing),
        _ => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Failed to downcast to {}", any::type_name::<T>()),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct AnyThing {
        value: i32,
    }

    impl AnyThing {
        fn new(value: i32) -> Self {
            AnyThing { value }
        }
    }

    #[test]
    fn test_successful_downcast() {
        let my_struct = AnyThing::new(42);
        let result: Result<&AnyThing, io::Error> = downcast(&my_struct);
        assert!(result.is_ok());
        let my_struct_ref = result.unwrap();
        assert_eq!(my_struct_ref.value, 42);
    }

    #[test]
    fn test_failed_downcast() {
        let my_struct = AnyThing::new(42);
        let result: Result<&String, io::Error> = downcast(&my_struct);
        assert!(result.is_err());
        let error = result.unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::InvalidData);
    }
}
