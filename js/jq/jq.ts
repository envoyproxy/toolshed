import {run_github_action} from './src/action'

const run = run_github_action

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
