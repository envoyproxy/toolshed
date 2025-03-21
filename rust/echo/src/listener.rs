use crate::{
    handler::{EchoHandler, Provider as _},
    proc::shutdown_signal,
};
use ::log::info;
use async_trait::async_trait;
use axum_server::tls_rustls::RustlsConfig;
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    io,
    net::{IpAddr, SocketAddr},
    path::PathBuf,
    sync::Arc,
};
use tokio::net::TcpListener;
use toolshed_core as core;

#[async_trait]
pub trait ListenersProvider {
    async fn listen(&self, handler: &EchoHandler) -> core::EmptyResult;
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
    async fn listen(&self, handler: &EchoHandler) -> core::EmptyResult {
        let hosts: Vec<Arc<dyn Listener>> = self
            .hosts
            .values()
            .cloned()
            .map(|ep| Arc::new(ep) as Arc<dyn Listener>)
            .collect();
        let mut tasks = Vec::new();
        for host in hosts {
            let handler = handler.router()?;
            tasks.push(tokio::task::spawn(host.listen(handler)));
        }
        core::all_ok!(futures::future::join_all(tasks).await)
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
    pub tls_cert: Option<PathBuf>,
    pub tls_key: Option<PathBuf>,
}

#[async_trait]
pub trait Listener: Send + Sync {
    async fn listen(self: Arc<Self>, router: axum::Router) -> core::EmptyResult {
        info!(
            "Binding listener({}): {}",
            self.name(),
            self.socket_address()
        );
        if self.is_tls() {
            self.serve_tls(router).await;
        } else {
            self.serve(router).await;
        }
        Ok(())
    }

    async fn serve(&self, router: axum::Router) {
        let handle = axum_server::Handle::new();
        let shutdown = shutdown_signal(handle.clone());
        axum::serve(self.bind().await, router)
            .with_graceful_shutdown(shutdown)
            .await
            .expect("Starting server failed");
    }

    async fn serve_tls(&self, router: axum::Router) {
        let handle = axum_server::Handle::new();

        tokio::spawn(shutdown_signal(handle.clone()));

        axum_server::bind_rustls(self.socket_address(), self.tls_config().await.unwrap())
            .handle(handle)
            .serve(router.into_make_service())
            .await
            .unwrap();
    }

    async fn bind(&self) -> TcpListener {
        TcpListener::bind(self.socket_address()).await.unwrap()
    }

    fn is_tls(&self) -> bool {
        matches!((self.tls_cert(), self.tls_key()), (Some(_), Some(_)))
    }

    async fn tls_config(&self) -> io::Result<RustlsConfig> {
        let cert = self.tls_cert().ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::NotFound,
                "TLS configuration missing: cert not available",
            )
        })?;
        let key = self.tls_key().ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::NotFound,
                "TLS configuration missing: key not available",
            )
        })?;
        RustlsConfig::from_pem_file(cert, key).await
    }

    fn name(&self) -> &str;
    fn socket_address(&self) -> SocketAddr;
    fn tls_cert(&self) -> Option<PathBuf>;
    fn tls_key(&self) -> Option<PathBuf>;
}

#[async_trait]
impl Listener for Host {
    fn name(&self) -> &str {
        &self.name
    }

    fn tls_cert(&self) -> Option<PathBuf> {
        self.tls_cert.clone()
    }

    fn tls_key(&self) -> Option<PathBuf> {
        self.tls_key.clone()
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

impl Config {
    pub fn new(host: IpAddr, port: u16) -> Self {
        Self { host, port }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{command, config, handler, test::patch::Patch};
    use guerrilla::{disable_patch, patch0, patch1, patch2};
    use once_cell::sync::Lazy;
    use once_cell::sync::OnceCell;
    use scopeguard::defer;
    use serial_test::serial;
    use std::net::{IpAddr, Ipv4Addr, SocketAddr, SocketAddrV4};
    use toolshed_runner as runner;
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
    async fn test_listeners_listen() {
        let test = TESTS
            .test("listeners_listen")
            .expecting(vec![
                "EchoHandler::router(true)",
                "EchoHandler::router(true)",
                "Host::listen(true)",
                "Host::listen(true)",
            ])
            .with_patches(vec![
                patch1(handler::EchoHandler::router, |_self| {
                    Patch::handler_router(TESTS.get("listeners_listen"), _self)
                }),
                patch2(Host::listen, |_self, handler| {
                    Box::pin(Patch::host_listen(
                        TESTS.get("listeners_listen"),
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
            tls_cert: None,
            tls_key: None,
        };
        let host1: IpAddr = "3.3.3.3".to_string().parse().unwrap();
        let port1 = 2323;
        listeners.hosts.insert(name, host.clone());
        let name1 = "OTHERHOST".to_string();
        let host1 = Host {
            name: name1.clone(),
            host: host1,
            port: port1,
            tls_cert: None,
            tls_key: None,
        };
        listeners.hosts.insert(name1, host1.clone());
        let config = serde_yaml::from_str::<config::Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = command::Command { config, name };
        let handler = <handler::EchoHandler as runner::handler::Factory<command::Command>>::new(
            command.clone(),
        );
        listeners.listen(&handler).await.unwrap();
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
            tls_cert: None,
            tls_key: None,
        };
        listeners.insert(host.clone());
        assert_eq!(listeners.hosts.get(&name).unwrap(), &host);
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_host_serve() {
        let test = TESTS
        .test("host_serve")
        .expecting(vec![
            "axum_server::Handle::new(true)",
            "proc::shutdown_signal(true): Handle { inner: HandleInner { addr: Mutex { data: None, poisoned: false, .. }, addr_notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) }, conn_count: 0, shutdown: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } }, graceful: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } }, graceful_dur: Mutex { data: None, poisoned: false, .. }, conn_end: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } } } }",
            "axum::serve(true)",
            "runner::runner::ctrl_c(true)"
        ])
        .with_patches(vec![
            patch0(axum_server::Handle::new, || {
                Patch::axum_server_handle_new(TESTS.get("host_serve"))
            }),
            patch1(crate::proc::shutdown_signal, |handle| {
                let test = TESTS.get("host_serve");
                let mut test = test.lock().unwrap();
                test.notify(&format!("proc::shutdown_signal({:?}): {:?}", true, handle));
                ttest::patch_forward!(test.patch_index(1), shutdown_signal(handle))
            }),
            patch2(axum::serve, |listener, router| {
                let test = TESTS.get("host_serve");
                test.lock().unwrap().patch_index(2);
                Patch::axum_serve(test, listener, router)
            }),
            patch2(axum::serve::Serve::with_graceful_shutdown, |_self, fun| {
                let test = TESTS.get("host_serve");
                test.lock().unwrap().patch_index(3);
                Patch::axum_serve_with_graceful_shutdown(test, _self, Box::pin(fun))
            }),
            patch0(runner::runner::ctrl_c, || Box::pin({
                let test = TESTS.get("host_serve");
                let test = test.lock().unwrap();
                test.notify(&format!("runner::runner::ctrl_c({:?})", true));
                // Return a future that resolves after a short delay
                async move {
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                    ()
                }
            })),
        ]);
        defer! {
            test.drop();
        }

        let router = axum::Router::new();
        let host: IpAddr = "127.0.0.1".parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        Arc::new(host).serve(router).await;
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_host_serve_tls() {
        let test = TESTS
        .test("host_serve_tls")
        .expecting(vec![
            "axum_server::Handle::new(true)",
            "proc::shutdown_signal(true): Handle { inner: HandleInner { addr: Mutex { data: None, poisoned: false, .. }, addr_notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) }, conn_count: 0, shutdown: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } }, graceful: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } }, graceful_dur: Mutex { data: None, poisoned: false, .. }, conn_end: NotifyOnce { notified: false, notify: Notify { state: 0, waiters: Mutex(PhantomData<std::sync::poison::mutex::Mutex<tokio::util::linked_list::LinkedList<tokio::sync::notify::Waiter, tokio::sync::notify::Waiter>>>, Mutex { data: LinkedList { head: None, tail: None } }) } } } }",
            "Host::tls_config(true)",
            "runner::runner::ctrl_c(true)",
            "axum_server::bind_rustls(true)"
        ])
        .with_patches(vec![
            patch0(axum_server::Handle::new, || {
                static HANDLE: OnceCell<axum_server::Handle> = OnceCell::new();
                let handle = HANDLE.get_or_init(|| {
                    let h = Patch::axum_server_handle_new(TESTS.get("host_serve_tls"));
                    let h_clone = h.clone();
                    tokio::spawn(async move {
                        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
                        h_clone.graceful_shutdown(Some(std::time::Duration::from_millis(200)));
                    });

                    h
                });
                handle.clone()
            }),
            patch1(crate::proc::shutdown_signal, |handle| {
                let test = TESTS.get("host_serve_tls");
                let mut test = test.lock().unwrap();
                test.notify(&format!("proc::shutdown_signal({:?}): {:?}", true, handle));
                ttest::patch_forward!(test.patch_index(1), shutdown_signal(handle))
            }),
            patch2(axum_server::bind_rustls, |address, config| {
                let test = TESTS.get("host_serve_tls");
                test.lock().unwrap().patch_index(2);
                Patch::axum_server_rustls(test, address, config)
            }),
            patch0(runner::runner::ctrl_c, || {
                Box::pin({
                    let test = TESTS.get("host_serve_tls");
                    let test = test.lock().unwrap();
                    test.notify(&format!("runner::runner::ctrl_c({:?})", true));
                    async move {
                        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                        ()
                    }
                })
            }),
            patch1(Host::tls_config, |_self| {
                Box::pin(Patch::host_tls_config(TESTS.get("host_serve_tls"), _self))
            }),
        ]);
        defer! {
            test.drop();
        }
        let router = axum::Router::new();
        let host: IpAddr = "127.0.0.1".parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        Arc::new(host).serve_tls(router).await;
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
            tls_cert: None,
            tls_key: None,
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
            tls_cert: None,
            tls_key: None,
        };
        assert_eq!(host.name, name);
        assert_eq!(
            host.socket_address(),
            SocketAddr::from(SocketAddrV4::new(host4, port))
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_tls_cert() {
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
            tls_cert: Some(PathBuf::from("TEST_TLS_CERT".to_string())),
            tls_key: None,
        };
        assert_eq!(host.name, name);
        assert_eq!(
            host.tls_cert(),
            Some(PathBuf::from("TEST_TLS_CERT".to_string()))
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_tls_key() {
        let host: IpAddr = "8.8.8.8".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name: name.clone(),
            host,
            port,
            tls_cert: None,
            tls_key: Some(PathBuf::from("TEST_TLS_KEY".to_string())),
        };
        assert_eq!(host.name, name);
        assert_eq!(
            host.tls_key(),
            Some(PathBuf::from("TEST_TLS_KEY".to_string()))
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_host_bind() {
        let test = TESTS
            .test("host_bind")
            .expecting(vec!["SocketAddr::new(true): 0.0.0.0 7373"])
            .with_patches(vec![patch2(SocketAddr::new, |host, port| {
                Patch::socket_addr_new(TESTS.get("host_bind"), host, port)
            })]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        let unwanted_listener = host.bind().await;
        let addr = unwanted_listener.local_addr().expect("Failed to get host");
        assert_eq!(addr, "0.0.0.0:7373".parse().unwrap());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_is_tls() {
        let test = TESTS
            .test("host_is_tls")
            .expecting(vec!["Host::tls_cert(true)", "Host::tls_key(true)"])
            .with_patches(vec![
                patch1(Listener::tls_key, |_self| {
                    Patch::host_tls_key(TESTS.get("host_is_tls"), true, _self)
                }),
                patch1(Listener::tls_cert, |_self| {
                    Patch::host_tls_cert(TESTS.get("host_is_tls"), true, _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        assert!(host.is_tls());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_host_is_tls_no() {
        let test = TESTS
            .test("host_is_tls")
            .expecting(vec!["Host::tls_cert(true)", "Host::tls_key(true)"])
            .with_patches(vec![
                patch1(Listener::tls_key, |_self| {
                    Patch::host_tls_key(TESTS.get("host_is_tls"), false, _self)
                }),
                patch1(Listener::tls_cert, |_self| {
                    Patch::host_tls_cert(TESTS.get("host_is_tls"), true, _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        assert!(!host.is_tls());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_host_tls_config() {
        let test = TESTS
            .test("host_tls_config")
            .expecting(vec![
                "Host::tls_cert(true)",
                "Host::tls_key(true)",
                "Host::rustls_from_pem(true): \"TLS_CERT\" \"TLS_KEY\"",
            ])
            .with_patches(vec![
                patch2(
                    RustlsConfig::from_pem_file,
                    |cert: PathBuf, key: PathBuf| {
                        let test = TESTS.get("host_tls_config");
                        let mut test = test.lock().unwrap();
                        test.notify(&format!(
                            "Host::rustls_from_pem({:?}): {:?} {:?}",
                            true, cert, key
                        ));
                        ttest::patch_forward!(
                            test.patch_index(0),
                            RustlsConfig::from_pem_file(
                                PathBuf::from("./snakeoil/tls.cert"),
                                PathBuf::from("./snakeoil/tls.key"),
                            )
                        )
                    },
                ),
                patch1(Listener::tls_key, |_self| {
                    Patch::host_tls_key(TESTS.get("host_tls_config"), true, _self)
                }),
                patch1(Listener::tls_cert, |_self| {
                    Patch::host_tls_cert(TESTS.get("host_tls_config"), true, _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };
        assert!(host.tls_config().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_host_tls_config_missing_cert() {
        let test = TESTS
            .test("host_tls_config_missing_cert")
            .expecting(vec!["Host::tls_cert(true)"])
            .with_patches(vec![
                patch2(
                    RustlsConfig::from_pem_file,
                    |cert: PathBuf, key: PathBuf| {
                        let test = TESTS.get("host_tls_config_missing_cert");
                        let mut test = test.lock().unwrap();
                        test.notify(&format!(
                            "Host::rustls_from_pem({:?}): {:?} {:?}",
                            true, cert, key
                        ));
                        ttest::patch_forward!(
                            test.patch_index(0),
                            RustlsConfig::from_pem_file(
                                PathBuf::from("./snakeoil/tls.cert"),
                                PathBuf::from("./snakeoil/tls.key"),
                            )
                        )
                    },
                ),
                patch1(Listener::tls_cert, |_self| {
                    Patch::host_tls_cert(TESTS.get("host_tls_config_missing_cert"), false, _self)
                }),
                patch1(Listener::tls_key, |_self| {
                    Patch::host_tls_key(TESTS.get("host_tls_config_missing_cert"), true, _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };

        let result = host.tls_config().await;
        assert!(result.is_err());

        if let Err(err) = result {
            assert_eq!(err.kind(), io::ErrorKind::NotFound);
            assert!(err.to_string().contains("TLS configuration missing: cert"));
        }
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_host_tls_config_missing_key() {
        let test = TESTS
            .test("host_tls_config_missing_key")
            .expecting(vec!["Host::tls_cert(true)", "Host::tls_key(true)"])
            .with_patches(vec![
                patch2(
                    RustlsConfig::from_pem_file,
                    |cert: PathBuf, key: PathBuf| {
                        let test = TESTS.get("host_tls_config_missing_key");
                        let mut test = test.lock().unwrap();
                        test.notify(&format!(
                            "Host::rustls_from_pem({:?}): {:?} {:?}",
                            true, cert, key
                        ));
                        ttest::patch_forward!(
                            test.patch_index(0),
                            RustlsConfig::from_pem_file(
                                PathBuf::from("./snakeoil/tls.cert"),
                                PathBuf::from("./snakeoil/tls.key"),
                            )
                        )
                    },
                ),
                patch1(Listener::tls_cert, |_self| {
                    Patch::host_tls_cert(TESTS.get("host_tls_config_missing_key"), true, _self)
                }),
                patch1(Listener::tls_key, |_self| {
                    Patch::host_tls_key(TESTS.get("host_tls_config_missing_key"), false, _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let host: IpAddr = "0.0.0.0".to_string().parse().unwrap();
        let port = 7373;
        let name = "http".to_string();
        let host = Host {
            name,
            host,
            port,
            tls_cert: None,
            tls_key: None,
        };

        let result = host.tls_config().await;
        assert!(result.is_err());

        if let Err(err) = result {
            assert_eq!(err.kind(), io::ErrorKind::NotFound);
            assert!(err.to_string().contains("TLS configuration missing: key"));
        }
    }

    #[test]
    fn test_listeners_new() {
        let listeners = Listeners::new();
        assert!(listeners.hosts.is_empty());
    }

    #[test]
    fn test_listeners_default() {
        let listeners = Listeners::default();
        assert!(listeners.hosts.is_empty());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_listener_listen() {
        let logger = ttest::setup_logger();
        let test = TESTS
            .test("listener_listen")
            .expecting(vec!["Host::is_tls(false)", "Host::serve(true)"])
            .with_patches(vec![
                patch1(Listener::is_tls, |_self| {
                    Patch::listener_is_tls(TESTS.get("listener_listen"), false, _self)
                }),
                patch2(Listener::serve, |_self, _router| {
                    Box::pin(Patch::listener_serve(
                        TESTS.get("listener_listen"),
                        true,
                        _self,
                        _router,
                    ))
                }),
                patch2(Listener::serve_tls, |_self, _router| {
                    Box::pin(Patch::listener_serve_tls(
                        TESTS.get("listener_listen"),
                        true,
                        _self,
                        _router,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }

        let host = Host {
            name: "test".to_string(),
            host: "127.0.0.1".parse().unwrap(),
            port: 8080,
            tls_cert: None,
            tls_key: None,
        };

        let listener = Arc::new(host);
        let router = axum::Router::new();

        let result = listener.listen(router).await;
        assert!(result.is_ok());
        let logs = logger.logs();
        assert!(logs.iter().any(|log| log.level == log::Level::Info
            && log
                .message
                .contains("Binding listener(test): 127.0.0.1:8080")));
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_listener_listen_tls() {
        let logger = ttest::setup_logger();
        let test = TESTS
            .test("listener_listen_tls")
            .expecting(vec!["Host::is_tls(true)", "Host::serve_tls(true)"])
            .with_patches(vec![
                patch1(Listener::is_tls, |_self| {
                    Patch::listener_is_tls(TESTS.get("listener_listen_tls"), true, _self)
                }),
                patch2(Listener::serve, |_self, _router| {
                    Box::pin(Patch::listener_serve(
                        TESTS.get("listener_listen_tls"),
                        true,
                        _self,
                        _router,
                    ))
                }),
                patch2(Listener::serve_tls, |_self, _router| {
                    Box::pin(Patch::listener_serve_tls(
                        TESTS.get("listener_listen_tls"),
                        true,
                        _self,
                        _router,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }
        let host = Host {
            name: "test".to_string(),
            host: "127.0.0.1".parse().unwrap(),
            port: 8080,
            tls_cert: Some(PathBuf::from("cert.pem")),
            tls_key: Some(PathBuf::from("key.pem")),
        };
        let listener = Arc::new(host);
        let router = axum::Router::new();
        let result = listener.listen(router).await;
        assert!(result.is_ok());
        let logs = logger.logs();
        assert!(logs.iter().any(|log| log.level == log::Level::Info
            && log
                .message
                .contains("Binding listener(test): 127.0.0.1:8080")));
    }
}
