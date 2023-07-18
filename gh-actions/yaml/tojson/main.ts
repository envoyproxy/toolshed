import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

const run = async (): Promise<void> => {
  try {
    const yamlString = core.getInput('yaml')
    if (!yamlString || yamlString === '') return
    const yamlObject = yaml.load(yamlString)
    const jsonString = JSON.stringify(yamlObject)
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
