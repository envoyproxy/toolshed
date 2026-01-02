import fs from 'fs'
import os from 'os'
import * as path from 'path'
import tmp from 'tmp'
import type {TempFileHandles} from './types'

/**
 * Result of building a filter with temp files and arguments
 */
export interface FilterBuildResult {
  filter_arg: string
  filter_fun_arg: string
  temp_handles: TempFileHandles
}

/**
 * Build jq filter with imports and manage temporary files
 */
export function build_filter(
  filter: string,
  filter_fun: string | undefined,
  use_tmp_file_for_filter: boolean,
): FilterBuildResult {
  const temp_handles: TempFileHandles = {}
  let mangled_filter = filter
  const mod_path = path.join(__dirname, '../../../jq')
  mangled_filter = `import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${mangled_filter}`
  let filter_fun_arg = `-L ${mod_path}`
  if (filter_fun) {
    temp_handles.tmp_dir_fun = tmp.dirSync()
    const fun_filename = 'fun.jq'
    const fun_path = path.join(temp_handles.tmp_dir_fun.name, fun_filename)
    fs.writeFileSync(fun_path, filter_fun)
    filter_fun_arg = `-L ${temp_handles.tmp_dir_fun.name}`
    mangled_filter = `import "fun" as fun; ${mangled_filter}`
  }
  let filter_arg: string
  if (os.platform() === 'win32' || use_tmp_file_for_filter) {
    temp_handles.tmp_file_filter = tmp.fileSync()
    fs.writeFileSync(temp_handles.tmp_file_filter.name, mangled_filter)
    filter_arg = `-f ${temp_handles.tmp_file_filter.name}`
  } else {
    filter_arg = `'${mangled_filter}'`
  }
  return {
    filter_arg,
    filter_fun_arg,
    temp_handles,
  }
}

/**
 * Clean up temporary files
 */
export function cleanup_temp_files(temp_handles: TempFileHandles): void {
  if (temp_handles.tmp_file) {
    temp_handles.tmp_file.removeCallback()
  }
  if (temp_handles.tmp_file_filter) {
    temp_handles.tmp_file_filter.removeCallback()
  }
  if (temp_handles.tmp_dir_fun) {
    temp_handles.tmp_dir_fun.removeCallback()
  }
}
