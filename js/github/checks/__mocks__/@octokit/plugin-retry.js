// Mock @octokit/plugin-retry to be a no-op in tests.
// This prevents Bottleneck timers from leaking and keeping Jest alive,
// while still allowing our own withRetry wrapper to be exercised.
const retry = function retry() {
  return {}
}
retry.VERSION = '0.0.0-mock'
module.exports = { retry }
