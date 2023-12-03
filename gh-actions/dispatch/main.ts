import * as core from '@actions/core'
import * as github from '@actions/github'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

const run = async (): Promise<void> => {
  try {
    const repository = core.getInput('repository')
    if (!repository || repository === '') return
    const ref = core.getInput('ref')
    const providedInputs = core.getInput('inputs')
    const token = core.getInput('token')
    const workflow = core.getInput('workflow')
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
    const request = {
      action: `POST /repos/${repository}/actions/workflows/${workflow}/dispatches`,
      params: {
        ref,
        inputs,
      },
    }
    const octokit = github.getOctokit(token)
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
