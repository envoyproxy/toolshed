use crate::mapping;
use axum::{
    body::{Body, Bytes},
    http::{HeaderMap, Method},
    response,
};
use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Serialize, Deserialize)]
pub struct Response {
    pub hostname: String,
    pub method: String,
    pub headers: mapping::OrderedMap,
    pub query_params: mapping::OrderedMap,
    pub body: String,
    pub path: String,
}

impl Response {
    pub fn new(
        hostname: String,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> Self {
        let headers: mapping::OrderedMap = headers
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
            .collect();
        Response {
            hostname,
            method: method.to_string(),
            headers,
            query_params: params,
            body: String::from_utf8_lossy(&body).to_string(),
            path,
        }
    }

    pub fn to_json(&self) -> response::Response {
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", self)))
            .unwrap()
    }
}

impl fmt::Debug for Response {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "Response: {}",
            serde_json::to_string_pretty(&self).unwrap_or_default()
        )
    }
}

impl fmt::Display for Response {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "{}",
            serde_json::to_string_pretty(&self).unwrap_or_default()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::patch::Patch;
    use bytes::Bytes;
    use guerrilla::{patch0, patch1, patch2};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_runner::test::{patch::Patches, spy::Spy, Tests};

    static PATCHES: Lazy<Patches> = Lazy::new(Patches::new);
    static SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TESTS: Lazy<Tests> = Lazy::new(|| Tests::new(&SPY, &PATCHES));

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_response_new() {
        let test = TESTS
            .test("response_new")
            .expecting(vec!["String::from_utf8_lossy(true): b\"BOODY\""])
            .with_patches(vec![patch1(String::from_utf8_lossy, |body| {
                Patch::string_from_utf8_lossy(TESTS.get("response_new").unwrap(), Bytes::from(body))
            })]);
        defer! {
            test.drop();
        }

        let method = Method::TRACE;
        let mut headers = HeaderMap::new();
        headers.insert("X-UP", "baz".parse().unwrap());
        headers.insert("X-DOWN", "baz".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("BOODY".to_string());
        let response = Response::new(
            "HOSTNAME23".to_string(),
            method,
            headers.clone(),
            params.clone(),
            "BACKWARDS".to_string(),
            body,
        );
        assert_eq!(response.method, Method::TRACE.to_string());
        assert_eq!(
            response.headers,
            headers
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                .collect()
        );
        assert_eq!(response.query_params, params);
        assert_eq!(response.body, "BODY COW");
        assert_eq!(response.path, "BACKWARDS");
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_response_to_json() {
        let test = TESTS.test("response_to_json")
            .expecting(vec![
                "Response::builder(true)",
                concat!(
                    "fmt::Display(true): Response: ",
                    "{\n  \"hostname\": \"HOSTNAME23\",\n  \"method\": \"TRACE\",\n  \"headers\": {\n    \"x-up\": \"baz\",\n    \"x-down\": \"baz\",\n    \"x-forward\": \"baz\",\n    \"x-back\": \"baz\"\n  },\n  ",
                    "\"query_params\": {\n    \"a0\": \"a\",\n    \"b0\": \"b\",\n    \"c0\": \"c\",\n    \"a1\": \"a\",\n    \"b1\": \"b\",\n    \"c1\": \"c\"\n  },\n  ",
                    "\"body\": \"BOODY\",\n  \"path\": \"BACKWARDS\"\n}"),
                "Body::from(true): SELF BODY\n"
            ])
            .with_patches(vec![
                patch0(response::Response::builder, || {
                    let test = TESTS.get("response_to_json").unwrap();
                    test.lock().unwrap().patch_index(0);
                    Patch::response_builder(test)
                }),
                patch2(fmt::Display::fmt, |_self, f| {
                    Patch::response_fmt(TESTS.get("response_to_json").unwrap(), _self, f)
                }),
                patch1(Body::from, |string| {
                    let test = TESTS.get("response_to_json").unwrap();
                    test.lock().unwrap().patch_index(2);
                    Patch::http_response_body(test, string)
                }),
            ]);
        defer! {
            test.drop();
        }

        let method = Method::TRACE;
        let mut headers = HeaderMap::new();
        headers.insert("X-UP", "baz".parse().unwrap());
        headers.insert("X-DOWN", "baz".parse().unwrap());
        headers.insert("X-FORWARD", "baz".parse().unwrap());
        headers.insert("X-BACK", "baz".parse().unwrap());
        let params: mapping::OrderedMap = [
            ("a0".to_string(), "a".to_string()),
            ("b0".to_string(), "b".to_string()),
            ("c0".to_string(), "c".to_string()),
            ("a1".to_string(), "a".to_string()),
            ("b1".to_string(), "b".to_string()),
            ("c1".to_string(), "c".to_string()),
        ]
        .as_ref()
        .into();
        let body = Bytes::from("BOODY".to_string());
        let hostname = "HOSTNAME23".to_string();
        let response = Response::new(
            hostname,
            method,
            headers.clone(),
            params.clone(),
            "BACKWARDS".to_string(),
            body,
        );
        let result = response.to_json();
        let (parts, body) = result.into_parts();
        let bytes = body.collect().await.unwrap().to_bytes();
        assert_eq!("NEW BODY", str::from_utf8(&bytes).unwrap());
        assert_eq!(
            format!("{:?}", hyper::Response::from_parts(parts, Body::empty())),
            "Response { status: 200, version: HTTP/1.1, headers: {\"content-type\": \"application/json\"}, body: Body(UnsyncBoxBody) }"
        );
    }

    use http_body_util::BodyExt; // Import this for `.collect()`
    use std::str;

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_response_debug() {
        let test = TESTS
            .test("response_debug")
            .expecting(vec!["serde_json::to_string_pretty(true)"])
            .with_patches(vec![patch1(
                serde_json::to_string_pretty::<&Response>,
                |thing| {
                    Patch::serde_json_to_string_pretty(TESTS.get("response_debug").unwrap(), thing)
                },
            )]);
        defer! {
            test.drop();
        }

        let method = Method::TRACE;
        let mut headers = HeaderMap::new();
        headers.insert("X-UP", "baz".parse().unwrap());
        headers.insert("X-DOWN", "baz".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("BOODY".to_string());
        let hostname = "HOSTNAME23".to_string();
        let response = Response::new(
            hostname,
            method,
            headers.clone(),
            params.clone(),
            "BACKWARDS".to_string(),
            body,
        );
        assert_eq!(
            "Response: {\"pretty\": \"thing\"}",
            format!("{:?}", response)
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_response_display() {
        let test = TESTS
            .test("response_display")
            .expecting(vec!["serde_json::to_string_pretty(true)"])
            .with_patches(vec![patch1(
                serde_json::to_string_pretty::<&Response>,
                |thing| {
                    Patch::serde_json_to_string_pretty(
                        TESTS.get("response_display").unwrap(),
                        thing,
                    )
                },
            )]);
        defer! {
            test.drop();
        }

        let method = Method::TRACE;
        let mut headers = HeaderMap::new();
        headers.insert("X-UP", "baz".parse().unwrap());
        headers.insert("X-DOWN", "baz".parse().unwrap());
        let params: mapping::OrderedMap = [("bar".to_string(), "foo".to_string())].as_ref().into();
        let body = Bytes::from("BOODY".to_string());
        let hostname = "HOSTNAME23".to_string();
        let response = Response::new(
            hostname,
            method,
            headers.clone(),
            params.clone(),
            "BACKWARDS".to_string(),
            body,
        );
        assert_eq!("{\"pretty\": \"thing\"}", format!("{:}", response));
    }
}
