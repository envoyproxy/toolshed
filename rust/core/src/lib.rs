mod cast;
mod comprehension;
pub mod mapping;
mod result;

#[derive(Debug, Clone, PartialEq)]
pub enum Primitive {
    Bool(bool),
    F64(f64),
    I32(i32),
    I64(i64),
    U32(u32),
    U64(u64),
    String(String),
}

pub use cast::downcast;
pub use result::EmptyResult;
