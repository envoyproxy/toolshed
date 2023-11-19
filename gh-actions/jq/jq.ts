import * as core from '@actions/core'
import fs from 'fs'
import os from 'os'
import tmp from 'tmp'
import {exec} from 'child_process'
// eslint-disable-next-line @typescript-eslint/ban-ts-ignore
// @ts-ignore
import * as yaml from 'js-yaml'

declare const atob: (encodedString: string) => string
declare const btoa: (rawString: string) => string

const run = async (): Promise<void> => {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return

    const useTmpFile = core.getBooleanInput('use-tmp-file')
    const useTmpFileForFilter = core.getBooleanInput('use-tmp-file-filter')
    const encode = core.getBooleanInput('encode')
    const decode = core.getBooleanInput('decode')
    const options = core.getInput('options')
    const envVar = core.getInput('env_var')
    const printOutput = core.getBooleanInput('print-output')
    const printResult = core.getBooleanInput('print-result')
    const filter = core.getInput('filter')
    const inputFormat = core.getInput('input-format')

    let mangledInput = input
    if (inputFormat.endsWith('-path')) {
      mangledInput = fs.readFileSync(input, 'utf-8')
      console.log(`read input from file ${mangledInput}`)
    } else if (decode) {
      mangledInput = decodeURIComponent(escape(atob(input)))
    }
    if (inputFormat.startsWith('yaml')) {
      console.log(`parsing yaml`)
      const yamlObject = yaml.load(mangledInput)
      mangledInput = JSON.stringify(yamlObject, null, 2)
    }
    let tmpFile: tmp.FileResult
    let tmpFileFilter: tmp.FileResult
    let filterArg

    if (os.platform() === 'win32' || useTmpFileForFilter) {
      tmpFileFilter = tmp.fileSync()
      fs.writeFileSync(tmpFileFilter.name, filter)
      filterArg = `-f ${tmpFileFilter.name}`
    } else {
      filterArg = `'${filter}'`
    }
    let shellCommand = `printf '%s' '${mangledInput}' | jq ${options} ${filterArg}`
    if (os.platform() === 'win32' || useTmpFile) {
      tmpFile = tmp.fileSync()
      fs.writeFileSync(tmpFile.name, mangledInput)
      shellCommand = `cat ${tmpFile.name} | jq ${options} ${filterArg}`
    }
    core.debug(`Running shell command: ${shellCommand}`)
    const proc = exec(shellCommand, (error, stdout, stderr) => {
      if (tmpFile) {
        tmpFile.removeCallback()
      }
      if (tmpFileFilter) {
        tmpFileFilter.removeCallback()
      }
      if (error) {
        console.error(`Error: ${error}`)
        return
      }
      let output = stdout.trim()
      if (printResult) {
        const tmpFileResult = tmp.fileSync()
        fs.writeFileSync(tmpFileResult.name, output)
        shellCommand = `cat ${tmpFileResult.name} | jq -C '.'`
        exec(shellCommand, (_, result) => {
          process.stdout.write(result.trim())
          tmpFileResult.removeCallback()
        })
      }
      if (encode) {
        output = btoa(unescape(encodeURIComponent(stdout)))
      }
      core.setOutput('value', output)
      if (envVar) {
        process.env[envVar] = output
        core.exportVariable(envVar, output)
      }
      if (printOutput) {
        process.stdout.write(output.trim())
      }
      if (stderr) {
        process.stderr.write(`stderr: ${stderr}`)
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
