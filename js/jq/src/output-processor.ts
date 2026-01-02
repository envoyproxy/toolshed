import fs from 'fs'
import {exec} from 'child_process'
import tmp from 'tmp'

declare const btoa: (rawString: string) => string

/**
 * Options for processing output
 */
export interface OutputOptions {
  encode: boolean
  printOutput: boolean
  printResult: boolean
  trimResult: boolean
  outputPath?: string
}

/**
 * Process jq output according to options
 */
export function processOutput(output: string, options: OutputOptions): string {
  let processedOutput = options.trimResult ? output.trim() : output

  // Print colored result if requested
  if (options.printResult) {
    const tmpFileResult = tmp.fileSync()
    fs.writeFileSync(tmpFileResult.name, processedOutput)
    const shellCommand = `cat ${tmpFileResult.name} | jq -C '.'`
    exec(shellCommand, (_, result) => {
      process.stdout.write(options.trimResult ? result.trim() : result)
      tmpFileResult.removeCallback()
    })
  }

  // Encode output if requested
  if (options.encode) {
    processedOutput = btoa(unescape(encodeURIComponent(processedOutput)))
  }

  return processedOutput
}

/**
 * Write output to specified destination
 */
export function writeOutput(
  output: string,
  outputPath: string | undefined,
  summaryWriter?: {addRaw: (text: string) => {write: () => void}},
): void {
  if (!outputPath) {
    return
  }

  if (outputPath === 'GITHUB_STEP_SUMMARY') {
    if (summaryWriter) {
      summaryWriter.addRaw(output).write()
    }
  } else {
    fs.writeFileSync(outputPath, output)
  }
}
