import * as core from '@actions/core'
import os from 'os'
import * as path from 'path'
import type {JqConfig} from './types'
import {runJq} from './runner'
import {processOutput, writeOutput, type OutputOptions} from './output'

/**
 * GitHub Actions integration for jq
 * Reads inputs from GitHub Actions, runs jq, and sets outputs
 */
export async function runGitHubAction(): Promise<void> {
  try {
    // Read input
    const input = core.getInput('input')
    if (!input || input === '') return

    // Build configuration from GitHub Actions inputs
    const config = buildConfigFromInputs()

    // Debug logging
    core.debug(`Running jq with config: ${JSON.stringify(config)}`)

    // Run jq
    const result = await runJq(config)

    // Process output
    const outputOptions: OutputOptions = {
      encode: core.getBooleanInput('encode'),
      printOutput: core.getBooleanInput('print-output'),
      printResult: core.getBooleanInput('print-result'),
      trimResult: core.getBooleanInput('trim-result'),
      outputPath: getOutputPath(),
    }

    const processedOutput = processOutput(result.output, outputOptions)

    // Set GitHub Actions outputs
    core.setOutput('value', processedOutput)

    // Export environment variable if requested
    const envVar = core.getInput('env_var')
    if (envVar) {
      process.env[envVar] = processedOutput
      core.exportVariable(envVar, processedOutput)
    }

    // Print output if requested
    if (outputOptions.printOutput) {
      process.stdout.write(outputOptions.trimResult ? processedOutput.trim() : processedOutput)
    }

    // Write to file or summary
    writeOutput(processedOutput, outputOptions.outputPath, core.summary)

    // Log stderr if present
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
