import {Octokit} from '@octokit/rest'
import * as core from '@actions/core'
import type {Endpoints} from '@octokit/types'
import {createAppAuth} from '@octokit/auth-app'
import {retry} from '@octokit/plugin-retry'

type listInstallationsResponse = Endpoints['GET /app/installations']['response']

const RETRIABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504])
const RETRIABLE_CODES = new Set(['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'ECONNREFUSED'])

const parseIntInput = (name: string, defaultVal: number): number => {
  const raw = core.getInput(name)
  if (raw === '') return defaultVal
  const parsed = parseInt(raw, 10)
  if (isNaN(parsed)) return defaultVal
  return Math.max(0, parsed)
}

const withRetry = async <T>(
  fn: () => Promise<T>,
  {retries, baseDelayMs, maxDelayMs}: {retries: number; baseDelayMs: number; maxDelayMs: number},
): Promise<T> => {
  let lastErr: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn()
    } catch (err: unknown) {
      lastErr = err
      const status = (err as {status?: number})?.status
      const code = (err as {code?: string})?.code
      const retriable =
        (status !== undefined && RETRIABLE_STATUSES.has(status)) ||
        (code !== undefined && RETRIABLE_CODES.has(code))
      if (!retriable || attempt === retries) break
      const expDelay = baseDelayMs * Math.pow(2, attempt)
      const delay = Math.min(expDelay, maxDelayMs) + Math.floor(Math.random() * 250)
      core.warning(
        `appauth attempt ${attempt + 1} failed (${status ?? code}); retrying in ${delay}ms`,
      )
      await new Promise((r) => setTimeout(r, delay))
    }
  }
  throw lastErr
}

const RetryingOctokit = Octokit.plugin(retry)

const run = async (): Promise<void> => {
  try {
    const privateKey = core.getInput('key')
    const appId = core.getInput('app_id')
    const providedToken = core.getInput('token')
    const tokenOk = core.getBooleanInput('token-ok')

    if (privateKey === '' || appId === '') {
      if (providedToken === '') {
        core.error('You must either provide app id/key or token, none provided')
        core.setFailed('No appauth token provided')
        return
      }
      if (!tokenOk) {
        core.warning('No app id/key provided, using token')
      }
      core.setOutput('token', providedToken)
      core.setSecret('token')
      return
    }

    const retries = parseIntInput('retries', 5)
    const retryBaseDelayMs = parseIntInput('retry-base-delay-ms', 1000)
    const retryMaxDelayMs = parseIntInput('retry-max-delay-ms', 15000)

    let installationId = parseInt(core.getInput('installation_id'))
    const appOctokit = new RetryingOctokit({
      authStrategy: createAppAuth,
      auth: {
        appId,
        privateKey,
      },
      baseUrl: process.env.GITHUB_API_URL || 'https://api.github.com',
      request: {
        retries,
        retryAfter: Math.ceil(retryBaseDelayMs / 1000),
      },
    })
    if (!installationId) {
      const installations: listInstallationsResponse = await appOctokit.apps.listInstallations()
      installationId = installations.data[0].id
    }
    const resp = await withRetry(
      () => appOctokit.auth({type: 'installation', installationId}),
      {retries, baseDelayMs: retryBaseDelayMs, maxDelayMs: retryMaxDelayMs},
    )

    // @ts-expect-error no typing for resp
    if (!resp || !resp.token) {
      throw new Error('Unable to authenticate')
    }

    // @ts-expect-error no typing for resp
    const token = resp.token
    core.setOutput('token', token)
    core.setSecret('token')

    // TODO: remove these
    core.setOutput('value', token)
    core.setSecret('value')
  } catch (error) {
    if (error instanceof Error) {
      core.error(error.message)
    }
    core.setFailed(`Appauth failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
