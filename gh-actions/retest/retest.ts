import * as core from '@actions/core'
import * as github from '@actions/github'

const run = async (): Promise<void> => {
  try {
    const token = process.env['GITHUB_TOKEN'] || core.getInput('token')
    if (!token || token === '') return

    // Create the octokit client
    const octokit = github.getOctokit(token)
    const nwo = process.env['GITHUB_REPOSITORY'] || '/'
    const [owner, repo] = nwo.split('/')
    const issue = github.context.payload.issue
    if (!issue) return

    const pullRequest = issue.pull_request
    if (!pullRequest) return

    const comment = github.context.payload.comment
    if (!comment) return

    let isRetest = false
    comment.body.split('\r\n').forEach((line: string) => {
      if (line.startsWith('/retest')) {
        if (!line.startsWith('/retest envoy')) {
          isRetest = true
          return
        }
      }
    })
    if (!isRetest) return

    const pullRequestResponse = await octokit.request(pullRequest.url)
    const fullPullRequest = pullRequestResponse.data
    if (!fullPullRequest) return

    const prNumber = fullPullRequest.number
    const prBranch = fullPullRequest.head.ref
    const prCommit = fullPullRequest.head.sha

    console.log(`Running /retest command for PR #${prNumber}`)
    console.log(`PR branch: ${prBranch}`)
    console.log(`Latest PR commit: ${prCommit}`)

    // Get failed Workflow runs for the latest PR commit

    // https://octokit.github.io/rest.js/v18#actions-list-workflow-runs-for-repo
    const branchWorkflowRunsResponse = await octokit.actions.listWorkflowRunsForRepo({
      owner,
      repo,
      branch: prBranch,
    })

    const branchWorkflowRuns = branchWorkflowRunsResponse.data
    if (!branchWorkflowRuns) return

    const runs = branchWorkflowRuns.workflow_runs
    if (!runs) return

    const runsForLatestCommit = runs.filter(run => {
      return run.head_sha === prCommit
    })

    const runsToRetry = runsForLatestCommit.filter(run => {
      return run.conclusion === 'cancelled' || run.conclusion === 'failure' || run.conclusion === 'timed_out'
    })

    // Iterate over each failed run and retry its failed jobs

    for (const run of runsToRetry) {
      console.log(`Retrying failed job: ${run.name}`)
      const rerunURL = `POST ${run.url}/rerun-failed-jobs`
      const rerunResponse = await octokit.request(rerunURL)
      console.log(`Retried: ${rerunResponse.status}`)
    }

    // Add emoji reaction to the comment
    // https://octokit.github.io/rest.js/v18#reactions-create-for-issue-comment
    const addReactionResponse = await octokit.reactions.createForIssueComment({
      owner,
      repo,
      comment_id: comment.id,
      content: 'rocket',
    })
    console.log(`Reacted to comment: ${addReactionResponse.status}`)
  } catch (error) {
    if (error instanceof Error) {
      console.error(error.message)
    }
    core.setFailed(`retest-action failure: ${error}`)
  }
}

// Don't auto-execute in the test environment
if (process.env['NODE_ENV'] !== 'test') {
  run()
}

export default run
