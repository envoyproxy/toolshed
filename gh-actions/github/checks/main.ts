import * as core from '@actions/core'
import * as github from '@actions/github'
import {GitHub} from '@actions/github/lib/utils'
import {RequestParameters} from '@octokit/types'

interface Check {
  action: string
  id: string
  name: string
}

interface CheckMap {
  [key: string]: Check
}

interface CheckOutput {
  text: string
}

interface CheckConfig {
  name: string
  output: CheckOutput
  id: string
}

interface CheckConfigs {
  run: CheckConfig
  skipped: CheckConfig
}

type OctokitType = InstanceType<typeof GitHub>

async function createCheckRun(octokit: OctokitType, checkRun: RequestParameters): Promise<[string, number]> {
  const response = await octokit.checks.create(checkRun)
  return [checkRun.id as string, response.data.id]
}

const run = async (): Promise<void> => {
  try {
    const config: CheckConfigs = JSON.parse(core.getInput('config'))
    const checks: CheckMap = JSON.parse(core.getInput('checks'))
    const token = core.getInput('token')
    const textExtra = core.getInput('text-extra')
    const requests: Promise<[string, number]>[] = []
    const octokit = github.getOctokit(token)
    const nwo = process.env['GITHUB_REPOSITORY'] || '/'
    const [owner, repo] = nwo.split('/')
    Object.entries(checks).forEach(([check, checkConfig]) => {
      const name = checkConfig.name
      const id = check
      const checkRequestConfig: CheckConfig = checkConfig.action === 'SKIP' ? {...config.skipped} : {...config.run}
      checkRequestConfig.output.text =
        textExtra === '' ? checkRequestConfig.output.text : `${checkRequestConfig.output.text}\n${textExtra}`
      requests.push(createCheckRun(octokit, {...checkRequestConfig, id, name, owner, repo}))
    })
    const checkRunIds: [string, number][] = await Promise.all(requests)
    core.setOutput('checks', JSON.stringify(Object.fromEntries(checkRunIds), null, 0))
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
