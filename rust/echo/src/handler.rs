use crate::{command::Command, config, mapping, response::Response};
use async_trait::async_trait;
use axum::{
    body::Bytes,
    extract::{Path, Query},
    http::{HeaderMap, Method},
    response,
    routing::any,
    Router,
};
use serde::{Deserialize, Serialize};
use toolshed_core as core;
use toolshed_runner::{self as runner, handler::Handler as _};

#[async_trait]
pub trait Provider: runner::handler::Handler + Clone
where
    Self: 'static,
{
    async fn handle(
        &self,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> response::Response;
    fn router(&self) -> Result<Router, Box<dyn std::error::Error + Send + Sync>>;

    fn route_path(&self) -> axum::routing::MethodRouter {
        let handler = self.clone();
        let closure = move |method: Method,
                            headers: HeaderMap,
                            Query(params): Query<mapping::OrderedMap>,
                            Path(path): Path<String>,
                            body: Bytes| {
            let handler = handler.clone();
            async move { handler.handle(method, headers, params, path, body).await }
        };
        any(closure)
    }

    #[inline(never)]
    fn route_root(&self) -> axum::routing::MethodRouter {
        let handler = self.clone();
        let closure = move |method: Method,
                            headers: HeaderMap,
                            Query(params): Query<mapping::OrderedMap>,
                            body: Bytes| {
            let handler = handler.clone();
            async move {
                handler
                    .handle(method, headers, params, "".to_string(), body)
                    .await
            }
        };
        any(closure)
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct EchoHandler {
    pub command: Command,
}

impl EchoHandler {}

impl runner::handler::Factory<Command> for EchoHandler {
    fn new(command: Command) -> Self {
        EchoHandler { command }
    }
}

impl runner::handler::Handler for EchoHandler {
    fn get_command(&self) -> Box<&dyn runner::command::Command> {
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
        let hostname = match self.config("hostname") {
            Some(core::Primitive::String(s)) => s,
            _ => config::Config::default_hostname(),
        };
        Response::new(hostname, method, headers, params, path, body).to_json()
    }

    fn router(&self) -> Result<Router, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Router::new()
            .route("/", self.route_root())
            .route("/{*path}", self.route_path()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{config, test::patch::Patch};
    use axum::Router;
    use bytes::Bytes;
    use guerrilla::{patch0, patch1, patch2, patch6};
    use http_body_util::Empty;
    use hyper::Request;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_test as ttest;
    use tower::ServiceExt as _;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    async fn _test_request(
        service: axum::routing::RouterIntoService<http_body_util::Empty<bytes::Bytes>>,
        path: &str,
        expected: &str,
    ) {
        let request = Request::builder()
            .uri(path)
            .body(Empty::<Bytes>::new())
            .unwrap();
        let response = service.oneshot(request).await.unwrap();
        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        assert_eq!(String::from_utf8_lossy(&body_bytes), expected.to_string());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_get_command() {
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler {
            command: command.clone(),
        };
        assert_eq!((*handler.get_command()).get_name(), command.name)
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handler_handle() {
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

        let test = TESTS.test("handler_handle")
            .expecting(vec![
                "Handler::config(true): \"hostname\"",
                "Config::default_hostname(true)",
                "Response::new(true): \"DEFAULT HOSTNAME\" TRACE {\"x-foo\": \"baz\", \"x-bar\": \"baz\"} OrderedMap({\"bar\": \"foo\"}) \"HOME\" b\"\"",
                "Response::to_json(true)",
            ])
            .with_patches(vec![
                patch2(
                    EchoHandler::config,
                    |_self, key| {
                        Patch::handler_config(
                            TESTS.get("handler_handle").unwrap(),
                            None,
                            _self,
                            key
                        )
                    },
                ),
                patch0(
                    config::Config::default_hostname,
                    || {
                        Patch::default_hostname(
                            TESTS.get("handler_handle").unwrap())
                    },
                ),
                patch6(
                    Response::new,
                    |hostname, method, headers, params, path, body| {
                        Patch::response_new(
                            TESTS.get("handler_handle").unwrap(),
                            hostname,
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
                            TESTS.get("handler_handle").unwrap(),
                            _self
                        )
                    },
                )
            ]);
        defer! {
            test.drop();
        }

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
    async fn test_handler_handle_hostname() {
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

        let test = TESTS.test("handler_handle")
            .expecting(vec![
                "Handler::config(true): \"hostname\"",
                "Response::new(true): \"HOSTNAME FROM CONFIG\" TRACE {\"x-foo\": \"baz\", \"x-bar\": \"baz\"} OrderedMap({\"bar\": \"foo\"}) \"HOME\" b\"\"",
                "Response::to_json(true)"
            ])
            .with_patches(vec![
                patch2(
                    EchoHandler::config,
                    |_self, key| {
                        Patch::handler_config(
                            TESTS.get("handler_handle").unwrap(),
                            Some(core::Primitive::String("HOSTNAME FROM CONFIG".to_string())),
                            _self,
                            key
                        )
                    },
                ),
                patch0(
                    config::Config::default_hostname,
                    || {
                        Patch::default_hostname(
                            TESTS.get("handler_handle").unwrap())
                    },
                ),
                patch6(
                    Response::new,
                    |hostname, method, headers, params, path, body| {
                        Patch::response_new(
                            TESTS.get("handler_handle").unwrap(),
                            hostname,
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
                            TESTS.get("handler_handle").unwrap(),
                            _self
                        )
                    },
                )
            ]);
        defer! {
            test.drop();
        }

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
    async fn test_handler_route_path() {
        let test = TESTS
            .test("handler_route_path")
            .expecting(vec![
                "EchoHandler::handle(true): GET {} OrderedMap({}) \"SOMEPATH\" b\"\"",
            ])
            .with_patches(vec![patch6(
                EchoHandler::handle,
                |_self, method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        TESTS.get("handler_route_path").unwrap(),
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

        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let router = Router::new().route("/{*path}", handler.route_path());
        let service = router.into_service();
        _test_request(service.clone(), "/SOMEPATH", "BOOM\n").await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handler_route_root() {
        let test = TESTS
            .test("handler_route_root")
            .expecting(vec![
                "EchoHandler::handle(true): GET {} OrderedMap({}) \"\" b\"\"",
            ])
            .with_patches(vec![patch6(
                EchoHandler::handle,
                |_self, method, headers, params, path, body| {
                    Box::pin(Patch::handler_handle(
                        TESTS.get("handler_route_root").unwrap(),
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

        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let router = Router::new().route("/", handler.route_root());
        let service = router.into_service();
        _test_request(service.clone(), "/", "BOOM\n").await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handler_router() {
        let test = TESTS
            .test("runner_router")
            .expecting(vec![
                "Router::new(true)",
                "Handler::route_root(true)",
                "Handler::route_path(true)",
            ])
            .with_patches(vec![
                patch0(Router::new, || {
                    let test = TESTS.get("runner_router").unwrap();
                    test.lock().unwrap().patch_index(0);
                    Patch::router_new(test)
                }),
                patch1(EchoHandler::route_path, |_self| {
                    Patch::handler_route_path(TESTS.get("runner_router").unwrap(), _self)
                }),
                patch1(EchoHandler::route_root, |_self| {
                    Patch::handler_route_root(TESTS.get("runner_router").unwrap(), _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let router = handler.router().unwrap();
        let service = router.into_service();

        _test_request(service.clone(), "/nowhere", "The future").await;
        _test_request(service.clone(), "/", "The future root").await;
        _test_request(service, "/some/path", "The future path").await;
    }
}
