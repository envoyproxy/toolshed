import fs from 'fs'
import os from 'os'
import * as path from 'path'
import tmp from 'tmp'
import type {TempFileHandles} from './types'

/**
 * Result of building a filter with temp files and arguments
 */
export interface FilterBuildResult {
  filterArg: string
  filterFunArg: string
  tempHandles: TempFileHandles
}

/**
 * Build jq filter with imports and manage temporary files
 */
export function buildFilter(
  filter: string,
  filterFun: string | undefined,
  useTmpFileForFilter: boolean,
): FilterBuildResult {
  const tempHandles: TempFileHandles = {}
  let mangledFilter = filter
  const modPath = path.join(__dirname, '../../../jq')
  mangledFilter = `import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${mangledFilter}`
  let filterFunArg = `-L ${modPath}`
  if (filterFun) {
    tempHandles.tmpDirFun = tmp.dirSync()
    const funFilename = 'fun.jq'
    const funPath = path.join(tempHandles.tmpDirFun.name, funFilename)
    fs.writeFileSync(funPath, filterFun)
    filterFunArg = `-L ${tempHandles.tmpDirFun.name}`
    mangledFilter = `import "fun" as fun; ${mangledFilter}`
  }
  let filterArg: string
  if (os.platform() === 'win32' || useTmpFileForFilter) {
    tempHandles.tmpFileFilter = tmp.fileSync()
    fs.writeFileSync(tempHandles.tmpFileFilter.name, mangledFilter)
    filterArg = `-f ${tempHandles.tmpFileFilter.name}`
  } else {
    filterArg = `'${mangledFilter}'`
  }
  return {
    filterArg,
    filterFunArg,
    tempHandles,
  }
}

/**
 * Clean up temporary files
 */
export function cleanupTempFiles(tempHandles: TempFileHandles): void {
  if (tempHandles.tmpFile) {
    tempHandles.tmpFile.removeCallback()
  }
  if (tempHandles.tmpFileFilter) {
    tempHandles.tmpFileFilter.removeCallback()
  }
  if (tempHandles.tmpDirFun) {
    tempHandles.tmpDirFun.removeCallback()
  }
}
