import fs from 'fs'
import os from 'os'
import {exec} from 'child_process'
import tmp from 'tmp'
import type {JqConfig, JqResult, TempFileHandles} from './types'
import {processInput} from './input-processor'
import {buildFilter, cleanupTempFiles} from './filter-builder'

/**
 * Execute jq with the given configuration
 */
export async function runJq(config: JqConfig): Promise<JqResult> {
  return new Promise((resolve, reject) => {
    try {
      // Process input
      const mangledInput = processInput(config.input, config.inputFormat, config.decode)

      // Build filter with imports
      const {filterArg, filterFunArg, tempHandles} = buildFilter(
        config.filter,
        config.filterFun,
        config.useTmpFileForFilter,
      )

      // Build shell command
      const shellCommand = buildShellCommand(
        mangledInput,
        config.options,
        filterFunArg,
        filterArg,
        config.useTmpFile,
        tempHandles,
      )

      // Execute jq
      const proc = exec(shellCommand, (error, stdout, stderr) => {
        cleanupTempFiles(tempHandles)

        if (error) {
          reject(error)
          return
        }

        resolve({
          output: stdout,
          stderr: stderr || undefined,
        })
      })

      proc.on('exit', (code) => {
        if (code !== 0) {
          reject(new Error(`Child process exited with code ${code}`))
        }
      })
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * Build the shell command for executing jq
 */
function buildShellCommand(
  input: string,
  options: string,
  filterFunArg: string,
  filterArg: string,
  useTmpFile: boolean,
  tempHandles: TempFileHandles,
): string {
  let shellCommand = `printf '%s' '${input}' | jq ${options} ${filterFunArg} ${filterArg}`

  if (os.platform() === 'win32' || useTmpFile) {
    tempHandles.tmpFile = tmp.fileSync()
    fs.writeFileSync(tempHandles.tmpFile.name, input)
    shellCommand = `cat ${tempHandles.tmpFile.name} | jq ${options} ${filterFunArg} ${filterArg}`
  }

  return shellCommand
}
