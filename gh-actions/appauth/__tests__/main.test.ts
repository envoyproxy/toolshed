import * as core from '@actions/core'
import nock from 'nock'
import run from '../main'

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
