import fetchMock from 'fetch-mock'
import * as core from '@actions/core'
import * as github from '@actions/github'

import run, {isExcluded, parseArgs} from '../retest'

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
  const githubMock = fetchMock.createInstance().post(
    `${githubApiUrl}${apiPath}`,
    {ok: true},
    {
      headers: {
        accept: 'application/vnd.github.v3+json',
      },
    },
  )

  const testokit = github.getOctokit('12345', {request: {fetch: githubMock.fetchHandler.bind(githubMock)}})

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

describe('parseArgs', () => {
  it('parses check names', () => {
    expect(parseArgs(' all check/name-1 check.name_2 ')).toEqual(['all', 'check/name-1', 'check.name_2'])
  })

  it('parses empty args', () => {
    expect(parseArgs('')).toEqual([])
  })

  it.each([['$(id)'], ['check;id'], ['`id`'], ['--flag'], ['check name && id']])('rejects %s', (args: string) => {
    expect(() => parseArgs(args)).toThrow(TypeError)
  })
})

describe('isExcluded', () => {
  it('matches an exact or prefix token', () => {
    expect(isExcluded('Envoy/Verify', ['Envoy/Verify'])).toBe(true)
    expect(isExcluded('Envoy/Verify / examples', ['Envoy/Verify'])).toBe(true)
    expect(isExcluded('Envoy/Checks', ['Envoy/Verify'])).toBe(false)
  })
  it('is false for an empty exclude list', () => {
    expect(isExcluded('anything', [])).toBe(false)
  })
  // Regression: backends must match the original plain name, not a display form.
  // The AZP backend renders names as `[pipeline](link)`; it filters on the plain
  // `pipeline` name, so excluding `pipeline` works (matching `[pipeline](link)` would not).
  it('matches the plain pipeline name, not a markdown display form', () => {
    expect(isExcluded('macos', ['macos'])).toBe(true)
    expect(isExcluded('[macos](https://dev.azure.com/x)', ['macos'])).toBe(false)
  })
})
