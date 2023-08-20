import {RestEndpointMethodTypes} from '@octokit/rest'
import {Endpoints} from '@octokit/types'
import {GitHub} from '@actions/github/lib/utils'

type GithubReactionType = 'rocket' | '+1' | '-1' | 'laugh' | 'confused' | 'heart' | 'hooray' | 'eyes'
type WorkflowRunsType = Endpoints['GET /repos/{owner}/{repo}/actions/runs']['response']
type CreateReactionType = RestEndpointMethodTypes['reactions']['createForIssueComment']
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

export {Env, PR, Retest, WorkflowRunsType, ListChecksType, GithubReactionType, CreateReactionType}
