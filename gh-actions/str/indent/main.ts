import * as core from '@actions/core'

const run = async (): Promise<void> => {
  try {
    const inputString = core.getInput('string')
    if (!inputString || inputString === '') return
    const indent = parseInt(core.getInput('indent'))
    if (indent === 0) {
      core.setOutput('string', inputString)
      return
    }
    const indentation = ' '.repeat(indent)
    const indentedString = inputString.replace(/^/gm, indentation)
    core.setOutput('string', indentedString)
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`str/indent stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`str/indent failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
