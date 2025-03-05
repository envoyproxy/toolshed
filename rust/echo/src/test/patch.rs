use crate::{args::Args, command::Command, config::Config, listener, listener::Endpoint};
use crate::{mapping, response::Response, runner::Runner};
use axum::body::Body;
use axum::{Router, routing::any};
use axum::{
    body::Bytes,
    extract::{Path, Query},
    http::{HeaderMap, Method},
    response,
};
use clap::Parser;
use guerrilla::disable_patch;
use once_cell::sync::Lazy;
use std::{
    any::{Any, TypeId},
    fmt,
    net::{IpAddr, SocketAddr, SocketAddrV4, SocketAddrV6},
};
use tokio::net::TcpListener;
use toolshed_runner::{EmptyResult, config, config::Factory as _, test::Tests};

pub struct Patch {}

impl Patch {
    pub fn args_as_any<'a>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &'a Args,
    ) -> &'a dyn Any {
        tests
            .spy
            .push(testid, &format!("Args::as_any({:?})", success,));
        _self
    }

    pub fn args_downcast_ref<'a>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &'a dyn Any,
    ) -> Option<&'a Args> {
        tests.spy.push(
            testid,
            &format!("Any::downcast_ref::<Args>({:?})", success,),
        );
        if _self.type_id() == TypeId::of::<Args>() {
            unsafe {
                let args_ptr = _self as *const dyn Any as *const Args;
                Some(&*args_ptr)
            }
        } else {
            None
        }
    }

    pub fn args_parse(tests: &Lazy<Tests>, testid: &str, success: bool) -> Args {
        tests
            .spy
            .push(testid, &format!("Args::parse({:?})", success));
        let args = vec!["somecommand"];
        Args::parse_from(args.clone())
    }

    pub fn axum_serve(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        listener: TcpListener,
        router: Router,
    ) -> axum::serve::Serve<TcpListener, axum::routing::Router, axum::routing::Router> {
        let (testid, patch) = tests.get_patch(testid);
        tests
            .spy
            .push(testid, &format!("axum::serve({:?})", success));
        disable_patch!(patch.lock().unwrap(), axum::serve(listener, router))
    }

    pub fn axum_serve_with_graceful_shutdown(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: axum::serve::Serve<TcpListener, axum::routing::Router, axum::routing::Router>,
        fun: std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send>>,
    ) -> axum::serve::WithGracefulShutdown<
        tokio::net::TcpListener,
        Router,
        Router,
        std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send>>,
    > {
        let (testid, patch) = tests.get_patch(testid);
        tests.spy.push(
            testid,
            &format!("axum::serve::Serve::with_graceful_shutdown({:?})", success),
        );
        disable_patch!(patch.lock().unwrap(), _self.with_graceful_shutdown(fun))
    }

    pub fn command_default_name(tests: &Lazy<Tests>, testid: &str, success: bool) -> String {
        tests
            .spy
            .push(testid, &format!("Command::default_name({:?})", success));
        "DEFAULT_NAME".to_string()
    }

    pub fn config_default_host(tests: &Lazy<Tests>, testid: &str, success: bool) -> IpAddr {
        tests
            .spy
            .push(testid, &format!("Config::default_host({:?})", success));
        "8.8.8.8".to_string().parse().unwrap()
    }

    pub fn config_default_port(tests: &Lazy<Tests>, testid: &str, success: bool) -> u16 {
        tests
            .spy
            .push(testid, &format!("Config::default_port({:?})", success));
        7373
    }

    pub async fn config_from_yaml<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        args: config::SafeArgs,
    ) -> Result<Box<Config>, config::SafeError> {
        let (testid, patch) = tests.get_patch(testid);
        tests
            .spy
            .push(testid, &format!("Config::from_yaml({:?})", success));
        if !success {
            return Err("Failed getting config from yaml".into());
        }
        disable_patch!(patch.lock().unwrap(), async {
            Config::from_yaml(args).await
        })
    }

    pub async fn ctrl_c<'a>(tests: &Lazy<Tests<'a>>, testid: &str, success: bool) {
        tests.spy.push(testid, &format!("ctrl_c({:?})", success));
    }

    pub fn default_listener(tests: &Lazy<Tests>, testid: &str, success: bool) -> listener::Config {
        tests.spy.push(
            testid,
            &format!("listener::Config::default_listener({:?})", success),
        );
        listener::Config {
            host: "7.7.7.7".to_string().parse().unwrap(),
            port: 2323,
        }
    }

    pub fn http_response_body(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        string: String,
    ) -> Body {
        let (testid, patch) = tests.get_patch(testid);
        tests
            .spy
            .push(testid, &format!("Body::from({:?}): {}", success, string));
        disable_patch!(patch.lock().unwrap(), Body::from("NEW BODY"))
    }

    pub fn response_fmt(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &Response,
        f: &mut fmt::Formatter,
    ) -> Result<(), std::fmt::Error> {
        tests
            .spy
            .push(testid, &format!("fmt::Display({:?}): {:?}", success, _self));
        write!(f, "SELF BODY")
    }

    pub async fn handler_handle<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> response::Response {
        tests.spy.push(
            testid,
            &format!(
                "EchoHandler::handle({:?}): {:?} {:?} {:?} {:?} {:?}",
                success, method, headers, params, path, body
            ),
        );
        let body = "BOOM";
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", body)))
            .unwrap()
    }

    pub fn override_config_listener<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        args: config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> EmptyResult {
        tests.spy.push(
            testid,
            &format!(
                "Config::override_config_listener({:?}): {:?}, {:?}",
                success, args, config
            ),
        );
        Ok(())
    }

    pub fn response_new<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> Response {
        tests.spy.push(
            testid,
            &format!(
                "EchoHandler::handle({:?}): {:?} {:?} {:?} {:?} {:?}",
                success, method, headers, params, path, body
            ),
        );
        let body_str = String::from_utf8_lossy(&body);
        Response {
            method: method.to_string(),
            headers: headers
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                .collect(),
            query_params: params.into(),
            body: body_str.to_string(),
            path,
        }
    }

    pub fn response_builder(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
    ) -> axum::http::response::Builder {
        let (testid, patch) = tests.get_patch(testid);
        tests
            .spy
            .push(testid, &format!("Response::builder({:?})", success));
        disable_patch!(patch.lock().unwrap(), response::Response::builder())
    }

    pub fn response_to_json<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &Response,
    ) -> response::Response {
        tests
            .spy
            .push(testid, &format!("EchoHandler::handle({:?})", success,));
        let body = "{\"foo\": \"bar\"}";
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", body)))
            .unwrap()
    }

    pub fn router_new(tests: &Lazy<Tests>, testid: &str, success: bool) -> Router {
        let (testid, patch) = tests.get_patch(testid);
        tests
            .spy
            .push(testid, &format!("Router::new({:?})", success));
        disable_patch!(patch.lock().unwrap(), {
            Router::new().route("/nowhere", any(|| async { "The future" }))
        })
    }

    pub async fn runner_cmd_start<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> EmptyResult {
        tests
            .spy
            .push(testid, &format!("Runner::cmd_start({:?})", success));
        Ok(())
    }

    pub fn runner_command_from_config(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        config: Config,
        name: Option<String>,
    ) -> Command {
        tests
            .spy
            .push(testid, &format!("Command::new({:?})", success));
        Command {
            config,
            name: name.expect("Command should be set"),
        }
    }

    pub fn runner_endpoint(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> Result<Endpoint, Box<dyn std::error::Error + Send + Sync>> {
        tests
            .spy
            .push(testid, &format!("Runner::endpoint({:?})", success));
        Ok(Endpoint {
            host: "0.0.0.0".parse().unwrap(),
            port: 1717,
        })
    }

    pub fn runner_factory(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        command: Command,
    ) -> Runner {
        tests
            .spy
            .push(testid, &format!("Runner::new({:?})", success));
        Runner { command }
    }

    pub async fn runner_handle_path<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _method: Method,
        _headers: HeaderMap,
        Query(_params): Query<mapping::OrderedMap>,
        Path(path): Path<String>,
        _body: Bytes,
    ) -> response::Response {
        tests.spy.push(
            testid,
            &format!("Handler::handle_path({:?}): {:?}", success, path),
        );
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from("PATH HANDLED"))
            .unwrap()
    }

    pub async fn runner_handle_root<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _method: Method,
        _headers: HeaderMap,
        Query(_params): Query<mapping::OrderedMap>,
        _body: Bytes,
    ) -> response::Response {
        tests
            .spy
            .push(testid, &format!("Handler::handle_root({:?})", success));
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from("ROOT HANDLED"))
            .unwrap()
    }

    pub fn runner_listener_host(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> Result<IpAddr, Box<dyn std::error::Error + Send + Sync>> {
        tests
            .spy
            .push(testid, &format!("Runner::listener_host({:?})", success));
        Ok("7.7.7.7".to_string().parse().unwrap())
    }

    pub fn runner_listener_port(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> Result<u16, Box<dyn std::error::Error + Send + Sync>> {
        tests
            .spy
            .push(testid, &format!("Runner::listener_port({:?})", success));
        Ok(7777)
    }

    pub fn runner_router(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> Result<Router, Box<dyn std::error::Error + Send + Sync>> {
        tests
            .spy
            .push(testid, &format!("Runner::router({:?})", success));
        Ok(Router::new().route("/nowhere", any(|| async { "The future" })))
    }

    pub async fn runner_run<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &Runner,
    ) -> EmptyResult {
        tests
            .spy
            .push(testid, &format!("Runner::run({:?})", success));
        Ok(())
    }

    pub async fn runner_start<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &Runner,
        endpoint: Endpoint,
    ) -> EmptyResult {
        tests.spy.push(
            testid,
            &format!("Runner::start({:?}): {:?}", success, endpoint),
        );
        Ok(())
    }

    pub fn serde_json_to_string_pretty(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _thing: &Response,
    ) -> Result<String, serde_json::Error> {
        tests.spy.push(
            testid,
            &format!("serde_json::to_string_pretty({:?})", success),
        );
        Ok("{\"pretty\": \"thing\"}".to_string())
    }

    pub fn string_from_utf8_lossy<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        bytes: Bytes,
    ) -> std::borrow::Cow<'a, str> {
        tests.spy.push(
            testid,
            &format!("String::from_utf8_lossy({:?}): {:?}", success, bytes),
        );
        std::borrow::Cow::Borrowed("BODY COW")
    }

    pub fn socket_addr_new(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        host: IpAddr,
        port: u16,
    ) -> SocketAddr {
        tests.spy.push(
            testid,
            &format!("SocketAddr::new({:?}): {:?} {:?}", success, host, port),
        );
        match host {
            IpAddr::V4(ipv4) => SocketAddr::V4(SocketAddrV4::new(ipv4, port)),
            IpAddr::V6(ipv6) => SocketAddr::V6(SocketAddrV6::new(ipv6, port, 0, 0)),
        }
    }
}
