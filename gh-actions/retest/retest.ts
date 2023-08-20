import * as core from '@actions/core'
import * as github from '@actions/github'
import cachedProperty from './cached-property'
import * as types from './types'
import GithubRetestCommand from './github'
import AZPRetestCommand from './azp'
import RetestCommand from './base'

class RetestCommands {
  @cachedProperty
  get env(): types.Env | void | undefined {
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
      console.debug('No creds for AZP')
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

  addReaction = async (reaction: types.GithubReactionType = 'rocket'): Promise<void> => {
    if (!this.env) {
      return
    }
    const addReactionResponse: types.CreateReactionType['response'] = await this.env.octokit.reactions.createForIssueComment({
      owner: this.env.owner,
      repo: this.env.repo,
      comment_id: this.env.comment.id,
      content: reaction,
    })
    if ([200, 201].includes(addReactionResponse.status)) {
      console.debug(`Reacted to comment ${reaction}`)
    } else {
      console.error(`Failed reacting to comment ${reaction}`)
    }
  }

  retest = async (): Promise<void> => {
    let retested = 0
    let isRetest = false
    for (const retester of this.retesters) {
      if (retester.isRetest) {
        isRetest = true
      }
      retested += await retester.retest()
    }
    if (!isRetest) {
      return
    }
    if (retested === 0) {
      await this.addReaction('confused')
    } else {
      await this.addReaction()
    }
  }
}

export default RetestCommands
