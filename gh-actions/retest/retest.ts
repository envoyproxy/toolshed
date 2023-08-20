import * as core from '@actions/core'
import * as github from '@actions/github'
import {RestEndpointMethodTypes} from '@octokit/rest'
import {Endpoints, OctokitResponse} from '@octokit/types'
import axios, {AxiosResponse} from 'axios'
import {GitHub} from '@actions/github/lib/utils'

type GithubReactionType = 'rocket' | '+1' | '-1' | 'laugh' | 'confused' | 'heart' | 'hooray' | 'eyes'
type WorkflowRunsType = Endpoints['GET /repos/{owner}/{repo}/actions/runs']['response']
type CreateReactionType = RestEndpointMethodTypes['reactions']['createForIssueComment']

function cachedProperty(_: unknown, key: string, descriptor: PropertyDescriptor): PropertyDescriptor {
  const originalGetter = descriptor.get
  if (!originalGetter) {
    throw new Error('The decorated property must have a getter.')
  }

  // Use a Symbol for storing the cached value on the instance
  const cachedValueKey = Symbol(`__cached_${key}`)
  /* eslint-disable  @typescript-eslint/no-explicit-any */
  descriptor.get = function(this: any): any {
    if (!this[cachedValueKey]) {
      this[cachedValueKey] = originalGetter.call(this)
    }
    return this[cachedValueKey]
  }
  return descriptor
}

type ListChecksType = RestEndpointMethodTypes['checks']['listForRef']

type Retest = {
  name: string
  octokit: boolean
  url: string
  method?: string
  config?: any
}

type PR = {
  number: number
  branch: string
  commit: string
}

type OctokitType = InstanceType<typeof GitHub>

type Env = {
  octokit: OctokitType
  token: string
  comment: OctokitType['context']['payload']['issue']['comment']
  issue: OctokitType['context']['payload']['issue']
  pr: OctokitType['context']['payload']['issue']['pull_request']
  nwo: string
  owner: string
  repo: string
  azpOrg: string | undefined
  azpToken: string | undefined
}

class RetestCommand {
  public env: Env
  public name = ''

  constructor(env: Env) {
    this.env = env
  }

  getPR = async (): Promise<PR | void> => {
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
      console.log(`Failed parsing env`)
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

  retestExternal = async (check: Retest): Promise<any | void> => {
    let response: AxiosResponse
    if (check.method == 'patch') {
      console.log(`CONFIG: ${check.config}`)
      console.log(`URL ${check.url}`)
      try {
        response = await axios.patch(check.url, {}, check.config)
        /* eslint-disable  prettier/prettier */
      } catch (error: any) {
        if (!axios.isAxiosError(error) || !error.response) {
          console.log('No response received')
          return
        }
        console.log(error.response.data)
        console.log(error.response.status)
        console.log(error.response.headers)
        return
      }
    } else {
      return
    }
    return response.data
  }

  retestOctokit = async (check: Retest): Promise<void> => {
    const rerunURL = `POST ${check.url}/rerun-failed-jobs`
    const rerunResponse = await this.env.octokit.request(rerunURL)
    if ([200, 201].includes(rerunResponse.status)) {
      console.log(`Retry success: (${check.name})`)
    } else {
      console.log(`Retry failed: (${check.name}) ... ${rerunResponse.status}`)
    }
  }

  retestRuns = async (pr: PR, retestables: Array<Retest>): Promise<void> => {
    console.log(`Running /retest command for PR #${pr.number}`)
    console.log(`PR branch: ${pr.branch}`)
    console.log(`Latest PR commit: ${pr.commit}`)
    for (const check of retestables) {
      console.log(`Retesting failed job: ${check.name}`)
      if (!check.octokit) {
        await this.retestExternal(check)
      } else {
        await this.retestOctokit(check)
      }
    }
  }

  getRetestables = async (pr: PR): Promise<Array<Retest>> => {
    console.log(pr)
    return []
  }

  listWorkflowRunsForPR = async (pr: PR): Promise<WorkflowRunsType['data']['workflow_runs'] | void> => {
    const response: WorkflowRunsType = await this.env.octokit.actions.listWorkflowRunsForRepo({
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

class GithubRetestCommand extends RetestCommand {
  name = 'Github'

  constructor(env: Env) {
    super(env)
  }

  getRetestables = async (pr: PR): Promise<Array<Retest>> => {
    // Get failed Workflow runs for the latest PR commit
    const runs = await this.listWorkflowRunsForPR(pr)
    if (!runs) return []
    const failedRuns = runs.filter((run: any) => {
      return run.conclusion === 'cancelled' || run.conclusion === 'failure' || run.conclusion === 'timed_out'
    })
    const retestables: Array<Retest> = []
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

class AZPRetestCommand extends RetestCommand {
  name = 'AZP'

  constructor(env: Env) {
    super(env)
  }

  getRetestables = async (pr: PR): Promise<Array<Retest>> => {
    const response: ListChecksType['response'] = await this.env.octokit.checks.listForRef({
      owner: this.env.owner,
      repo: this.env.repo,
      ref: pr.commit,
    })
    // add err handling
    const retestables: Array<Retest> = []
    const azpRuns: ListChecksType['response']['data']['check_runs'] = response.data.check_runs.filter((run: any) => {
      return run.app.slug === 'azure-pipelines'
    })
    const checks: Array<any> = []
    const checkIds: Set<string> = new Set()
    for (const check of azpRuns) {
      if (!check.external_id) {
        continue
      }
      checkIds.add(check.external_id)
      if (check.name.endsWith(')')) {
        checks.push(check)
      }
    }

    for (const checkId of checkIds) {
      const subchecks = checks.filter((c: any) => {
        return c.external_id === checkId
      })
      if (Object.keys(subchecks).length === 0) {
        continue
      }
      const subcheck = subchecks[0].name.split(' ')[0]
      const link = this.getAZPLink(checkId)
      const name = `[${subcheck}](${link})`
      const config = {
        headers: {
          authorization: `basic ${this.env.azpToken}`,
          'content-type': 'application/json;odata=verbose',
        },
      }
      for (const check of subchecks) {
        if (check.conclusion && check.conclusion !== 'success') {
          const [_, buildId, project] = checkId.split('|')
          const url = `https://dev.azure.com/${this.env.azpOrg}/${project}/_apis/build/builds/${buildId}?retry=true&api-version=6.0`
          retestables.push({
            url,
            name,
            config,
            method: 'patch',
            octokit: false,
          })
        }
      }
    }
    return retestables
  }

  getAZPLink = (checkId: string): string => {
    const [_, buildId, project] = checkId.split('|')
    return `https://dev.azure.com/${this.env.azpOrg}/${project}/_build/results?buildId=${buildId}&view=results`
  }
}

class RetestCommands {
  @cachedProperty
  get env(): Env | void | undefined {
    let azpOrg, azpToken
    const token = process.env['GITHUB_TOKEN'] || core.getInput('token')
    if (!token || token === '') return
    const octokit = github.getOctokit(token)
    // Create the octokit client
    const nwo = process.env['GITHUB_REPOSITORY'] || '/'
    const [owner, repo] = nwo.split('/')
    const issue = github.context.payload.issue
    if (!issue) return
    const pr = issue.pull_request
    if (!pr) return
    const comment = github.context.payload.comment
    if (!comment) return
    if (core.getInput('azp_org') && core.getInput('azp_token')) {
      azpOrg = core.getInput('azp_org')
      azpToken = core.getInput('azp_token')
    } else {
      console.log('No creds for AZP')
    }
    return {
      token,
      octokit,
      nwo,
      owner,
      repo,
      issue,
      pr,
      comment,
      azpOrg,
      azpToken,
    }
  }

  get retesters(): Array<RetestCommand> {
    if (!this.env) {
      return []
    }
    const retesters: Array<RetestCommand> = [new GithubRetestCommand(this.env)]
    if (this.env.azpOrg) {
      retesters.push(new AZPRetestCommand(this.env))
    }
    return retesters
  }

  addReaction = async (reaction: GithubReactionType = 'rocket'): Promise<void> => {
    if (!this.env) {
      return
    }
    const addReactionResponse: CreateReactionType['response'] = await this.env.octokit.reactions.createForIssueComment({
      owner: this.env.owner,
      repo: this.env.repo,
      comment_id: this.env.comment.id,
      content: reaction,
    })
    if ([200, 201].includes(addReactionResponse.status)) {
      console.log(`Reacted to comment ${reaction}`)
    } else {
      console.log(`Failed reacting to comment ${reaction}`)
    }
  }

  retest = async (): Promise<void> => {
    let retested = 0
    for (const retester of this.retesters) {
      retested += await retester.retest()
    }
    if (retested === 0) {
      await this.addReaction('confused')
    } else {
      await this.addReaction()
    }
  }
}

const run = async (): Promise<void> => {
  try {
    const retesters = new RetestCommands()
    await retesters.retest()
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
