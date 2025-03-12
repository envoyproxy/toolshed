use crate::{command::Command, mapping, response::Response};
use async_trait::async_trait;
use axum::{
    body::Bytes,
    extract::{Path, Query},
    http::{HeaderMap, Method},
    response,
};
use serde::{Deserialize, Serialize};
use toolshed_runner::{command, handler};

#[async_trait]
pub trait Provider: handler::Handler {
    async fn handle(
        &self,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_path(
        &self,
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> impl response::IntoResponse;

    async fn handle_root(
        &self,
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        body: Bytes,
    ) -> impl response::IntoResponse;
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct EchoHandler {
    pub command: Command,
}

impl EchoHandler {}

impl handler::Factory<Command> for EchoHandler {
    fn new(command: Command) -> Self {
        EchoHandler { command }
    }
}

impl handler::Handler for EchoHandler {
    fn get_command(&self) -> Box<&dyn command::Command> {
        Box::new(&self.command)
    }
}

#[async_trait]
impl Provider for EchoHandler {
    async fn handle(
        &self,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> response::Response {
        Response::new(method, headers, params, path, body).to_json()
    }

    async fn handle_path(
        &self,
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        Path(path): Path<String>,
        body: Bytes,
    ) -> response::Response {
        self.handle(method, headers, params, path, body).await
    }

    async fn handle_root(
        &self,
        method: Method,
        headers: HeaderMap,
        Query(params): Query<mapping::OrderedMap>,
        body: Bytes,
    ) -> response::Response {
        self.handle(method, headers, params, "".to_string(), body)
            .await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{config, test::patch::Patch};
    use bytes::Bytes;
    use guerrilla::{patch1, patch5, patch6};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_runner::test::{patch::Patches, spy::Spy, Tests};

    static PATCHES: Lazy<Patches> = Lazy::new(Patches::new);
    static SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TESTS: Lazy<Tests> = Lazy::new(|| Tests::new(&SPY, &PATCHES));

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle() {
        let test = TESTS.test("handle")
            .expecting(vec![
                "EchoHandler::handle(true): TRACE {\"x-foo\": \"baz\", \"x-bar\": \"baz\"} OrderedMap({\"bar\": \"foo\"}) \"HOME\" b\"\"", "EchoHandler::handle(true)"])
            .with_patches(vec![
                patch5(
                    Response::new,
                    |method, headers, params, path, body| {
                        Patch::response_new(
                            TESTS.get("handle").unwrap(),
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
                            TESTS.get("handle").unwrap(),
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
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };

        assert_eq!(
            format!(
                "{:?}",
                handler.handle(method, headers, params, "HOME".to_string(), body).await
            ),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        )
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle_root() {
        let test = TESTS.test("handle_root")
            .expecting(vec![
                "EchoHandler::handle(true): PATCH {\"x-foo\": \"foo\", \"x-bar\": \"bar\"} OrderedMap({\"bar\": \"foo\"}) \"\" b\"DIFF\""])
            .with_patches(vec![patch6(
                EchoHandler::handle,
                |_self, method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        TESTS.get("handle_root").unwrap(),
                        _self,
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

        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };

        assert_eq!(
            format!(
                "{:?}",
                handler.handle_root(method, headers, Query(params), body).await
            ),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        )
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handle_path() {
        let test = TESTS.test("handle_path")
            .expecting(vec![
                "EchoHandler::handle(true): POST {\"x-foo\": \"bar\", \"x-bar\": \"foo\"} OrderedMap({\"bar\": \"foo\"}) \"NOWHERE\" b\"DIFF\""])
            .with_patches(vec![patch6(
                EchoHandler::handle,
                |_self, method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        TESTS.get("handle_path").unwrap(),
                        _self,
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

        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };

        assert_eq!(
            format!(
                "{:?}",
                handler.handle_path(
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
