use std::error::Error;

pub type EmptyResult<E = Box<dyn Error + Send + Sync>> = Result<(), E>;
