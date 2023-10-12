import RetestCommand from './base'
import * as types from './types'

class GithubRetestCommand extends RetestCommand {
  name = 'Github'

  constructor(env: types.Env) {
    super(env)
  }

  getRetestables = async (pr: types.PR): Promise<Array<types.Retest>> => {
    // Get failed Workflow runs for the latest PR commit
    const runs = await this.listWorkflowRunsForPR(pr)
    if (!runs) return []
    const failedRuns = runs.filter((run: any) => {
      return run.conclusion === 'cancelled' || run.conclusion === 'failure' || run.conclusion === 'timed_out'
    })
    const retestables: Array<types.Retest> = []
    for (const run of failedRuns) {
      retestables.push({
        name: run.name || 'unknown',
        url: run.url,
        octokit: true,
      })
    }
    return retestables
  }
}

export default GithubRetestCommand
