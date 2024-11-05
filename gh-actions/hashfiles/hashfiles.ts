import * as core from '@actions/core'
import {hashFiles} from '@actions/glob'
import path from 'path'

const run = async (): Promise<void> => {
  try {
    const workingDirectory = core.getInput('working-directory')
    if (workingDirectory && workingDirectory.trim() !== '') {
      const fullPath = path.resolve(workingDirectory)
      process.chdir(fullPath)
    }
    const files = core.getInput('files')
    if (!files || files === '') return
    const failEmpty = core.getInput('failEmpty')
    const format = core.getInput('format')
    const delimiter = core.getInput('delimiter')
    const verbose = core.getInput('verbose')
    let parsedFiles
    if (format == 'json') {
      parsedFiles = JSON.parse(`${files}`)
    } else {
      parsedFiles = files.split(delimiter)
    }
    console.log(
      `hashfiles: ${parsedFiles.join(
        ',',
      )} (verbose=${verbose}, format=${format}, failEmpty=${failEmpty}, delimiter=${delimiter})`,
    )
    const stdout = await hashFiles(parsedFiles.join('\n'))
    if (!stdout && failEmpty) {
      throw new Error(`hashfiles failure: No files matched ${parsedFiles.join(',')}`)
    }
    console.log(`Generated hash: ${stdout}`)
    core.setOutput('value', stdout)
  } catch (error) {
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`hashfiles failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
