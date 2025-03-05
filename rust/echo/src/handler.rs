use crate::response::Response;
use async_trait::async_trait;
use axum::{
    body::{Body, Bytes},
    extract::{Path, Query},
    http::{HeaderMap, Method},
    response,
};
use std::collections::HashMap;

#[async_trait]
pub trait Handler {
    async fn handle(
        method: Method,
        headers: HeaderMap,
        params: HashMap<String, String>,
        path: String,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_path(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<HashMap<String, String>>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_root(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<HashMap<String, String>>,
        body: Bytes,
    ) -> impl response::IntoResponse;
}

pub struct EchoHandler {}

#[async_trait]
impl Handler for EchoHandler {
    async fn handle(
        method: Method,
        headers: HeaderMap,
        params: HashMap<String, String>,
        path: String,
        body: Bytes,
    ) -> impl response::IntoResponse {
        let body_str = String::from_utf8_lossy(&body);
        let echo_response = Response {
            method: method.to_string(),
            headers: headers
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                .collect(),
            query_params: params,
            body: body_str.to_string(),
            path,
        };
        let pretty_json = serde_json::to_string_pretty(&echo_response).unwrap_or_default();
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", pretty_json)))
            .unwrap()
    }

    async fn handle_path(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<HashMap<String, String>>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> impl response::IntoResponse {
        Self::handle(method, headers, params, path, body).await
    }

    async fn handle_root(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<HashMap<String, String>>,
        body: Bytes,
    ) -> impl response::IntoResponse {
        Self::handle(method, headers, params, "".to_string(), body).await
    }
}
