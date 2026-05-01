import * as core from '@actions/core'
import * as github from '@actions/github'
import type {GitHub} from '@actions/github/lib/utils'
import type {RestEndpointMethodTypes} from '@octokit/rest'
import {withRetry, parseIntInput, type RetryOptions} from '../../_shared/retry'

type ChecksCreateParams = RestEndpointMethodTypes['checks']['create']['parameters']
type ChecksCreateResponse = RestEndpointMethodTypes['checks']['create']['response']
type ChecksUpdateResponse = RestEndpointMethodTypes['checks']['update']['response']
type ChecksListForRefResponse = RestEndpointMethodTypes['checks']['listForRef']['response']

interface Check {
  action?: string
  // eslint-disable-next-line @typescript-eslint/naming-convention
  head_sha: string
  id: number
  name: string
  output?: CheckOutput
}

interface CheckMap {
  [key: string]: Check
}

interface CheckOutput {
  text: string
  title: string
  summary: string
}

interface CheckConfig {
  name: string
  output: CheckOutput
  id: number
  // eslint-disable-next-line @typescript-eslint/naming-convention
  head_sha?: string
}

interface CheckConfigs {
  run: CheckConfig
  skipped: CheckConfig
}

type OctokitType = InstanceType<typeof GitHub>

async function createCheckRun(
  octokit: OctokitType,
  checkRun: ChecksCreateParams,
  retryOpts: RetryOptions,
): Promise<[string, number]> {
  const response = await withRetry<ChecksCreateResponse>(
    () => octokit.rest.checks.create(checkRun),
    retryOpts,
    `checks.create(${checkRun.id as string})`,
    core.warning.bind(core),
  )
  return [checkRun.id as string, response.data.id]
}

async function startChecks(
  octokit: OctokitType,
  checks: CheckMap,
  config: CheckConfigs,
  textExtra: string,
  retryOpts: RetryOptions,
  failOnPartial: boolean,
): Promise<void> {
  const nwo = process.env['GITHUB_REPOSITORY'] || '/'
  const [owner, repo] = nwo.split('/')
  const entries = Object.entries(checks)
  const requests = entries.map(([id, checkConfig]) => {
    const name = checkConfig.name
    const checkRequestConfig: CheckConfig = checkConfig.action === 'SKIP' ? {...config.skipped} : {...config.run}
    const output = {...checkRequestConfig.output}
    output.text = textExtra === '' ? output.text : `${checkRequestConfig.output.text}\n${textExtra}`
    return createCheckRun(
      octokit,
      {
        ...checkRequestConfig,
        id,
        name,
        owner,
        repo,
        output,
        // eslint-disable-next-line @typescript-eslint/naming-convention
        head_sha: checkConfig.head_sha ?? checkRequestConfig.head_sha ?? '',
      },
      retryOpts,
    )
  })
  const results = await Promise.allSettled(requests)
  const succeeded: [string, number][] = []
  const failed: Record<string, string> = {}
  results.forEach((result, i) => {
    const [id] = entries[i]
    if (result.status === 'fulfilled') {
      succeeded.push(result.value)
    } else {
      failed[id] = String(result.reason)
    }
  })
  core.setOutput('checks', JSON.stringify(Object.fromEntries(succeeded), null, 0))
  core.setOutput('failed', JSON.stringify(failed, null, 0))
  const failedIds = Object.keys(failed)
  if (failedIds.length > 0) {
    if (succeeded.length === 0) {
      core.setFailed(`All checks failed: ${failedIds.join(', ')}`)
    } else if (failOnPartial) {
      core.setFailed(`Some checks failed: ${failedIds.join(', ')}`)
    } else {
      core.warning(`Some checks failed: ${failedIds.join(', ')}`)
    }
  }
}

async function updateCheckRun(
  octokit: OctokitType,
  checkConfig: Check,
  textExtra: string,
  retryOpts: RetryOptions,
): Promise<[string, number]> {
  const nwo = process.env['GITHUB_REPOSITORY'] || '/'
  const [owner, repo] = nwo.split('/')
  const output = checkConfig.output || {text: '', summary: '', title: ''}
  output.text = textExtra === '' ? output.text : `${output.text}\n${textExtra}`

  // Only call listForRef when the caller did not supply an id
  if (!checkConfig.id) {
    const checkResponse = await withRetry<ChecksListForRefResponse>(
      () =>
        octokit.rest.checks.listForRef({
          owner,
          repo,
          ref: checkConfig.head_sha || '',
          // eslint-disable-next-line @typescript-eslint/naming-convention
          check_name: checkConfig.name,
          filter: 'latest',
        }),
      retryOpts,
      `checks.listForRef(${checkConfig.name})`,
      core.warning.bind(core),
    )
    if (checkResponse.data.check_runs.length === 0) {
      throw new Error(`No existing check run found for "${checkConfig.name}" at ${checkConfig.head_sha}`)
    }
    const text = checkResponse.data.check_runs[0].output?.text || ''
    checkConfig.id = checkResponse.data.check_runs[0].id
    output.text = `${output.text}\n### Check started by\n${text.split('### Check started by')[1]}`
  }

  checkConfig.output = output
  const response = await withRetry<ChecksUpdateResponse>(
    () =>
      octokit.rest.checks.update({
        owner,
        repo,
        // eslint-disable-next-line @typescript-eslint/naming-convention
        check_run_id: checkConfig.id,
        ...checkConfig,
      }),
    retryOpts,
    `checks.update(${checkConfig.name})`,
    core.warning.bind(core),
  )
  return [checkConfig.name, response.data.id]
}

async function updateChecks(
  octokit: OctokitType,
  checks: CheckMap,
  textExtra: string,
  retryOpts: RetryOptions,
  failOnPartial: boolean,
): Promise<void> {
  const checkEntries = Object.values(checks)
  const requests: Promise<[string, number]>[] = checkEntries.map((checkConfig) =>
    updateCheckRun(octokit, checkConfig, textExtra, retryOpts),
  )
  const results = await Promise.allSettled(requests)
  const succeeded: [string, number][] = []
  const failed: Record<string, string> = {}
  results.forEach((result, i) => {
    if (result.status === 'fulfilled') {
      succeeded.push(result.value)
    } else {
      const checkId = checkEntries[i]?.name ?? `check-${i}`
      failed[checkId] = String(result.reason)
    }
  })
  core.setOutput('checks', JSON.stringify(Object.fromEntries(succeeded), null, 0))
  core.setOutput('failed', JSON.stringify(failed, null, 0))
  const failedIds = Object.keys(failed)
  if (failedIds.length > 0) {
    if (succeeded.length === 0) {
      core.setFailed(`All checks failed: ${failedIds.join(', ')}`)
    } else if (failOnPartial) {
      core.setFailed(`Some checks failed: ${failedIds.join(', ')}`)
    } else {
      core.warning(`Some checks failed: ${failedIds.join(', ')}`)
    }
  }
}

const run = async (): Promise<void> => {
  try {
    const action: string = core.getInput('action')
    const config: CheckConfigs = JSON.parse(core.getInput('config') || '{}')
    const checks: CheckMap = JSON.parse(core.getInput('checks'))
    const token = core.getInput('token')
    const textExtra = core.getInput('text-extra')
    const failOnPartial = core.getInput('fail-on-partial') === 'true'

    const retries = parseIntInput(core.getInput('retries'), 'retries', 5, 'checks', core.warning.bind(core))
    const baseDelayMs = parseIntInput(
      core.getInput('retry-base-delay-ms'),
      'retry-base-delay-ms',
      1000,
      'checks',
      core.warning.bind(core),
    )
    const maxDelayMs = parseIntInput(
      core.getInput('retry-max-delay-ms'),
      'retry-max-delay-ms',
      15000,
      'checks',
      core.warning.bind(core),
    )
    const retryOpts: RetryOptions = {retries, baseDelayMs, maxDelayMs}

    const octokit = github.getOctokit(token)

    if (action === 'start') {
      await startChecks(octokit, checks, config, textExtra, retryOpts, failOnPartial)
    } else if (action === 'update') {
      await updateChecks(octokit, checks, textExtra, retryOpts, failOnPartial)
    }
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`checks stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`checks failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
