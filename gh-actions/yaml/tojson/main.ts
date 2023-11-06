import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

const run = async (): Promise<void> => {
  try {
    const yamlString = core.getInput('yaml')
    if (!yamlString || yamlString === '') return
    const compact = core.getBooleanInput('compact')
    const yamlObject = yaml.load(yamlString)
    const jsonString = compact ? JSON.stringify(yamlObject) : JSON.stringify(yamlObject, null, 2)
    core.setOutput('json', jsonString)
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
