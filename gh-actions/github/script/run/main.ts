import * as core from '@actions/core'
import {spawn} from 'child_process'
import * as fs from 'fs'
import {EOL} from 'os'

const script = async (cmd: string): Promise<void> => {
  try {
    const subprocess = spawn(cmd, {stdio: 'inherit', shell: true})
    subprocess.on('exit', (exitCode: number) => {
      process.exitCode = exitCode
    })
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`script/run stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`script/run failure: ${error}`)
  }
}

const run = async (): Promise<void> => {
  if (process.env.INPUT_KEY) {
    const key = process.env.INPUT_KEY.toUpperCase()

    if (process.env[`STATE_${key}`] !== undefined && process.env.INPUT_POST) {
      await script(process.env.INPUT_POST)
    } else {
      if (process.env.GITHUB_STATE && process.env.INPUT_RUN) {
        fs.appendFileSync(process.env.GITHUB_STATE, `${key}=true${EOL}`)
        await script(process.env.INPUT_RUN)
      }
    }
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
