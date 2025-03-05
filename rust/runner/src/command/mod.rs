use crate::config;
use std::fmt;

pub trait Factory<T, C>: Send + Sync
where
    T: Command + Sized,
    C: config::Provider + Sized,
{
    fn new(config: C, name: Option<String>) -> Self;
}

pub trait Command: fmt::Debug + Send + Sync {
    fn get_config(&self) -> Box<&dyn config::Provider>;
    fn get_name(&self) -> &str;
}
