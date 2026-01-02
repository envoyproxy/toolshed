/**
 * Configuration for jq execution
 */
export interface JqConfig {
  input: string
  filter: string
  options: string
  input_format: string
  use_tmp_file: boolean
  use_tmp_file_for_filter: boolean
  filter_fun?: string
  decode: boolean
  encode: boolean
  print_output: boolean
  print_result: boolean
  trim_result: boolean
  env_var?: string
  output_path?: string
}

/**
 * Result from jq execution
 */
export interface JqResult {
  output: string
  stderr?: string
}

/**
 * Temporary file handles for cleanup
 */
export interface TempFileHandles {
  tmp_file?: {name: string; removeCallback: () => void}
  tmp_file_filter?: {name: string; removeCallback: () => void}
  tmp_dir_fun?: {name: string; removeCallback: () => void}
}
