import * as core from '@actions/core'
import nock from 'nock'
import run from '../main'
import {_mockInstance} from '../__mocks__/@octokit/rest.js'

beforeEach(() => {
  jest.resetModules()
  jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
    if (name === 'token') return '12345'
    return ''
  })

  jest.spyOn(core, 'getBooleanInput').mockImplementation((name: string): boolean => {
    if (name === 'token-ok') return true
    return false
  })

  process.env['GITHUB_REPOSITORY'] = 'example/repository'
})

afterEach(() => {
  expect(nock.pendingMocks()).toEqual([])
  nock.isDone()
  nock.cleanAll()
})

describe('dispatch action', () => {
  it('runs', async () => {
    await expect(run()).resolves.not.toThrow()
  })
})

describe('retry logic', () => {
  beforeEach(() => {
    _mockInstance.auth.mockReset()
    _mockInstance.apps.listInstallations.mockReset()
    _mockInstance.apps.listInstallations.mockResolvedValue({data: [{id: 123}]})
    jest.useFakeTimers()
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'key') return 'fake-key'
      if (name === 'app_id') return '123'
      if (name === 'retries') return '3'
      if (name === 'retry-base-delay-ms') return '100'
      if (name === 'retry-max-delay-ms') return '500'
      return ''
    })
    jest.spyOn(core, 'warning').mockImplementation(() => {})
    jest.spyOn(core, 'setFailed').mockImplementation(() => {})
    jest.spyOn(core, 'setOutput').mockImplementation(() => {})
    jest.spyOn(core, 'setSecret').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('respects Retry-After header on 429', async () => {
    const err429 = Object.assign(new Error('Too Many Requests'), {
      status: 429,
      response: {headers: {'retry-after': '2'}},
    })
    let calls = 0
    _mockInstance.auth.mockImplementation(() => {
      calls++
      if (calls < 2) return Promise.reject(err429)
      return Promise.resolve({token: 'rl-token'})
    })

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(calls).toBe(2)
    expect(core.setOutput).toHaveBeenCalledWith('token', 'rl-token')
  })

  it('succeeds after transient 504 failures', async () => {
    const err504 = Object.assign(new Error('Gateway Timeout'), {status: 504})
    let calls = 0
    _mockInstance.auth.mockImplementation(() => {
      calls++
      if (calls < 3) return Promise.reject(err504)
      return Promise.resolve({token: 'retried-token'})
    })

    const runPromise = run()
    // advance timers to skip backoff delays
    await jest.runAllTimersAsync()
    await runPromise

    expect(calls).toBe(3)
    expect(core.setOutput).toHaveBeenCalledWith('token', 'retried-token')
    expect(core.warning).toHaveBeenCalledTimes(2)
  })

  it('fails after exhausting retries', async () => {
    const err504 = Object.assign(new Error('Gateway Timeout'), {status: 504})
    _mockInstance.auth.mockRejectedValue(err504)

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('Appauth failure'))
    // 3 retries means 4 total calls (initial + 3 retries)
    expect(_mockInstance.auth).toHaveBeenCalledTimes(4)
  })

  it('fails immediately on non-retriable error (401)', async () => {
    const err401 = Object.assign(new Error('Unauthorized'), {status: 401})
    _mockInstance.auth.mockRejectedValue(err401)

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('Appauth failure'))
    // Should only try once - no retries on 401
    expect(_mockInstance.auth).toHaveBeenCalledTimes(1)
    expect(core.warning).not.toHaveBeenCalled()
  })

  it('does not retry when retries input is 0', async () => {
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'key') return 'fake-key'
      if (name === 'app_id') return '123'
      if (name === 'retries') return '0'
      return ''
    })
    const err504 = Object.assign(new Error('Gateway Timeout'), {status: 504})
    _mockInstance.auth.mockRejectedValue(err504)

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(_mockInstance.auth).toHaveBeenCalledTimes(1)
    expect(core.warning).not.toHaveBeenCalled()
    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('Appauth failure'))
  })

  it('applies default values when inputs are empty', async () => {
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'key') return 'fake-key'
      if (name === 'app_id') return '123'
      // retries, retry-base-delay-ms, retry-max-delay-ms all empty
      return ''
    })
    _mockInstance.auth.mockResolvedValue({token: 'default-token'})

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(core.setOutput).toHaveBeenCalledWith('token', 'default-token')
  })

  it('applies default values when inputs are invalid (NaN)', async () => {
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'key') return 'fake-key'
      if (name === 'app_id') return '123'
      if (name === 'retries') return 'not-a-number'
      if (name === 'retry-base-delay-ms') return 'bad'
      if (name === 'retry-max-delay-ms') return 'bad'
      return ''
    })
    _mockInstance.auth.mockResolvedValue({token: 'default-token'})

    const runPromise = run()
    await jest.runAllTimersAsync()
    await runPromise

    expect(core.setOutput).toHaveBeenCalledWith('token', 'default-token')
  })
})
