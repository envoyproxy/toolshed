import * as core from '@actions/core'
import fs from 'fs'
import os from 'os'
import tmp from 'tmp'
import {exec} from 'child_process'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return

    const useTmpFile = core.getBooleanInput('use-tmp-file')
    const encode = core.getBooleanInput('encode')
    const decode = core.getBooleanInput('decode')
    const options = core.getInput('options')
    const envVar = core.getInput('env_var')
    const printResult = core.getBooleanInput('print-result')
    const filter = core.getInput('filter')
    const sanitize = core.getBooleanInput('sanitize-input')
    const inputFormat = core.getInput('input-format')

    if (!filter || filter === '') return
    core.debug(`input: ${input}`)
    core.debug(`encode: ${encode}`)
    core.debug(`decode: ${decode}`)
    core.debug(`options: ${options}`)
    core.debug(`filter: ${filter}`)
    let encodePipe = ''
    if (encode) {
      encodePipe = '| base64 -w0'
    }
    let decodePipe = ''
    if (decode) {
      decodePipe = '| base64 -d'
    }
    let sanitizedInput
    if (sanitize && inputFormat === 'json') {
      sanitizedInput = JSON.stringify(JSON.parse(input), null, 2)
    } else if (inputFormat === 'yaml') {
      const yamlObject = yaml.load(input)
      sanitizedInput = JSON.stringify(yamlObject, null, 2)
    } else {
      sanitizedInput = input
    }

    let tmpFile: tmp.FileResult
    let shellCommand = `printf '%s' '${sanitizedInput}' ${decodePipe} | jq ${options} '${filter}' ${encodePipe}`
    if (os.platform() === 'win32' || useTmpFile) {
      tmpFile = tmp.fileSync()
      fs.writeFileSync(tmpFile.name, sanitizedInput)
      shellCommand = `cat ${tmpFile.name} ${decodePipe} | jq ${options} '${filter}' ${encodePipe}`
    }
    core.debug(`Running shell command: ${shellCommand}`)
    const proc = exec(shellCommand, (error, stdout, stderr) => {
      if (tmpFile) {
        tmpFile.removeCallback()
      }
      if (error) {
        console.error(`Error: ${error}`)
        return
      }
      core.setOutput('value', stdout.trim())
      if (envVar) {
        process.env[envVar] = stdout
        core.exportVariable(envVar, stdout.trim())
      }
      if (printResult) {
        process.stdout.write(stdout.trim())
      }
      if (stderr) {
        core.error(`stderr: ${stderr}`)
      }
    })
    proc.on('exit', code => {
      if (code !== 0) {
        core.setFailed(`Child process exited with code ${code}`)
      }
    })
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
