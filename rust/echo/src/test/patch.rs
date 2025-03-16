use crate::{
    args::Args,
    command::Command,
    config::Config,
    handler::EchoHandler,
    listener::{self, Endpoint, Listeners, ListenersProvider as _},
};
use crate::{mapping, response::Response, runner::Runner};
use axum::body::Body;
use axum::{
    body::Bytes,
    http::{HeaderMap, Method},
    response,
};
use axum::{routing::any, Router};
use clap::Parser;
use guerrilla::disable_patch;
use std::{
    any::{Any, TypeId},
    collections::HashMap,
    fmt,
    net::{IpAddr, SocketAddr, SocketAddrV4, SocketAddrV6},
    sync::{Arc, Mutex},
};
use tokio::net::TcpListener;
use toolshed_core as core;
use toolshed_runner::{self as runner, config::Factory as _};
use toolshed_test as ttest;

pub struct Patch {}

impl Patch {
    pub fn args_as_any<'a>(test: Arc<Mutex<ttest::Test>>, _self: &'a Args) -> &'a dyn Any {
        let test = test.lock().unwrap();
        test.notify(&format!("Args::as_any({:?})", !test.fails));
        _self
    }

    pub fn args_downcast_ref<'a>(
        test: Arc<Mutex<ttest::Test>>,
        _self: &'a dyn Any,
    ) -> Option<&'a Args> {
        let test = test.lock().unwrap();
        test.notify(&format!("Any::downcast_ref::<Args>({:?})", !test.fails));
        if _self.type_id() == TypeId::of::<Args>() {
            unsafe {
                let args_ptr = _self as *const dyn Any as *const Args;
                Some(&*args_ptr)
            }
        } else {
            None
        }
    }

    pub fn args_parse(test: Arc<Mutex<ttest::Test>>) -> Args {
        let test = test.lock().unwrap();
        test.notify(&format!("Args::parse({:?})", !test.fails));
        let args = vec!["somecommand"];
        Args::parse_from(args.clone())
    }

    pub fn axum_serve(
        test: Arc<Mutex<ttest::Test>>,
        listener: TcpListener,
        router: Router,
    ) -> axum::serve::Serve<TcpListener, axum::routing::Router, axum::routing::Router> {
        let test = test.lock().unwrap();
        test.notify(&format!("axum::serve({:?})", !test.fails));
        disable_patch!(
            test.get_patch().lock().unwrap(),
            axum::serve(listener, router)
        )
    }

    pub fn axum_serve_with_graceful_shutdown(
        test: Arc<Mutex<ttest::Test>>,
        _self: axum::serve::Serve<TcpListener, axum::routing::Router, axum::routing::Router>,
        fun: std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send>>,
    ) -> axum::serve::WithGracefulShutdown<
        tokio::net::TcpListener,
        Router,
        Router,
        std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send>>,
    > {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "axum::serve::Serve::with_graceful_shutdown({:?})",
            !test.fails
        ));
        disable_patch!(
            test.get_patch().lock().unwrap(),
            _self.with_graceful_shutdown(fun)
        )
    }

    pub fn command_default_name(test: Arc<Mutex<ttest::Test>>) -> String {
        let test = test.lock().unwrap();
        test.notify(&format!("Command::default_name({:?})", !test.fails));
        "DEFAULT_NAME".to_string()
    }

    pub fn config_default_host(test: Arc<Mutex<ttest::Test>>) -> IpAddr {
        let test = test.lock().unwrap();
        test.notify(&format!("Config::default_host({:?})", !test.fails));
        "8.8.8.8".to_string().parse().unwrap()
    }

    pub fn config_default_port(test: Arc<Mutex<ttest::Test>>) -> u16 {
        let test = test.lock().unwrap();
        test.notify(&format!("Config::default_port({:?})", !test.fails));
        7373
    }

    pub async fn config_from_yaml<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        args: runner::config::SafeArgs,
    ) -> Result<Box<Config>, runner::config::SafeError> {
        {
            let test = test.lock().unwrap();
            test.notify(&format!("Config::from_yaml({:?})", !test.fails));
            if test.fails {
                return Err("Failed getting config from yaml".into());
            }
        }
        disable_patch!(
            test.lock().unwrap().get_patch().lock().unwrap(),
            async Config::from_yaml(args).await
        )
    }

    pub async fn config_override_config(
        test: Arc<Mutex<ttest::Test<'_>>>,
        args: &runner::config::ArcSafeArgs,
        config: Box<Config>,
    ) -> Result<Box<Config>, runner::config::SafeError> {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "Config::override_config({:?}): {:?}, {:?}",
            !test.fails, args, config
        ));
        Ok(config)
    }

    pub fn config_override_config_hostname<
        T: runner::config::Provider + serde::Deserialize<'static>,
    >(
        test: Arc<Mutex<ttest::Test>>,
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "Config::override_config_hostname({:?}): {:?}, {:?}",
            !test.fails, args, config
        ));
        Ok(())
    }

    pub fn config_override_config_http_host<
        T: runner::config::Provider + serde::Deserialize<'static>,
    >(
        test: Arc<Mutex<ttest::Test>>,
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "Config::override_config_http_host({:?}): {:?}, {:?}",
            !test.fails, args, config
        ));
        Ok(())
    }

    pub fn config_override_config_http_port<
        T: runner::config::Provider + serde::Deserialize<'static>,
    >(
        test: Arc<Mutex<ttest::Test>>,
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "Config::override_config_http_port({:?}): {:?}, {:?}",
            !test.fails, args, config
        ));
        Ok(())
    }

    pub async fn ctrl_c<'a>(test: Arc<Mutex<ttest::Test<'a>>>) {
        let test = test.lock().unwrap();
        test.notify(&format!("ctrl_c({:?})", !test.fails));
    }

    pub fn default_hostname(test: Arc<Mutex<ttest::Test>>) -> String {
        let test = test.lock().unwrap();
        test.notify(&format!("Config::default_hostname({:?})", !test.fails));
        "DEFAULT HOSTNAME".to_string()
    }

    pub fn default_listeners(test: Arc<Mutex<ttest::Test>>) -> HashMap<String, listener::Config> {
        let test = test.lock().unwrap();
        test.notify(&format!("Config::default_listeners({:?})", !test.fails));
        let mut map = HashMap::new();
        map.insert(
            "http".to_string(),
            listener::Config {
                host: "7.7.7.7".to_string().parse().unwrap(),
                port: 2323,
            },
        );
        map
    }

    pub fn env_var(
        test: Arc<Mutex<ttest::Test>>,
        name: &str,
    ) -> Result<String, std::env::VarError> {
        let test = test.lock().unwrap();
        test.notify(&format!("std::env::var({:?}): {:?}", !test.fails, name));
        if test.fails {
            return Err(std::env::VarError::NotUnicode("Not unicode".into()));
        }
        Ok("SOMEVAR".to_string())
    }

    pub fn handler_route_path<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &EchoHandler,
    ) -> axum::routing::MethodRouter {
        let test = test.lock().unwrap();
        test.notify(&format!("Handler::route_path({:?})", !test.fails));
        any(|| async { "The future path" })
    }

    pub fn handler_route_root<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &EchoHandler,
    ) -> axum::routing::MethodRouter {
        let test = test.lock().unwrap();
        test.notify(&format!("Handler::route_root({:?})", !test.fails));
        any(|| async { "The future root" })
    }

    pub fn handler_router(
        test: Arc<Mutex<ttest::Test>>,
        _self: &EchoHandler,
    ) -> Result<Router, Box<dyn std::error::Error + Send + Sync>> {
        let test = test.lock().unwrap();
        test.notify(&format!("EchoHandler::router({:?})", !test.fails));
        Ok(Router::new().route("/nowhere", any(|| async { "The future" })))
    }

    pub fn http_response_body(test: Arc<Mutex<ttest::Test>>, string: String) -> Body {
        let test = test.lock().unwrap();
        test.notify(&format!("Body::from({:?}): {}", !test.fails, string));
        disable_patch!(test.get_patch().lock().unwrap(), Body::from("NEW BODY"))
    }

    pub fn response_fmt(
        test: Arc<Mutex<ttest::Test>>,
        _self: &Response,
        f: &mut fmt::Formatter,
    ) -> Result<(), std::fmt::Error> {
        let test = test.lock().unwrap();
        test.notify(&format!("fmt::Display({:?}): {:?}", !test.fails, _self));
        write!(f, "SELF BODY")
    }

    pub fn handler_config(
        test: Arc<Mutex<ttest::Test>>,
        returns: Option<core::Primitive>,
        _self: &EchoHandler,
        key: &str,
    ) -> Option<core::Primitive> {
        let test = test.lock().unwrap();
        test.notify(&format!("Handler::config({:?}): {:?}", !test.fails, key));
        returns
    }

    pub async fn handler_handle<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &EchoHandler,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> response::Response {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "EchoHandler::handle({:?}): {:?} {:?} {:?} {:?} {:?}",
            !test.fails, method, headers, params, path, body
        ));
        let body = "BOOM";
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", body)))
            .unwrap()
    }

    pub async fn listeners_bind<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &Listeners,
        handler: &EchoHandler,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::start({:?}): {:?}", !test.fails, handler));
        Ok(())
    }

    pub fn response_builder(test: Arc<Mutex<ttest::Test>>) -> axum::http::response::Builder {
        let test = test.lock().unwrap();
        test.notify(&format!("Response::builder({:?})", !test.fails));
        disable_patch!(
            test.get_patch().lock().unwrap(),
            response::Response::builder()
        )
    }

    pub fn response_new<'a>(
        test: Arc<Mutex<ttest::Test>>,
        hostname: String,
        method: Method,
        headers: HeaderMap,
        params: mapping::OrderedMap,
        path: String,
        body: Bytes,
    ) -> Response {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "Response::new({:?}): {:?} {:?} {:?} {:?} {:?} {:?}",
            !test.fails, hostname, method, headers, params, path, body
        ));
        let body_str = String::from_utf8_lossy(&body);
        Response {
            hostname,
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

    pub fn response_to_json<'a>(
        test: Arc<Mutex<ttest::Test>>,
        _self: &Response,
    ) -> response::Response {
        let test = test.lock().unwrap();
        test.notify(&format!("Response::to_json({:?})", !test.fails,));
        let body = "{\"foo\": \"bar\"}";
        response::Response::builder()
            .header("Content-Type", "application/json")
            .body(Body::from(format!("{}\n", body)))
            .unwrap()
    }

    pub fn router_new(test: Arc<Mutex<ttest::Test>>) -> Router {
        let test = test.lock().unwrap();
        test.notify(&format!("Router::new({:?})", !test.fails));
        disable_patch!(test.get_patch().lock().unwrap(), {
            Router::new().route("/nowhere", any(|| async { "The future" }))
        })
    }

    pub async fn runner_cmd_start<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &Runner,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::cmd_start({:?})", !test.fails));
        Ok(())
    }

    pub fn runner_command_from_config(
        test: Arc<Mutex<ttest::Test>>,
        config: Config,
        name: Option<String>,
    ) -> Command {
        let test = test.lock().unwrap();
        test.notify(&format!("Command::new({:?})", !test.fails));
        Command {
            config,
            name: name.expect("Command should be set"),
        }
    }

    pub fn runner_listeners(
        test: Arc<Mutex<ttest::Test>>,
        _self: &Runner,
    ) -> Result<Listeners, Box<dyn std::error::Error + Send + Sync>> {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::listeners({:?})", !test.fails));
        let mut listeners = Listeners::new();
        listeners.insert(
            "http",
            Endpoint {
                name: "http".to_string(),
                host: "0.0.0.0".parse().unwrap(),
                port: 1717,
            },
        );
        Ok(listeners)
    }

    pub fn runner_get_handler<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &'a Runner,
    ) -> &'a EchoHandler {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::get_handler({:?})", !test.fails));
        &_self.handler
    }

    pub fn runner_factory(test: Arc<Mutex<ttest::Test>>, handler: EchoHandler) -> Runner {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::new({:?})", !test.fails));
        Runner { handler }
    }

    pub fn runner_http_host(
        test: Arc<Mutex<ttest::Test>>,
        _self: &Runner,
    ) -> Result<IpAddr, Box<dyn std::error::Error + Send + Sync>> {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::http_host({:?})", !test.fails));
        Ok("7.7.7.7".to_string().parse().unwrap())
    }

    pub fn runner_http_port(
        test: Arc<Mutex<ttest::Test>>,
        _self: &Runner,
    ) -> Result<u16, Box<dyn std::error::Error + Send + Sync>> {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::http_port({:?})", !test.fails));
        Ok(7777)
    }

    pub async fn runner_run<'a>(
        test: Arc<Mutex<ttest::Test<'a>>>,
        _self: &Runner,
    ) -> core::EmptyResult {
        let test = test.lock().unwrap();
        test.notify(&format!("Runner::run({:?})", !test.fails));
        Ok(())
    }

    pub fn serde_json_to_string_pretty(
        test: Arc<Mutex<ttest::Test>>,
        _thing: &Response,
    ) -> Result<String, serde_json::Error> {
        let test = test.lock().unwrap();
        test.notify(&format!("serde_json::to_string_pretty({:?})", !test.fails));
        Ok("{\"pretty\": \"thing\"}".to_string())
    }

    pub fn string_from_utf8_lossy<'a>(
        test: Arc<Mutex<ttest::Test>>,
        bytes: Bytes,
    ) -> std::borrow::Cow<'a, str> {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "String::from_utf8_lossy({:?}): {:?}",
            !test.fails, bytes
        ));
        std::borrow::Cow::Borrowed("BODY COW")
    }

    pub fn socket_addr_new(test: Arc<Mutex<ttest::Test>>, host: IpAddr, port: u16) -> SocketAddr {
        let test = test.lock().unwrap();
        test.notify(&format!(
            "SocketAddr::new({:?}): {:?} {:?}",
            !test.fails, host, port
        ));
        match host {
            IpAddr::V4(ipv4) => SocketAddr::V4(SocketAddrV4::new(ipv4, port)),
            IpAddr::V6(ipv6) => SocketAddr::V6(SocketAddrV6::new(ipv6, port, 0, 0)),
        }
    }
}
