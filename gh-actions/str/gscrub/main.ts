import * as core from '@actions/core'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'
import CryptoJS from 'crypto-js'

const run = async (): Promise<void> => {
  try {
    const inputString = core.getInput('string')
    const seed = core.getInput('seed')
    const reverse = core.getBooleanInput('reverse')
    if (!inputString || inputString === '') return
    const replacements = core.getInput('replacements')
    let scrubbedString = inputString
    yaml.load(replacements).forEach((item: string) => {
      const replacement = CryptoJS.SHA256(item + seed).toString(CryptoJS.enc.Hex)
      if (!reverse) {
        scrubbedString = scrubbedString.replace(`${item}{{`, `☠${replacement}☠`)
      } else {
        scrubbedString = scrubbedString.replace(`☠${replacement}☠`, `${item}{{`)
      }
    })
    core.setOutput('string', scrubbedString)
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`str/gscrub stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`str/gscrub failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
