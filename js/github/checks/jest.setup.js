// @actions/github v9 imports fetch directly from undici, bypassing globalThis.fetch
// which is what nock's FetchInterceptor patches. Redirect undici.fetch to always
// call the current globalThis.fetch so nock interceptors work in tests.
const undici = require('undici')
undici.fetch = function (...args) {
  return globalThis.fetch(...args)
}
