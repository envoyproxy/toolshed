import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import {spawn} from '@await/spawn'

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return

    const encode = core.getInput('encode')
    const decode = core.getInput('decode')
    const options = core.getInput('options')
    const envVar = core.getInput('env_var')
    const printResult = core.getInput('print-result')

    const filter = core.getInput('filter')
    if (!filter || filter === '') return
    core.debug(`input: ${input}`)
    core.debug(`encode: ${encode}`)
    core.debug(`decode: ${decode}`)
    core.debug(`options: ${options}`)
    core.debug(`filter: ${filter}`)
    let encodePipe = ''
    if (encode && encode !== 'false') {
      encodePipe = '| base64 -w0'
    }
    let decodePipe = ''
    if (decode && decode !== 'false') {
      decodePipe = '| base64 -d'
    }
    // preferably use spawn/stdin
    const shellCommand = `printf "%s" '${input}' ${decodePipe} | jq ${options} '${filter}' ${encodePipe}`
    core.debug(`Running shell command: ${shellCommand}`)
    const proc = spawn('sh', ['-c', shellCommand])
    const response = await proc
    const stdout = response.stdout
    core.setOutput('value', stdout.trim())
    if (envVar) {
      process.env[envVar] = stdout
      core.exportVariable(envVar, stdout.trim())
    }
    if (printResult && printResult !== 'false') {
      process.stdout.write(stdout.trim())
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
