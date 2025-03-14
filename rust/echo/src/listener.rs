use ::log::info;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::net::{IpAddr, SocketAddr};
use tokio::net::TcpListener;

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Endpoint {
    pub host: IpAddr,
    pub port: u16,
}

#[async_trait]
pub trait Listener {
    async fn bind(&self) -> TcpListener {
        info!("Binding listener: {}", self.socket_address());
        TcpListener::bind(self.socket_address()).await.unwrap()
    }
    fn socket_address(&self) -> SocketAddr;
}

#[async_trait]
impl Listener for Endpoint {
    fn socket_address(&self) -> SocketAddr {
        SocketAddr::new(self.host, self.port)
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    #[serde(default = "Config::default_host")]
    pub host: IpAddr,
    #[serde(default = "Config::default_port")]
    pub port: u16,
}

impl Config {
    pub fn default_listener() -> Config {
        Config {
            host: Self::default_host(),
            port: Self::default_port(),
        }
    }

    fn default_host() -> IpAddr {
        crate::DEFAULT_ADDRESS.to_string().parse().unwrap()
    }

    fn default_port() -> u16 {
        crate::DEFAULT_PORT
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::patch::Patch;
    use guerrilla::{patch0, patch2};
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
        let endpoint = Endpoint { host, port };
        assert_eq!(
            endpoint.socket_address(),
            SocketAddr::from(SocketAddrV4::new(host4, port))
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_default_listener() {
        let test = TESTS
            .test("config_default_listener")
            .expecting(vec![
                "Config::default_host(true)",
                "Config::default_port(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_host, || {
                    Patch::config_default_host(TESTS.get("config_default_listener"))
                }),
                patch0(Config::default_port, || {
                    Patch::config_default_port(TESTS.get("config_default_listener"))
                }),
            ]);
        defer! {
            test.drop();
        }

        let host = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let config = Config { host, port };
        assert_eq!(Config::default_listener(), config);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_default_host() {
        assert_eq!(
            Config::default_host(),
            crate::DEFAULT_ADDRESS
                .to_string()
                .parse::<IpAddr>()
                .unwrap()
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_default_port() {
        assert_eq!(Config::default_port(), crate::DEFAULT_PORT);
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
        let endpoint = Endpoint { host, port };
        let unwanted_listener = endpoint.bind().await;
        let addr = unwanted_listener
            .local_addr()
            .expect("Failed to get address");
        assert_eq!(addr, "0.0.0.0:7373".parse().unwrap());
    }
}
