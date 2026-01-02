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
export function process_input(input: string, input_format: string, decode: boolean): string {
  let mangled_input = input
  if (input_format.endsWith('-path')) {
    if (input.startsWith('/tmp') && process.platform === 'win32') {
      mangled_input = path.join(os.tmpdir(), path.basename(input))
    }
    mangled_input = fs.readFileSync(mangled_input, 'utf-8')
  } else if (decode) {
    mangled_input = decodeURIComponent(escape(atob(input)))
  }
  if (input_format.startsWith('yaml')) {
    const yaml_object = yaml.load(mangled_input)
    mangled_input = JSON.stringify(yaml_object, null, 2)
  }
  return mangled_input
}
