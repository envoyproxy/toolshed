import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import {spawn} from '@await/spawn'

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return

    const options = core.getInput('options')
    const envVar = core.getInput('env_var')

    const filter = core.getInput('filter')
    if (!filter || filter === '') return

    core.info(`input: ${input}`)
    core.info(`options: ${options}`)
    core.info(`filter: ${filter}`)

    // preferably use spawn/stdin
    const shellCommand = `echo '${input}' | jq ${options} '${filter}'`
    console.log(`Running shell command: ${shellCommand}`)
    const proc = spawn('sh', ['-c', shellCommand])
    const response = await proc
    const stdout = response.stdout
    core.setOutput('value', stdout)
    if (envVar) {
      process.env[envVar] = stdout
      core.exportVariable(envVar, stdout)
    }
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`jq stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`jq failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
