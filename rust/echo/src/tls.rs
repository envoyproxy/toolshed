use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    pub cert: String,
    pub key: String,
}

impl Config {
    pub fn new(cert: String, key: String) -> Self {
        Self { cert, key }
    }
}
