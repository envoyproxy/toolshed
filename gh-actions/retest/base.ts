import {OctokitResponse} from '@octokit/types'
import axios, {AxiosResponse} from 'axios'
import cachedProperty from './cached-property'
import * as types from './types'


class RetestCommand {
  public env: types.Env
  public name = ''

  constructor(env: types.Env) {
    this.env = env
  }

  getPR = async (): Promise<types.PR | void> => {
    if (!this.env.pr || !this.env.pr.url) {
      return
    }
    const response: OctokitResponse<any> = await this.env.octokit.request(this.env.pr.url)
    const data = response.data
    if (!data) return
    return {
      number: data.number,
      branch: data.head.ref,
      commit: data.head.sha,
    }
  }

  @cachedProperty
  get isRetest(): boolean {
    let isRetest = false
    this.env.comment.body.split('\r\n').forEach((line: string) => {
      if (line.startsWith('/retest')) {
        if (!line.startsWith('/retest envoy')) {
          isRetest = true
          return
        }
      }
    })
    return isRetest
  }

  retest = async (): Promise<number> => {
    if (!this.env) {
      console.error(`Failed parsing env`)
      return 0
    }
    if (!this.isRetest) return 0
    const pr = await this.getPR()
    if (!pr) {
      return 0
    }
    const retestables = await this.getRetestables(pr)
    if (Object.keys(retestables).length === 0) {
      return 0
    }
    await this.retestRuns(pr, retestables)
    return Object.keys(retestables).length
  }

  retestExternal = async (check: types.Retest): Promise<any | void> => {
    let response: AxiosResponse
    if (check.method == 'patch') {
      try {
        response = await axios.patch(check.url, {}, check.config)
        /* eslint-disable  prettier/prettier */
      } catch (error: any) {
        if (!axios.isAxiosError(error) || !error.response) {
          console.error('No response received')
          return
        }
        console.error(`External API call failed: ${check.url}`)
        console.error(error.response.status)
        console.error(error.response.data)
        return
      }
    } else {
      return
    }
    return response.data
  }

  retestOctokit = async (check: types.Retest): Promise<void> => {
    const rerunURL = `POST ${check.url}/rerun-failed-jobs`
    const rerunResponse = await this.env.octokit.request(rerunURL)
    if ([200, 201].includes(rerunResponse.status)) {
      console.debug(`Retry success: (${check.name})`)
    } else {
      console.error(`Retry failed: (${check.name}) ... ${rerunResponse.status}`)
    }
  }

  retestRuns = async (pr: types.PR, retestables: Array<types.Retest>): Promise<void> => {
    console.debug(`Running /retest command for PR #${pr.number}`)
    console.debug(`PR branch: ${pr.branch}`)
    console.debug(`Latest PR commit: ${pr.commit}`)
    for (const check of retestables) {
      console.debug(`Retesting failed job: ${check.name}`)
      if (!check.octokit) {
        await this.retestExternal(check)
      } else {
        await this.retestOctokit(check)
      }
    }
  }

  getRetestables = async (_: types.PR): Promise<Array<types.Retest>> => {
    return []
  }

  listWorkflowRunsForPR = async (pr: types.PR): Promise<types.WorkflowRunsType['data']['workflow_runs'] | void> => {
    const response: types.WorkflowRunsType = await this.env.octokit.actions.listWorkflowRunsForRepo({
      owner: this.env.owner,
      repo: this.env.repo,
      branch: pr.branch,
    })

    const workflowRuns = response.data
    if (!workflowRuns) return

    const runs = workflowRuns.workflow_runs
    if (!runs) return

    return runs.filter((run: any) => {
      return run.head_sha === pr.commit
    })
  }
}

export default RetestCommand
