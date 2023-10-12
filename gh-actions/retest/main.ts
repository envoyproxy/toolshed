import * as core from '@actions/core'
import RetestCommands from './retest'

const run = async (): Promise<void> => {
  try {
    const retesters = new RetestCommands()
    await retesters.retest()
  } catch (error) {
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`retest-action failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export {RetestCommands}
export default run
