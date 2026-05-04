import {Octokit} from '@octokit/rest'
import * as core from '@actions/core'
import type {Endpoints} from '@octokit/types'
import {createAppAuth} from '@octokit/auth-app'
import {withRetry, parseIntInput, type RetryOptions} from '../utils/retry'

type listInstallationsResponse = Endpoints['GET /app/installations']['response']

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

    const retries = parseIntInput(core.getInput('retries'), 'retries', 5, 'appauth', core.warning.bind(core))
    const baseDelayMs = parseIntInput(
      core.getInput('retry-base-delay-ms'),
      'retry-base-delay-ms',
      1000,
      'appauth',
      core.warning.bind(core),
    )
    const maxDelayMs = parseIntInput(
      core.getInput('retry-max-delay-ms'),
      'retry-max-delay-ms',
      15000,
      'appauth',
      core.warning.bind(core),
    )
    const retryOpts: RetryOptions = {retries, baseDelayMs, maxDelayMs}

    let installationId = parseInt(core.getInput('installation_id'))
    const appOctokit = new Octokit({
      authStrategy: createAppAuth,
      auth: {
        appId,
        privateKey,
      },
      baseUrl: process.env.GITHUB_API_URL || 'https://api.github.com',
    })
    if (!installationId) {
      const installations: listInstallationsResponse = await withRetry(
        () => appOctokit.apps.listInstallations(),
        retryOpts,
        'appauth',
        core.warning.bind(core),
      )
      installationId = installations.data[0].id
    }
    const resp = await withRetry(
      () => appOctokit.auth({type: 'installation', installationId}),
      retryOpts,
      'appauth',
      core.warning.bind(core),
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
