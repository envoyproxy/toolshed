use crate::{mapping, response::Response};
use async_trait::async_trait;
use axum::{
    body::Bytes,
    extract::{Path, Query},
    http::{HeaderMap, Method},
    response,
};

#[async_trait]
pub trait Handler {
    async fn handle(
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_path(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_root(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        body: Bytes,
    ) -> impl response::IntoResponse;
}

pub struct EchoHandler {}

#[async_trait]
impl Handler for EchoHandler {
    async fn handle(
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> response::Response {
        Response::new(method, headers, params, path, body).to_json()
    }

    async fn handle_path(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> response::Response {
        Self::handle(method, headers, params, path, body).await
    }

    async fn handle_root(
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        body: Bytes,
    ) -> response::Response {
        Self::handle(method, headers, params, "".to_string(), body).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::patch::Patch;
    use bytes::Bytes;
    use guerrilla::{patch1, patch5};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_runner::test::{Test, Tests, patch::Patches, spy::Spy};

    static PATCHES: Lazy<Patches> = Lazy::new(Patches::new);
    static SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TESTS: Lazy<Tests> = Lazy::new(|| Tests::new(&SPY, &PATCHES));

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle() {
        let test = Test::new(&TESTS, "handle")
            .expecting(vec![
                "EchoHandler::handle(true): TRACE {\"x-foo\": \"baz\", \"x-bar\": \"baz\"} OrderedMap({\"bar\": \"foo\"}) \"HOME\" b\"\"", "EchoHandler::handle(true)"])
            .with_patches(vec![
                patch5(
                    Response::new,
                    |method, headers, params, path, body| {
                        Patch::response_new(
                            &TESTS,
                            "handle",
                            true,
                            method,
                            headers,
                            params,
                            path,
                            body,
                        )
                    },
                ),
                patch1(
                    Response::to_json,
                    |_self| {
                        Patch::response_to_json(
                            &TESTS,
                            "handle",
                            true,
                            _self
                        )
                    },
                )
            ]);
        defer! {
            test.drop();
        }

        let method = Method::TRACE;
        let mut headers = HeaderMap::new();
        headers.insert("X-FOO", "baz".parse().unwrap());
        headers.insert("X-BAR", "baz".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("".to_string());
        assert_eq!(
            format!(
                "{:?}",
                EchoHandler::handle(method, headers, params, "HOME".to_string(), body).await
            ),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        )
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle_root() {
        let test = Test::new(&TESTS, "handle_root")
            .expecting(vec![
                "EchoHandler::handle(true): PATCH {\"x-foo\": \"foo\", \"x-bar\": \"bar\"} OrderedMap({\"bar\": \"foo\"}) \"\" b\"DIFF\""])
            .with_patches(vec![patch5(
                EchoHandler::handle,
                |method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        &TESTS,
                        "handle_root",
                        true,
                        method,
                        headers,
                        params,
                        path,
                        body,
                    ))
                },
            )]);
        defer! {
            test.drop();
        }

        let method = Method::PATCH;
        let mut headers = HeaderMap::new();
        headers.insert("X-FOO", "foo".parse().unwrap());
        headers.insert("X-BAR", "bar".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("DIFF".to_string());
        assert_eq!(
            format!(
                "{:?}",
                EchoHandler::handle_root(method, headers, Query(params), body).await
            ),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        )
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle_path() {
        let test = Test::new(&TESTS, "handle_path")
            .expecting(vec![
                "EchoHandler::handle(true): POST {\"x-foo\": \"bar\", \"x-bar\": \"foo\"} OrderedMap({\"bar\": \"foo\"}) \"NOWHERE\" b\"DIFF\""])
            .with_patches(vec![patch5(
                EchoHandler::handle,
                |method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        &TESTS,
                        "handle_path",
                        true,
                        method,
                        headers,
                        params,
                        path,
                        body,
                    ))
                },
            )]);
        defer! {
            test.drop();
        }

        let method = Method::POST;
        let mut headers = HeaderMap::new();
        headers.insert("X-FOO", "bar".parse().unwrap());
        headers.insert("X-BAR", "foo".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("DIFF".to_string());
        assert_eq!(
            format!(
                "{:?}",
                EchoHandler::handle_path(
                    method,
                    headers,
                    Query(params),
                    Path("NOWHERE".to_string()),
                    body,
                )
                .await
            ),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        )
    }
}
