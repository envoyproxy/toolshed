import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import {load} from 'js-yaml'

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return
    const elif = core.getInput('elif')
    const defaultValue = core.getInput('default')
    const parsed = load(elif, 'utf8')
    let output = input
    if (parsed[input]) {
      output = parsed[input]
    } else if (defaultValue) {
      output = defaultValue
    }
    core.setOutput('value', output)
    console.log(output)
  } catch (error) {
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`elif failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
