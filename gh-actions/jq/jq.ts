import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import {spawn} from '@await/spawn'

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return

    const options = core.getInput('options')

    const filter = core.getInput('filter')
    if (!filter || filter === '') return

    core.info(`input: ${input}`)
    core.info(`options: ${options}`)
    core.info(`filter: ${filter}`)

    const args: string[] = []
    args.push(options)
    args.push(`${filter}`)

    console.log(`jq ${args.join(' ')}`)
    console.log(`> '${input}'`)
    const proc = spawn('jq', args)
    proc.process.stdin.setEncoding('utf-8')
    proc.process.stdin.write(`${input}`)
    proc.process.stdin.end()
    const response = await proc
    const stdout = response.stdout
    core.setOutput('value', stdout)
  } catch (error) {
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
