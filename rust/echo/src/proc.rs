use std::time::Duration;
use tokio::signal;
use toolshed_runner as runner;

pub async fn shutdown_signal(handle: axum_server::Handle) {
    let ctrl_c = async { runner::runner::ctrl_c().await };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
    handle.graceful_shutdown(Some(Duration::from_secs(1)));
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum_server::Handle;
    use serial_test::serial;
    use tokio::time;

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_shutdown_signal() {
        let handle = Handle::new();
        let handle_clone = handle.clone();
        let (tx, rx) = tokio::sync::oneshot::channel();
        let shutdown_task = tokio::spawn(async move {
            tokio::spawn(async {
                unsafe {
                    libc::raise(libc::SIGINT);
                }
            });
            shutdown_signal(handle_clone).await;
            let _ = tx.send(());
        });
        let result = tokio::select! {
            _ = rx => {
                Ok(())
            },
            _ = time::sleep(Duration::from_secs(2)) => {
                Err(())
            },
        };
        assert!(result.is_ok(), "Shutdown did not complete in time");
        match shutdown_task.await {
            Ok(_) => (),
            Err(_e) => {
                panic!("Shutdown task failed",);
            }
        }
    }
}
