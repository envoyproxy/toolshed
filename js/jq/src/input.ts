import fs from 'fs'
import os from 'os'
import * as path from 'path'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error no typing for js-yaml
import * as yaml from 'js-yaml'

declare const atob: (encodedString: string) => string

/**
 * Process input string based on format and decode options
 */
export function processInput(input: string, inputFormat: string, decode: boolean): string {
  let mangledInput = input
  if (inputFormat.endsWith('-path')) {
    if (input.startsWith('/tmp') && process.platform === 'win32') {
      mangledInput = path.join(os.tmpdir(), path.basename(input))
    }
    mangledInput = fs.readFileSync(mangledInput, 'utf-8')
  } else if (decode) {
    mangledInput = decodeURIComponent(escape(atob(input)))
  }
  if (inputFormat.startsWith('yaml')) {
    const yamlObject = yaml.load(mangledInput)
    mangledInput = JSON.stringify(yamlObject, null, 2)
  }
  return mangledInput
}
