use ::log::info;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::net::{IpAddr, SocketAddr};
use tokio::net::TcpListener;

pub struct Endpoint {
    pub address: IpAddr,
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
        SocketAddr::new(self.address, self.port)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Config {
    #[serde(default = "Config::default_address")]
    pub address: IpAddr,
    #[serde(default = "Config::default_port")]
    pub port: u16,
}

impl Config {
    pub fn default_listener() -> Config {
        Config {
            address: Self::default_address(),
            port: Self::default_port(),
        }
    }

    fn default_address() -> IpAddr {
        crate::DEFAULT_ADDRESS.to_string().parse().unwrap()
    }

    fn default_port() -> u16 {
        crate::DEFAULT_PORT
    }
}
