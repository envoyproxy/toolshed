use crate::handler::{EchoHandler, Provider as _};
use ::log::info;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    net::{IpAddr, SocketAddr},
    sync::Arc,
};
use tokio::net::TcpListener;
use toolshed_core as core;
use toolshed_runner as runner;

#[async_trait]
pub trait ListenersProvider {
    async fn bind(&self, handler: &EchoHandler) -> core::EmptyResult;
    fn insert(&mut self, host: Host);
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Listeners {
    pub hosts: HashMap<String, Host>,
}

impl Listeners {
    pub fn new() -> Self {
        Self {
            hosts: HashMap::new(),
        }
    }
}

impl Default for Listeners {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ListenersProvider for Listeners {
    async fn bind(&self, handler: &EchoHandler) -> core::EmptyResult {
        let hosts: Vec<Arc<dyn Listener>> = self
            .hosts
            .values()
            .cloned()
            .map(|ep| Arc::new(ep) as Arc<dyn Listener>)
            .collect();
        let mut tasks = Vec::new();
        for host in hosts {
            let handler = handler.router()?;
            tasks.push(tokio::task::spawn(host.bind(handler)));
        }
        futures::future::join_all(tasks).await;
        Ok(())
    }

    fn insert(&mut self, host: Host) {
        self.hosts.insert(host.name.clone(), host);
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Host {
    pub name: String,
    pub host: IpAddr,
    pub port: u16,
}

#[async_trait]
pub trait Listener: Send + Sync {
    async fn bind(self: Arc<Self>, router: axum::Router) {
        axum::serve(self.listen().await, router)
            .with_graceful_shutdown(runner::runner::ctrl_c())
            .await
            .expect("Starting server failed");
    }

    async fn listen(&self) -> TcpListener {
        info!(
            "Binding listener({}): {}",
            self.name(),
            self.socket_address()
        );
        TcpListener::bind(self.socket_address()).await.unwrap()
    }
    fn name(&self) -> &str;
    fn socket_address(&self) -> SocketAddr;
}

#[async_trait]
impl Listener for Host {
    fn name(&self) -> &str {
        &self.name
    }

    fn socket_address(&self) -> SocketAddr {
        SocketAddr::new(self.host, self.port)
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    pub host: IpAddr,
    pub port: u16,
}

impl Config {}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{command, config, handler, test::patch::Patch};
    use guerrilla::{patch0, patch1, patch2};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::net::{IpAddr, Ipv4Addr, SocketAddr, SocketAddrV4};
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    #[test]
    #[serial(toolshed_lock)]
    fn test_listeners_constructor() {
        let listeners = Listeners::new();
        assert!(listeners.hosts.is_empty());
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_listeners_bind() {
        let test = TESTS
            .test("listeners_bind")
            .expecting(vec![
                "EchoHandler::router(true)",
                "EchoHandler::router(true)",
                "Host::bind(true)",
                "Host::bind(true)",
            ])
            .with_patches(vec![
                patch1(handler::EchoHandler::router, |_self| {
                    Patch::handler_router(TESTS.get("listeners_bind"), _self)
                }),
                patch2(Host::bind, |_self, handler| {
                    Box::pin(Patch::host_bind(
                        TESTS.get("listeners_bind"),
                        _self,
                        handler,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }

        let mut listeners = Listeners::new();
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "SOMEHOST".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
        };
        let host1: IpAddr = "3.3.3.3".to_string().parse().unwrap();
        let port1 = 2323;
        listeners.hosts.insert(name, host.clone());
        let name1 = "OTHERHOST".to_string();
        let host1 = Host {
            name: name1.clone(),
            host: host1,
            port: port1,
        };
        listeners.hosts.insert(name1, host1.clone());
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = command::Command { config, name };
        let handler = <handler::EchoHandler as runner::handler::Factory<command::Command>>::new(
            command.clone(),
        );
        listeners.bind(&handler).await.unwrap();
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_listeners_insert() {
        let mut listeners = Listeners::new();
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "SOMEHOST".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
        };
        listeners.insert(host.clone());
        assert_eq!(listeners.hosts.get(&name).unwrap(), &host);
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_host_bind() {
        let test = TESTS
            .test("host_bind")
            .expecting(vec![
                "axum::serve(true)",
                "axum::serve::Serve::with_graceful_shutdown(true)",
                "ctrl_c(true)",
            ])
            .with_patches(vec![
                patch0(runner::runner::ctrl_c, || {
                    Box::pin(Patch::ctrl_c(TESTS.get("host_bind")))
                }),
                patch2(axum::serve, |listener, router| {
                    let test = TESTS.get("host_bind");
                    test.lock().unwrap().patch_index(1);
                    Patch::axum_serve(test, listener, router)
                }),
                patch2(axum::serve::Serve::with_graceful_shutdown, |_self, fun| {
                    let test = TESTS.get("host_bind");
                    test.lock().unwrap().patch_index(2);
                    Patch::axum_serve_with_graceful_shutdown(test, _self, Box::pin(fun))
                }),
            ]);
        defer! {
            test.drop();
        }

        let router = axum::Router::new();
        let host: IpAddr = "127.0.0.1".parse().unwrap();
        let port = 1717;
        let name = "http".to_string();
        let host = Host { name, host, port };
        Arc::new(host).bind(router).await;
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_name() {
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
        };
        assert_eq!(host.name, name);
        assert_eq!(host.name(), name);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_socket_address() {
        let test = TESTS
            .test("host_socket_address")
            .expecting(vec!["SocketAddr::new(true): 8.8.8.8 7373"])
            .with_patches(vec![patch2(SocketAddr::new, |host, port| {
                Patch::socket_addr_new(TESTS.get("host_socket_address"), host, port)
            })]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let host4: Ipv4Addr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
        };
        assert_eq!(host.name, name);
        assert_eq!(
            host.socket_address(),
            SocketAddr::from(SocketAddrV4::new(host4, port))
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_host_listen() {
        let test = TESTS
            .test("host_listen")
            .expecting(vec!["SocketAddr::new(true): 0.0.0.0 7373"])
            .with_patches(vec![patch2(SocketAddr::new, |host, port| {
                Patch::socket_addr_new(TESTS.get("host_listen"), host, port)
            })]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host { name, host, port };
        let unwanted_listener = host.listen().await;
        let addr = unwanted_listener
            .local_addr()
            .expect("Failed to get address");
        assert_eq!(addr, "0.0.0.0:7373".parse().unwrap());
    }
}
