use crate::{command::Command, config, mapping, response::Response};
use async_trait::async_trait;
use axum::{
    body::{to_bytes, Bytes},
    extract::{Request, State},
    http::HeaderMap,
    response,
    routing::any,
    Router,
};
use hyper::header::HeaderValue;
use serde::{Deserialize, Serialize};
use toolshed_core as core;
use toolshed_runner::{self as runner, handler::Handler as _};

macro_rules! route {
    ($method:ident, $handler:expr, $($extractor:ident $type:ty),*) => {
        $method(async move |$($extractor: $type),*| $handler($($extractor),*).await)
    };
}

#[async_trait]
pub trait Provider: runner::handler::Handler + Clone
where
    Self: 'static,
{
    async fn handle(State(state): State<EchoState>, request: Request) -> response::Response;
    async fn body(request: Request) -> Bytes;
    fn headers(request: &Request) -> HeaderMap;
    fn host(request: &Request) -> String;
    fn params(request: &Request) -> mapping::OrderedMap;
    fn path(request: &Request) -> String;
    fn scheme(request: &Request) -> String;

    fn handler_config(&self) -> EchoHandlerConfig;
    fn router(&self) -> Result<Router, Box<dyn std::error::Error + Send + Sync>>;
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
    async fn handle(State(state): State<EchoState>, request: Request) -> response::Response {
        Response::new(
            state.config.hostname.to_string(),
            request.method().clone(),
            Self::scheme(&request),
            Self::headers(&request),
            Self::params(&request),
            Self::path(&request),
            Self::body(request).await,
        )
        .to_json()
    }

    async fn body(request: Request) -> Bytes {
        to_bytes(request.into_body(), 1024 * 1024)
            .await
            .unwrap_or_else(|_| Bytes::new())
    }

    fn headers(request: &Request) -> HeaderMap {
        let mut headers = request.headers().clone();
        match headers.get("host") {
            Some(_) => headers,
            None => {
                if let Ok(host) = HeaderValue::from_str(&Self::host(request)) {
                    headers.insert("host", host);
                }
                headers
            }
        }
    }

    fn host(request: &Request) -> String {
        request
            .headers()
            .get("host")
            .and_then(|h| h.to_str().ok())
            .or_else(|| request.uri().authority().map(|a| a.as_str()))
            .map(|host| host.to_string())
            .unwrap_or_else(|| "unknown".to_string())
    }

    fn params(request: &Request) -> mapping::OrderedMap {
        request
            .uri()
            .query()
            .filter(|q| !q.is_empty())
            .and_then(|q| serde_urlencoded::from_str::<mapping::OrderedMap>(q).ok())
            .unwrap_or_default()
    }

    fn path(request: &Request) -> String {
        let path = request.uri().path();
        if !path.is_empty() {
            path.into()
        } else {
            "/".into()
        }
    }

    fn scheme(request: &Request) -> String {
        request.uri().scheme_str().unwrap_or("http").to_string()
    }

    // Selfish fun
    fn handler_config(&self) -> EchoHandlerConfig {
        let hostname = match self.config("hostname") {
            Some(core::Primitive::String(s)) => s,
            _ => config::Config::default_hostname(),
        };
        EchoHandlerConfig::new(hostname)
    }

    fn router(&self) -> Result<Router, Box<dyn std::error::Error + Send + Sync>> {
        let config = self.handler_config();
        let state = EchoState::new(config);
        Ok(Router::new()
            .route(
                "/",
                route!(any, Self::handle, state State<EchoState>, request Request),
            )
            .route(
                "/{*path}",
                route!(any, Self::handle, state State<EchoState>,  request Request),
            )
            .with_state(state))
    }
}

#[derive(Clone, Debug)]
pub struct EchoHandlerConfig {
    pub hostname: String,
}

impl EchoHandlerConfig {
    fn new(hostname: String) -> Self {
        EchoHandlerConfig { hostname }
    }
}

#[derive(Clone, Debug)]
pub struct EchoState {
    pub config: EchoHandlerConfig,
}

impl EchoState {
    fn new(config: EchoHandlerConfig) -> Self {
        EchoState { config }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{config, test::patch::Patch};
    use axum::{
        body::Body,
        http::{Method, Request as HttpRequest, Uri},
    };
    use guerrilla::{disable_patch, patch0, patch1, patch2, patch7};
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

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_handler_config() {
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let test = TESTS
            .test("handler_handler_config")
            .expecting(vec![
                "Handler::config(true): \"hostname\"",
                "EchoHandlerConfig::new(true): SOMEHOSTNAME",
            ])
            .with_patches(vec![
                patch2(EchoHandler::config, |_self, key| {
                    Patch::handler_config(
                        TESTS.get("handler_handler_config"),
                        Some(core::Primitive::String("SOMEHOSTNAME".to_string())),
                        _self,
                        key,
                    )
                }),
                patch0(config::Config::default_hostname, || {
                    Patch::default_hostname(TESTS.get("handler_handler_config"))
                }),
                patch1(EchoHandlerConfig::new, |hostname| {
                    Patch::handlerconfig_new(TESTS.get("handler_handler_config"), hostname)
                }),
            ]);
        defer! {
            test.drop();
        }
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler {
            command: command.clone(),
        };
        let handler_config = handler.handler_config();
        assert_eq!(handler_config.hostname, "SOMEHOSTNAME");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_handler_config_default() {
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let test = TESTS
            .test("handler_handler_config")
            .expecting(vec![
                "Handler::config(true): \"hostname\"",
                "Config::default_hostname(true)",
                "EchoHandlerConfig::new(true): DEFAULT HOSTNAME",
            ])
            .with_patches(vec![
                patch2(EchoHandler::config, |_self, key| {
                    Patch::handler_config(TESTS.get("handler_handler_config"), None, _self, key)
                }),
                patch0(config::Config::default_hostname, || {
                    Patch::default_hostname(TESTS.get("handler_handler_config"))
                }),
                patch1(EchoHandlerConfig::new, |hostname| {
                    Patch::handlerconfig_new(TESTS.get("handler_handler_config"), hostname)
                }),
            ]);
        defer! {
            test.drop();
        }
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler {
            command: command.clone(),
        };
        let handler_config = handler.handler_config();
        assert_eq!(handler_config.hostname, "DEFAULT HOSTNAME");
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_handler_router() {
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let test = TESTS
            .test("handler_router")
            .expecting(vec![
                "Handler::handler_config(true)",
                "EchoState::new(true): EchoHandlerConfig { hostname: \"HANDLERHOSTNAME\" }",
                "EchoHandler::handle(true): State(EchoState { config: EchoHandlerConfig { hostname: \"HANDLERHOSTNAME\" } }) Request { method: GET, uri: /nowhere, version: HTTP/1.1, headers: {}, body: Body(UnsyncBoxBody) }",
                "EchoHandler::handle(true): State(EchoState { config: EchoHandlerConfig { hostname: \"HANDLERHOSTNAME\" } }) Request { method: GET, uri: /, version: HTTP/1.1, headers: {}, body: Body(UnsyncBoxBody) }",
                "EchoHandler::handle(true): State(EchoState { config: EchoHandlerConfig { hostname: \"HANDLERHOSTNAME\" } }) Request { method: GET, uri: /some/path, version: HTTP/1.1, headers: {}, body: Body(UnsyncBoxBody) }"

            ])
            .with_patches(vec![
                patch0(Router::new, || {
                    let test = TESTS.get("handler_router");
                    test.lock().unwrap().patch_index(0);
                    Patch::router_new(test)
                }),
                patch1(EchoHandler::handler_config, |_self| {
                    Patch::handler_handler_config(
                        TESTS.get("handler_router"),
                        _self,
                    )
                }),
                patch1(EchoState::new, |config| {
                    Patch::echostate_new(
                        TESTS.get("handler_router"),
                        config,
                    )
                }),
                patch2(EchoHandler::handle, |state, request| {
                    Box::pin(Patch::handler_handle(
                        TESTS.get("handler_router"),
                        state,
                        request,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let router = handler.router().unwrap();
        let service = router.into_service();

        // TODO: test with_state
        _test_request(service.clone(), "/nowhere", "BOOM\n").await;
        _test_request(service.clone(), "/", "BOOM\n").await;
        _test_request(service, "/some/path", "BOOM\n").await;
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_handler_handle() {
        let test = TESTS
            .test("handler_handle")
            .expecting(vec![
                "Handler::scheme(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "Handler::headers(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "Handler::params(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "Handler::path(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "Handler::host(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "Response::new(true): \"OTHERHOSTNAME\" PATCH {\"x-foo\": \"bar\"} OrderedMap({\"a0\": \"A\", \"b0\": \"B\"}) \"SOMEPATH\" b\"SOMEBOODY\"",

                "Response::to_json(true)"
            ])
            .with_patches(vec![
                patch7(
                    Response::new,
                    |hostname, method, scheme, headers, params, path, body| {
                        Patch::response_new(
                            TESTS.get("handler_handle"),
                            hostname,
                            method,
                            scheme,
                            headers,
                            params,
                            path,
                            body,
                        )
                    },
                ),
                patch1(Response::to_json, |_self| {
                    Patch::response_to_json(TESTS.get("handler_handle"), _self)
                }),
                patch1(EchoHandler::body, |request| {
                    Box::pin(Patch::handler_body(TESTS.get("handler_handle"), request))
                }),
                patch1(EchoHandler::headers, |request| {
                    Patch::handler_headers(TESTS.get("handler_handle"), request)
                }),
                patch1(EchoHandler::params, |request| {
                    Patch::handler_params(TESTS.get("handler_handle"), request)
                }),
                patch1(EchoHandler::path, |request| {
                    Patch::handler_path(TESTS.get("handler_handle"), request)
                }),
                patch1(EchoHandler::scheme, |request| {
                    Patch::handler_scheme(TESTS.get("handler_handle"), request)
                }),
            ]);
        defer! {
            test.drop();
        }

        let hostname = "OTHERHOSTNAME".to_string();
        let handler_config = EchoHandlerConfig { hostname };
        let echo_state = EchoState {
            config: handler_config,
        };
        let state = State(echo_state);
        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .uri(Uri::from_static("REQUESTPATH"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let response = EchoHandler::handle(state, request).await;
        let bytes = to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
        assert_eq!(
            "{\"foo\": \"bar\"}\n".to_string(),
            String::from_utf8(bytes.to_vec()).unwrap()
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_headers() {
        let test = TESTS
            .test("handler_headers")
            .expecting(vec![
                "Handler::host(true): Request { method: PATCH, uri: REQUESTPATH, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }",
                "HeaderValue::from_str(true): \"SOMEHOST\""
            ])
            .with_patches(vec![
                patch1(EchoHandler::host, |request| {
                    Patch::handler_host(TESTS.get("handler_headers"), request)
                }),
                patch1(HeaderValue::from_str, |string| {
                    Patch::headervalue_from_str(TESTS.get("handler_headers"), string)
                }),
            ]);
        defer! {
            test.drop();
        }

        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .uri(Uri::from_static("REQUESTPATH"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let headers = EchoHandler::headers(&request);
        assert_eq!(headers.get("host").unwrap(), "SOMEHEADERVALUE");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_headers_host_exists() {
        let test = TESTS
            .test("handler_headers_host_exists")
            .expecting(vec![])
            .with_patches(vec![
                patch1(EchoHandler::host, |request| {
                    Patch::handler_host(TESTS.get("handler_headers_host_exists"), request)
                }),
                patch1(HeaderValue::from_str, |string| {
                    Patch::headervalue_from_str(TESTS.get("handler_headers_host_exists"), string)
                }),
            ]);
        defer! {
            test.drop();
        }

        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .uri(Uri::from_static("REQUESTPATH"))
            .header("Content-Type", "application/json")
            .header("Host", "foo.com")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let headers = EchoHandler::headers(&request);
        assert_eq!(headers.get("host").unwrap(), "foo.com");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_host() {
        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .uri(Uri::from_static("REQUESTPATH"))
            .header("Content-Type", "application/json")
            .header("Host", "foo.com")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let host = EchoHandler::host(&request);
        assert_eq!(host, "foo.com");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_host_authority() {
        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .uri(Uri::from_static("REQUESTPATH"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let host = EchoHandler::host(&request);
        assert_eq!(host, "REQUESTPATH");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_host_unknown() {
        let http_request = HttpRequest::builder()
            .method(Method::PATCH)
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let host = EchoHandler::host(&request);
        assert_eq!(host, "unknown");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_params() {
        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/path?foo=bar&baz=qux"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let params = EchoHandler::params(&request);
        let iterator = vec![
            ("foo".to_string(), "bar".to_string()),
            ("baz".to_string(), "qux".to_string()),
        ];
        let expected = iterator
            .clone()
            .into_iter()
            .collect::<mapping::OrderedMap>();
        assert_eq!(params, expected);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_default() {
        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/path"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request = Request::from(http_request);
        let params = EchoHandler::params(&request);
        assert_eq!(params, mapping::OrderedMap::default());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_path() {
        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();

        let request = Request::from(http_request);
        let path = EchoHandler::path(&request);
        assert_eq!(path, "/foo/bar");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_path_empty() {
        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();

        let request = Request::from(http_request);
        let path = EchoHandler::path(&request);

        assert_eq!(path, "/");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handler_scheme() {
        let http_request_https = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request_https = Request::from(http_request_https);
        let scheme_https = EchoHandler::scheme(&request_https);
        assert_eq!(scheme_https, "https");

        let http_request_http = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("http://example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request_http = Request::from(http_request_http);
        let scheme_http = EchoHandler::scheme(&request_http);
        assert_eq!(scheme_http, "http");

        let http_request_no_scheme = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("//example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();
        let request_no_scheme = Request::from(http_request_no_scheme);
        let scheme_no_scheme = EchoHandler::scheme(&request_no_scheme);
        assert_eq!(scheme_no_scheme, "http");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handlerconfig_new() {
        let config = EchoHandlerConfig::new("SOMEHOSTNAME".to_string());
        assert_eq!(config.hostname, "SOMEHOSTNAME".to_string());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_handlerstate_new() {
        let config = EchoHandlerConfig::new("SOMEHOSTNAME".to_string());
        let state = EchoState::new(config);
        assert_eq!(state.config.hostname, "SOMEHOSTNAME".to_string());
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_handler_body_success() {
        let test = TESTS
            .test("handler_body_success")
            .expecting(vec!["to_bytes(true): Body(UnsyncBoxBody) 1048576"])
            .with_patches(vec![patch2(to_bytes, |body, limit| {
                let test = TESTS.get("handler_body_success");
                let mut test = test.lock().unwrap();
                test.notify(&format!("to_bytes({:?}): {:?} {:?}", true, body, limit));
                ttest::patch_forward!(test.patch_index(0), to_bytes(body, limit))
            })]);
        defer! {
            test.drop();
        }

        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();

        let request = Request::from(http_request);
        let body_bytes = EchoHandler::body(request).await;
        assert_eq!(body_bytes, Bytes::from("REQUESTBODY"));
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_handler_body_error() {
        let test = TESTS
            .test("handler_body_error")
            .expecting(vec!["to_bytes(true): Body(UnsyncBoxBody) 1048576"])
            .with_patches(vec![patch2(to_bytes, |body, limit| {
                let test = TESTS.get("handler_body_error");
                let mut test = test.lock().unwrap();
                test.notify(&format!("to_bytes({:?}): {:?} {:?}", true, body, limit));
                ttest::patch_forward!(test.patch_index(0), to_bytes(body, 2))
            })]);

        defer! {
            test.drop();
        }

        let http_request = HttpRequest::builder()
            .method(Method::GET)
            .uri(Uri::from_static("https://example.com/foo/bar"))
            .header("Content-Type", "application/json")
            .body(Body::from("REQUESTBODY".to_string()))
            .unwrap();

        let request = Request::from(http_request);
        let body_bytes = EchoHandler::body(request).await;
        assert_eq!(body_bytes, Bytes::new());
    }
}
