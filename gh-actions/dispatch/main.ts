import {createAppAuth} from '@octokit/auth-app'
import * as core from '@actions/core'
import {Endpoints} from '@octokit/types'
import {Octokit} from '@octokit/rest'
import * as github from '@actions/github'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

type listInstallationsResponse = Endpoints['GET /app/installations']['response']

const run = async (): Promise<void> => {
  try {
    const repository = core.getInput('repository')
    if (!repository || repository === '') return
    const ref = core.getInput('ref')
    const providedInputs = core.getInput('inputs')
    const privateKey = core.getInput('key')
    const appId = core.getInput('app_id')
    let installationId = parseInt(core.getInput('installation_id'))
    const workflow = core.getInput('workflow')
    const appOctokit = new Octokit({
      authStrategy: createAppAuth,
      auth: {
        appId,
        privateKey,
      },
      baseUrl: process.env.GITHUB_API_URL || 'https://api.github.com',
    })
    if (!installationId) {
      const installations: listInstallationsResponse = await appOctokit.apps.listInstallations()
      installationId = installations.data[0].id
    }
    const resp = await appOctokit.auth({
      type: 'installation',
      installationId,
    })

    const inputs: {[key: string]: string | number | boolean} = {}

    if (providedInputs) {
      const parsedInputs = yaml.load(providedInputs)

      for (const [key, value] of Object.entries(parsedInputs)) {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          inputs[key] = value
        } else {
          inputs[key] = JSON.stringify(value)
        }
      }
    }

    // @ts-expect-error
    if (!resp || !resp.token) {
      throw new Error('Unable to authenticate')
    }
    const request = {
      action: `POST /repos/${repository}/actions/workflows/${workflow}/dispatches`,
      params: {
        ref,
        inputs,
      },
    }
    // @ts-expect-error
    const octokit = github.getOctokit(resp.token)
    await octokit.request(request.action, request.params)
    console.log(`Dispatched ${repository}/${workflow}`)
  } catch (error) {
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`dispatch failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
