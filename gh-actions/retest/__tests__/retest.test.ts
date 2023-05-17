import * as github from '@actions/github'
import * as core from '@actions/core'
import {WebhookPayload} from '@actions/github/lib/interfaces'
import nock from 'nock'
import run from '../retest'

beforeEach(() => {
  jest.resetModules()
  jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
    if (name === 'token') return '12345'
    return ''
  })

  process.env['GITHUB_REPOSITORY'] = 'example/repository'
})

afterEach(() => {
  expect(nock.pendingMocks()).toEqual([])
  nock.isDone()
  nock.cleanAll()
})

describe('retest action', () => {
  it('runs', async () => {
    await expect(run()).resolves.not.toThrow()
  })

  it('completes a full run', async () => {
    // https://developer.github.com/v3/activity/events/types/#issuecommentevent
    github.context.payload = {
      action: 'created',
      issue: {
        number: 1,
        pull_request: {
          url: 'https://api.github.com/repos/example/repository/pulls/1234',
        },
      },
      comment: {
        id: 1,
        user: {
          login: 'monalisa',
        },
        body: '/retest',
      },
    } as WebhookPayload

    nock('https://api.github.com')
      .get(`/repos/example/repository/pulls/1234`)
      .reply(200, {
        number: 1234,
        head: {
          ref: 'the-branch',
          sha: 'cafed00d',
        },
      })

    nock('https://api.github.com')
      .get(`/repos/example/repository/actions/runs?branch=the-branch`)
      .reply(200, {
        workflow_runs: [
          {
            name: 'CI',
            head_sha: 'deadbeef',
            conclusion: 'failure',
            url: 'https://api.github.com/repos/example/repository/actions/runs/101',
          },
          {
            name: 'CI',
            head_sha: 'cafed00d',
            conclusion: 'failure',
            url: 'https://api.github.com/repos/example/repository/actions/runs/102',
          },
          {
            name: 'Lint',
            head_sha: 'cafed00d',
            conclusion: 'success',
            url: 'https://api.github.com/repos/example/repository/actions/runs/102',
          },
        ],
      })

    nock('https://api.github.com')
      .post(`/repos/example/repository/actions/runs/102/rerun-failed-jobs`)
      .reply(200, {})

    nock('https://api.github.com')
      .post(`/repos/example/repository/issues/comments/1/reactions`, body => {
        return body.content === 'rocket'
      })
      .reply(200, {})

    await run()
  })
})
