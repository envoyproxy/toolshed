import fetchMock from 'fetch-mock'
import * as core from '@actions/core'
import * as github from '@actions/github'

import run from '../retest'

beforeEach(() => {
  jest.resetModules()
  jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
    if (name === 'token') return '12345'
    if (name === 'azp_token') return '678910'
    if (name === 'azp_org') return 'AZPORG'
    if (name === 'comment-id') return '12357'
    return ''
  })

  const repository = 'example/repository'
  const githubApiUrl = 'https://api.github.com'
  const commentId = 12357
  const apiPath = `/repos/${repository}/issues/comments/${commentId}/reactions`
  const githubMock = fetchMock.sandbox().post(
    `${githubApiUrl}${apiPath}`,
    {ok: true},
    {
      headers: {
        accept: 'application/vnd.github.v3+json',
      },
    },
  )

  const testokit = github.getOctokit('12345', {request: {fetch: githubMock}})

  jest.spyOn(github, 'getOctokit').mockImplementation(() => {
    return testokit
  })

  process.env['GITHUB_REPOSITORY'] = repository
})

describe('retest action', () => {
  it('runs', async () => {
    await expect(run()).resolves.not.toThrow()
  })

  it('completes a full run', async () => {
    // https://developer.github.com/v3/activity/events/types/#issuecommentevent
    await run()
  })
})
