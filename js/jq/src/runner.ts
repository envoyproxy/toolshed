import fs from 'fs'
import os from 'os'
import {exec} from 'child_process'
import tmp from 'tmp'
import type {JqConfig, JqResult, TempFileHandles} from './types'
import {process_input} from './input'
import {build_filter, cleanup_temp_files} from './filter'

/**
 * Execute jq with the given configuration
 */
export async function run_jq(config: JqConfig): Promise<JqResult> {
  return new Promise((resolve, reject) => {
    try {
      const mangled_input = process_input(config.input, config.input_format, config.decode)
      const {filter_arg, filter_fun_arg, temp_handles} = build_filter(
        config.filter,
        config.filter_fun,
        config.use_tmp_file_for_filter,
      )
      const shell_command = build_shell_command(
        mangled_input,
        config.options,
        filter_fun_arg,
        filter_arg,
        config.use_tmp_file,
        temp_handles,
      )
      const proc = exec(shell_command, (error, stdout, stderr) => {
        cleanup_temp_files(temp_handles)
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
function build_shell_command(
  input: string,
  options: string,
  filter_fun_arg: string,
  filter_arg: string,
  use_tmp_file: boolean,
  temp_handles: TempFileHandles,
): string {
  let shell_command = `printf '%s' '${input}' | jq ${options} ${filter_fun_arg} ${filter_arg}`
  if (os.platform() === 'win32' || use_tmp_file) {
    temp_handles.tmp_file = tmp.fileSync()
    fs.writeFileSync(temp_handles.tmp_file.name, input)
    shell_command = `cat ${temp_handles.tmp_file.name} | jq ${options} ${filter_fun_arg} ${filter_arg}`
  }
  return shell_command
}
