import fs from 'fs'
import {exec} from 'child_process'
import tmp from 'tmp'

declare const btoa: (rawString: string) => string

/**
 * Options for processing output
 */
export interface OutputOptions {
  encode: boolean
  print_output: boolean
  print_result: boolean
  trim_result: boolean
  output_path?: string
}

/**
 * Process jq output according to options
 */
export function process_output(output: string, options: OutputOptions): string {
  let processed_output = options.trim_result ? output.trim() : output
  if (options.print_result) {
    const tmp_file_result = tmp.fileSync()
    fs.writeFileSync(tmp_file_result.name, processed_output)
    const shell_command = `cat ${tmp_file_result.name} | jq -C '.'`
    exec(shell_command, (_, result) => {
      process.stdout.write(options.trim_result ? result.trim() : result)
      tmp_file_result.removeCallback()
    })
  }
  if (options.encode) {
    processed_output = btoa(unescape(encodeURIComponent(processed_output)))
  }
  return processed_output
}

/**
 * Write output to specified destination
 */
export function write_output(
  output: string,
  output_path: string | undefined,
  summary_writer?: {addRaw: (text: string) => {write: () => void}},
): void {
  if (!output_path) {
    return
  }
  if (output_path === 'GITHUB_STEP_SUMMARY') {
    if (summary_writer) {
      summary_writer.addRaw(output).write()
    }
  } else {
    fs.writeFileSync(output_path, output)
  }
}
