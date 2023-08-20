import RetestCommand from './base'
import * as types from './types'

class AZPRetestCommand extends RetestCommand {
  name = 'AZP'

  constructor(env: types.Env) {
    super(env)
  }

  getRetestables = async (pr: types.PR): Promise<Array<types.Retest>> => {
    const response: types.ListChecksType['response'] = await this.env.octokit.checks.listForRef({
      owner: this.env.owner,
      repo: this.env.repo,
      ref: pr.commit,
    })
    // add err handling
    const retestables: Array<types.Retest> = []
    const azpRuns: types.ListChecksType['response']['data']['check_runs'] = response.data.check_runs.filter((run: any) => {
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

export default AZPRetestCommand
