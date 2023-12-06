import * as core from '@actions/core'
import {minimatch} from 'minimatch'

interface BooleanMap {
  [key: string]: boolean
}

interface CheckConfig {
  paths: string[]
  push: string
}

interface CheckConfigList {
  [key: number]: CheckConfig
}

function globMatchPaths(paths: string[], globs: string[]): boolean {
  return paths.some(path => globs.some(glob => minimatch(path, glob)))
}

const run = async (): Promise<void> => {
  try {
    const config: CheckConfigList = JSON.parse(core.getInput('config'))
    const paths = JSON.parse(core.getInput('paths'))
    const event = core.getInput('event')
    const checks: BooleanMap = {}

    Object.entries(config).forEach(([check, checkConfig]) => {
      checks[check] = false
      if (!checkConfig) {
        checks[check] = true
        return
      }
      if (!checkConfig.paths || (event === 'push' && checkConfig.push === 'always')) {
        checks[check] = true
        return
      }
      if (event === 'push' && checkConfig.push === 'never') {
        checks[check] = false
        return
      }
      if (checkConfig.paths) {
        checks[check] = globMatchPaths(paths, checkConfig.paths)
        return
      }
      checks[check] = true
    })
    core.setOutput('runs', JSON.stringify(checks, null, 0))
  } catch (error) {
    const e = error as Record<'stderr', string>
    if (e.stderr) {
      console.error(`torun stderr: ${e.stderr}`)
    }
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`torun failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
