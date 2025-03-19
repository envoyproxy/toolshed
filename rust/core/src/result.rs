use std::error::Error;

pub type EmptyResult<E = Box<dyn Error + Send + Sync>> = Result<(), E>;

#[macro_export]
macro_rules! all_ok {
    ($results:expr) => {{
        let errors: Vec<_> = $results
            .into_iter()
            .filter_map(|result| match result {
                Ok(Ok(_)) => None,
                Ok(Err(e)) => Some(anyhow::anyhow!("{}", e)),
                Err(join_err) => Some(anyhow::anyhow!("{}", join_err)),
            })
            .collect();

        if errors.is_empty() {
            Ok(())
        } else {
            let combined_error = errors
                .into_iter()
                .enumerate()
                .fold(String::new(), |acc, (i, err)| {
                    format!("{}Error {}: {}\n", acc, i + 1, err)
                });
            Err(anyhow::anyhow!("Multiple listener errors: \n{}", combined_error).into())
        }
    }};
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::Result;
    use tokio::task::JoinError;

    #[tokio::test]
    async fn test_all_ok_when_all_results_are_ok() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> =
            vec![Ok(Ok(())), Ok(Ok(())), Ok(Ok(()))];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_all_ok_with_one_error() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Ok(())),
            Ok(Err(anyhow::anyhow!("Test error"))),
            Ok(Ok(())),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("Test error"));
        assert!(err.contains("Error 1:"));
    }

    #[tokio::test]
    async fn test_all_ok_with_multiple_errors() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Err(anyhow::anyhow!("First error"))),
            Ok(Ok(())),
            Ok(Err(anyhow::anyhow!("Second error"))),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("First error"));
        assert!(err.contains("Second error"));
        assert!(err.contains("Error 1:"));
        assert!(err.contains("Error 2:"));
    }

    #[tokio::test]
    async fn test_all_ok_with_join_errors() {
        let handle = tokio::spawn(async { Err::<(), &str>("Task error") });

        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Ok(())),
            handle
                .await
                .map(|res| res.map_or_else(|e| Err(anyhow::anyhow!("{}", e)), Ok)),
            Ok(Ok(())),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("Task error"));
    }

    #[tokio::test]
    async fn test_all_ok_with_empty_results() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_all_ok_with_mixed_errors() {
        let handle = tokio::spawn(async { Err::<(), &str>("Task join error") });

        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Err(anyhow::anyhow!("Regular error"))),
            handle
                .await
                .map(|res| res.map_or_else(|e| Err(anyhow::anyhow!("{}", e)), Ok)),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("Regular error"));
        assert!(err.contains("Task join error"));
        assert!(err.contains("Error 1:"));
        assert!(err.contains("Error 2:"));
    }

    #[tokio::test]
    async fn test_all_ok_error_formatting() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Err(anyhow::anyhow!("Error one"))),
            Ok(Err(anyhow::anyhow!("Error two"))),
        ];

        let result: EmptyResult = all_ok!(results);
        let err = result.unwrap_err().to_string();

        assert!(err.contains("Multiple listener errors:"));
        assert!(err.contains("Error 1: Error one"));
        assert!(err.contains("Error 2: Error two"));
    }

    #[tokio::test]
    async fn test_all_ok_with_different_error_types() {
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Err(anyhow::anyhow!("Anyhow error"))),
            Ok(Err(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                "IO error",
            )
            .into())),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("Anyhow error"));
        assert!(err.contains("IO error"));
    }

    #[tokio::test]
    async fn test_all_ok_with_actual_tokio_tasks() {
        // Simulate some async tasks that might succeed or fail
        let task1 = tokio::spawn(async { Ok::<(), anyhow::Error>(()) });

        let task2 =
            tokio::spawn(async { Err::<(), anyhow::Error>(anyhow::anyhow!("Task 2 failed")) });

        let task3 = tokio::spawn(async {
            tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
            Ok::<(), anyhow::Error>(())
        });

        // Wait for all tasks to complete
        let results = vec![task1.await, task2.await, task3.await];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("Task 2 failed"));
    }

    // Test with EmptyResult type
    #[tokio::test]
    async fn test_all_ok_with_empty_result_type() {
        let results: Vec<Result<EmptyResult, JoinError>> = vec![
            Ok(Ok(())),
            Ok(Err(anyhow::anyhow!("EmptyResult error").into())),
            Ok(Ok(())),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("EmptyResult error"));
    }

    #[tokio::test]
    async fn test_all_ok_with_actual_join_error() {
        // Create a task that will be canceled, causing a JoinError
        let handle = tokio::spawn(async {
            tokio::time::sleep(tokio::time::Duration::from_secs(30)).await;
            Ok::<(), anyhow::Error>(())
        });

        // Cancel the task
        handle.abort();

        // This will result in a JoinError directly
        let results: Vec<Result<Result<(), anyhow::Error>, JoinError>> = vec![
            Ok(Ok(())),
            handle.await, // This will be Err(JoinError) due to cancellation
            Ok(Ok(())),
        ];

        let result: EmptyResult = all_ok!(results);
        assert!(result.is_err());

        let err = result.unwrap_err().to_string();
        assert!(err.contains("cancelled")); // Join errors from cancellation usually mention "cancelled"
    }
}
