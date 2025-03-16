use crate::handler::{EchoHandler, Provider as _};
use ::log::info;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    net::{IpAddr, SocketAddr},
};
use tokio::{net::TcpListener, task};
use toolshed_core as core;
use toolshed_runner as runner;

#[async_trait]
pub trait ListenersProvider {
    async fn bind(&self, handler: &EchoHandler) -> core::EmptyResult;
    fn insert(&mut self, key: &str, endpoint: Endpoint);
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Listeners {
    pub endpoints: HashMap<String, Endpoint>,
}

impl Listeners {
    pub fn new() -> Self {
        Self {
            endpoints: HashMap::new(),
        }
    }
}

#[async_trait]
impl ListenersProvider for Listeners {
    async fn bind(&self, handler: &EchoHandler) -> core::EmptyResult {
        let endpoints: Vec<_> = self.endpoints.values().cloned().collect();
        let mut tasks = Vec::new();
        for endpoint in endpoints {
            let handler = handler.router()?;
            let task = task::spawn(async move {
                if let Err(e) = axum::serve(endpoint.bind().await, handler)
                    .with_graceful_shutdown(runner::runner::ctrl_c())
                    .await
                {
                    eprintln!("Error serving endpoint: {:?}", e);
                }
            });
            tasks.push(task);
        }
        futures::future::join_all(tasks).await;
        Ok(())
    }

    fn insert(&mut self, key: &str, endpoint: Endpoint) {
        self.endpoints.insert(key.to_string(), endpoint);
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Endpoint {
    pub name: String,
    pub host: IpAddr,
    pub port: u16,
}

#[async_trait]
pub trait Listener {
    async fn bind(&self) -> TcpListener {
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
impl Listener for Endpoint {
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
    use crate::test::patch::Patch;
    use guerrilla::patch2;
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
    fn test_endpoint_name() {
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let endpoint = Endpoint {
            name: name.clone(),
            host,
            port,
        };
        assert_eq!(endpoint.name, name);
        assert_eq!(endpoint.name(), name);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_endpoint_socket_address() {
        let test = TESTS
            .test("endpoint_socket_address")
            .expecting(vec!["SocketAddr::new(true): 8.8.8.8 7373"])
            .with_patches(vec![patch2(SocketAddr::new, |host, port| {
                Patch::socket_addr_new(TESTS.get("endpoint_socket_address"), host, port)
            })]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let host4: Ipv4Addr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let endpoint = Endpoint {
            name: name.clone(),
            host,
            port,
        };
        assert_eq!(endpoint.name, name);
        assert_eq!(
            endpoint.socket_address(),
            SocketAddr::from(SocketAddrV4::new(host4, port))
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_endpoint_bind() {
        let test = TESTS
            .test("endpoint_bind")
            .expecting(vec!["SocketAddr::new(true): 0.0.0.0 7373"])
            .with_patches(vec![patch2(SocketAddr::new, |host, port| {
                Patch::socket_addr_new(TESTS.get("endpoint_bind"), host, port)
            })]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let endpoint = Endpoint { name, host, port };
        let unwanted_listener = endpoint.bind().await;
        let addr = unwanted_listener
            .local_addr()
            .expect("Failed to get address");
        assert_eq!(addr, "0.0.0.0:7373".parse().unwrap());
    }
}
