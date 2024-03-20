import * as core from '@actions/core'
import * as github from '@actions/github'
import {GitHub} from '@actions/github/lib/utils'
import {RestEndpointMethodTypes} from '@octokit/rest'

type ChecksCreateParams = RestEndpointMethodTypes['checks']['create']['parameters']

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
}

interface CheckConfigs {
  run: CheckConfig
  skipped: CheckConfig
}

type OctokitType = InstanceType<typeof GitHub>

async function createCheckRun(octokit: OctokitType, checkRun: ChecksCreateParams): Promise<[string, number]> {
  const response = await octokit.rest.checks.create(checkRun)
  return [checkRun.id as string, response.data.id]
}

async function startChecks(
  octokit: OctokitType,
  checks: CheckMap,
  config: CheckConfigs,
  textExtra: string,
): Promise<void> {
  const nwo = process.env['GITHUB_REPOSITORY'] || '/'
  const [owner, repo] = nwo.split('/')
  const requests: Promise<[string, number]>[] = []
  Object.entries(checks).forEach(([check, checkConfig]) => {
    const name = checkConfig.name
    const id = check
    const checkRequestConfig: CheckConfig = checkConfig.action === 'SKIP' ? {...config.skipped} : {...config.run}
    const output = {...checkRequestConfig.output}
    output.text = textExtra === '' ? output.text : `${checkRequestConfig.output.text}\n${textExtra}`
    // eslint-disable-next-line @typescript-eslint/naming-convention
    requests.push(createCheckRun(octokit, {head_sha: '', ...checkRequestConfig, id, name, owner, repo, output}))
  })
  const checkRunIds: [string, number][] = await Promise.all(requests)
  core.setOutput('checks', JSON.stringify(Object.fromEntries(checkRunIds), null, 0))
}

async function updateCheckRun(octokit: OctokitType, checkConfig: Check, textExtra: string): Promise<[string, number]> {
  const nwo = process.env['GITHUB_REPOSITORY'] || '/'
  const [owner, repo] = nwo.split('/')
  const output = checkConfig.output || {text: '', summary: '', title: ''}
  output.text = textExtra === '' ? output.text : `${output.text}\n${textExtra}`
  const checkResponse = await octokit.rest.checks.listForRef({
    owner,
    repo,
    ref: checkConfig.head_sha || '',
    // eslint-disable-next-line @typescript-eslint/naming-convention
    check_name: checkConfig.name,
    filter: 'latest',
  })
  const text = checkResponse.data.check_runs[0].output.text || ''
  checkConfig.id = checkResponse.data.check_runs[0].id
  output.text = `${output.text}\n### Check started by\n${text.split('### Check started by')[1]}`
  checkConfig.output = output
  const response = await octokit.rest.checks.update({
    owner,
    repo,
    // eslint-disable-next-line @typescript-eslint/naming-convention
    check_run_id: checkConfig.id,
    ...checkConfig,
  })
  return [checkConfig.name, response.data.id]
}

async function updateChecks(octokit: OctokitType, checks: CheckMap, textExtra: string): Promise<void> {
  const requests: Promise<[string, number]>[] = []
  Object.values(checks).forEach((checkConfig) => {
    requests.push(updateCheckRun(octokit, checkConfig, textExtra))
  })
  const checkRunIds: [string, number][] = await Promise.all(requests)
  core.setOutput('checks', JSON.stringify(Object.fromEntries(checkRunIds), null, 0))
}

const run = async (): Promise<void> => {
  try {
    const action: string = core.getInput('action')
    const config: CheckConfigs = JSON.parse(core.getInput('config') || '{}')
    const checks: CheckMap = JSON.parse(core.getInput('checks'))
    const token = core.getInput('token')
    const textExtra = core.getInput('text-extra')
    const octokit = github.getOctokit(token)
    if (action === 'start') {
      await startChecks(octokit, checks, config, textExtra)
    } else if (action === 'update') {
      await updateChecks(octokit, checks, textExtra)
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
