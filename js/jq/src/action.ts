import * as core from '@actions/core'
import os from 'os'
import * as path from 'path'
import type {JqConfig} from './types'
import {runJq} from './runner'
import {processOutput, writeOutput, type OutputOptions} from './output'

/**
 * GitHub Actions integration for jq
 */
export async function runGitHubAction(): Promise<void> {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return
    const config = buildConfigFromInputs()
    core.debug(`Running jq with config: ${JSON.stringify(config)}`)
    const result = await runJq(config)
    const outputOptions: OutputOptions = {
      encode: core.getBooleanInput('encode'),
      printOutput: core.getBooleanInput('print-output'),
      printResult: core.getBooleanInput('print-result'),
      trimResult: core.getBooleanInput('trim-result'),
      outputPath: getOutputPath(),
    }
    const processedOutput = processOutput(result.output, outputOptions)
    core.setOutput('value', processedOutput)
    const envVar = core.getInput('env_var')
    if (envVar) {
      process.env[envVar] = processedOutput
      core.exportVariable(envVar, processedOutput)
    }
    if (outputOptions.printOutput) {
      process.stdout.write(outputOptions.trimResult ? processedOutput.trim() : processedOutput)
    }
    writeOutput(processedOutput, outputOptions.outputPath, core.summary)
    if (result.stderr) {
      process.stderr.write(`stderr: ${result.stderr}`)
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

/**
 * Build JqConfig from GitHub Actions inputs
 */
function buildConfigFromInputs(): JqConfig {
  let outputPath = core.getInput('output-path')
  if (outputPath && outputPath.startsWith('/tmp') && process.platform === 'win32') {
    outputPath = path.join(os.tmpdir(), path.basename(outputPath))
  }
  return {
    input: core.getInput('input'),
    filter: core.getInput('filter'),
    options: core.getInput('options'),
    inputFormat: core.getInput('input-format'),
    useTmpFile: core.getBooleanInput('use-tmp-file'),
    useTmpFileForFilter: core.getBooleanInput('use-tmp-file-filter'),
    filterFun: core.getInput('filter-fun') || undefined,
    decode: core.getBooleanInput('decode'),
    encode: core.getBooleanInput('encode'),
    printOutput: core.getBooleanInput('print-output'),
    printResult: core.getBooleanInput('print-result'),
    trimResult: core.getBooleanInput('trim-result'),
    envVar: core.getInput('env_var') || undefined,
    outputPath: outputPath || undefined,
  }
}

/**
 * Get output path with Windows path handling
 */
function getOutputPath(): string | undefined {
  let outputPath = core.getInput('output-path')
  if (!outputPath) {
    return undefined
  }
  if (outputPath && outputPath.startsWith('/tmp') && process.platform === 'win32') {
    outputPath = path.join(os.tmpdir(), path.basename(outputPath))
  }
  return outputPath
}
