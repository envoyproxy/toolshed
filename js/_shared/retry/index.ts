export const RETRIABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504])
export const RETRIABLE_CODES = new Set(['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'ECONNREFUSED'])

export interface RetryOptions {
  retries: number
  baseDelayMs: number
  maxDelayMs: number
}

export const parseRetryAfter = (err: unknown): number | undefined => {
  const headers = (err as {response?: {headers?: Record<string, string | undefined>}})?.response?.headers
  const raw = headers?.['retry-after']
  const secs = raw === undefined ? NaN : parseInt(raw, 10)
  return Number.isFinite(secs) && secs >= 0 ? secs * 1000 : undefined
}

export const parseIntInput = (
  raw: string,
  name: string,
  defaultVal: number,
  label: string,
  warn: (msg: string) => void,
): number => {
  if (raw === '') return defaultVal
  const parsed = parseInt(raw, 10)
  if (isNaN(parsed)) return defaultVal
  if (parsed < 0) {
    warn(`${label}: '${name}' is negative (${parsed}); coerced to 0`)
    return 0
  }
  return parsed
}

export const withRetry = async <T>(
  fn: () => Promise<T>,
  {retries, baseDelayMs, maxDelayMs}: RetryOptions,
  label: string,
  warn: (msg: string) => void,
): Promise<T> => {
  let lastErr: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn()
    } catch (err: unknown) {
      lastErr = err
      const e = err as Record<string, unknown>
      const status = (e?.status ?? (e?.response as Record<string, unknown>)?.status) as number | undefined
      const code = e?.code as string | undefined
      const retriable =
        (status !== undefined && RETRIABLE_STATUSES.has(status)) || (code !== undefined && RETRIABLE_CODES.has(code))
      if (!retriable || attempt >= retries) {
        if (retriable && retries > 0) {
          warn(`${label}: exhausted ${retries} retries (last error: ${status ?? code})`)
        }
        break
      }
      const expDelay = baseDelayMs * Math.pow(2, attempt)
      const headerDelay = parseRetryAfter(err)
      const baseDelay = headerDelay !== undefined ? Math.max(headerDelay, expDelay) : expDelay
      const rawDelay = baseDelay + Math.floor(Math.random() * 250)
      const delay = Math.min(rawDelay, maxDelayMs)
      warn(`${label}: attempt ${attempt + 1} failed (${status ?? code}); retrying in ${delay}ms`)
      await new Promise((r) => setTimeout(r, delay))
    }
  }
  throw lastErr
}
