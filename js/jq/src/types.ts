/**
 * Configuration for jq execution
 */
export interface JqConfig {
  input: string
  filter: string
  options: string
  inputFormat: string
  useTmpFile: boolean
  useTmpFileForFilter: boolean
  filterFun?: string
  decode: boolean
  encode: boolean
  printOutput: boolean
  printResult: boolean
  trimResult: boolean
  envVar?: string
  outputPath?: string
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
  tmpFile?: {name: string; removeCallback: () => void}
  tmpFileFilter?: {name: string; removeCallback: () => void}
  tmpDirFun?: {name: string; removeCallback: () => void}
}
