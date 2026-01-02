import * as core from '@actions/core'
import os from 'os'
import * as path from 'path'
import type {JqConfig} from './types'
import {run_jq} from './runner'
import {process_output, write_output, type OutputOptions} from './output'

/**
 * GitHub Actions integration for jq
 */
export async function run_github_action(): Promise<void> {
  try {
    const input = core.getInput('input')
    if (!input || input === '') return
    const config = build_config_from_inputs()
    core.debug(`Running jq with config: ${JSON.stringify(config)}`)
    const result = await run_jq(config)
    const output_options: OutputOptions = {
      encode: core.getBooleanInput('encode'),
      print_output: core.getBooleanInput('print-output'),
      print_result: core.getBooleanInput('print-result'),
      trim_result: core.getBooleanInput('trim-result'),
      output_path: get_output_path(),
    }
    const processed_output = process_output(result.output, output_options)
    core.setOutput('value', processed_output)
    const env_var = core.getInput('env_var')
    if (env_var) {
      process.env[env_var] = processed_output
      core.exportVariable(env_var, processed_output)
    }
    if (output_options.print_output) {
      process.stdout.write(output_options.trim_result ? processed_output.trim() : processed_output)
    }
    write_output(processed_output, output_options.output_path, core.summary)
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
function build_config_from_inputs(): JqConfig {
  let output_path = core.getInput('output-path')
  if (output_path && output_path.startsWith('/tmp') && process.platform === 'win32') {
    output_path = path.join(os.tmpdir(), path.basename(output_path))
  }
  return {
    input: core.getInput('input'),
    filter: core.getInput('filter'),
    options: core.getInput('options'),
    input_format: core.getInput('input-format'),
    use_tmp_file: core.getBooleanInput('use-tmp-file'),
    use_tmp_file_for_filter: core.getBooleanInput('use-tmp-file-filter'),
    filter_fun: core.getInput('filter-fun') || undefined,
    decode: core.getBooleanInput('decode'),
    encode: core.getBooleanInput('encode'),
    print_output: core.getBooleanInput('print-output'),
    print_result: core.getBooleanInput('print-result'),
    trim_result: core.getBooleanInput('trim-result'),
    env_var: core.getInput('env_var') || undefined,
    output_path: output_path || undefined,
  }
}

/**
 * Get output path with Windows path handling
 */
function get_output_path(): string | undefined {
  let output_path = core.getInput('output-path')
  if (!output_path) {
    return undefined
  }
  if (output_path && output_path.startsWith('/tmp') && process.platform === 'win32') {
    output_path = path.join(os.tmpdir(), path.basename(output_path))
  }
  return output_path
}
