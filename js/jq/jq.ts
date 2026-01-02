import {runGitHubAction} from './src/github-action'

const run = runGitHubAction

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
