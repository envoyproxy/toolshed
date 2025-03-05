use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
pub struct Response {
    pub method: String,
    pub headers: HashMap<String, String>,
    pub query_params: HashMap<String, String>,
    pub body: String,
    pub path: String,
}
