import * as core from '@actions/core'
import nock from 'nock'
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

  const githubApiUrl = 'https://api.github.com'
  const repository = 'example/repository'
  const commentId = 12357

  // Nock the request
  nock(githubApiUrl).post(`/repos/${repository}/issues/comments/${commentId}/reactions`).reply(200, {})
  process.env['GITHUB_REPOSITORY'] = repository
})

afterEach(() => {
  // expect(nock.pendingMocks()).toEqual([])
  nock.isDone()
  nock.cleanAll()
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
