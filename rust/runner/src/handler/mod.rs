use crate::command::Command;
use std::fmt;

pub trait Factory<T>: Send + Sync
where
    T: Command + Sized,
{
    fn new(command: T) -> Self;
}

pub trait Handler: fmt::Debug + Send + Sync {
    fn get_command(&self) -> Box<&dyn Command>;
}
